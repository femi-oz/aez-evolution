# 🔒 AEZ Evolution Security Implementation Plan

## Phase 1: Critical Security Fixes (TODAY)

### 1. Fix PDA Collision Bug
**File**: `programs/aez-evolution/src/lib.rs`
**Priority**: CRITICAL

```rust
// Add commitment counter account
#[account]
pub struct CommitmentCounter {
    pub count: u64,
    pub bump: u8,
}

// Update create_commitment seeds:
seeds = [
    b"commitment",
    agent_a.key().as_ref(),
    agent_b.key().as_ref(),
    &commitment_counter.count.to_le_bytes()  // Sequential, not timestamp
]
```

### 2. Add Authority Checks
**File**: `programs/aez-evolution/src/lib.rs`
**Lines**: submit_action, reveal_action

```rust
pub fn submit_action(ctx: Context<SubmitAction>, ...) -> Result<()> {
    require_keys_eq!(
        ctx.accounts.authority.key(),
        ctx.accounts.agent.authority,
        ErrorCode::Unauthorized
    );
    // ... rest of function
}
```

### 3. Implement Checked Math
**File**: `programs/aez-evolution/src/lib.rs`
**Lines**: All compute_balance operations

```rust
agent.compute_balance = agent.compute_balance
    .checked_sub(stake)
    .ok_or(ErrorCode::InsufficientCompute)?;

agent.compute_balance = agent.compute_balance
    .checked_add(reward)
    .ok_or(ErrorCode::ComputeOverflow)?;
```

### 4. Both-Reveal Requirement
**File**: `programs/aez-evolution/src/lib.rs`
**Function**: resolve_commitment

```rust
pub fn resolve_commitment(...) -> Result<()> {
    require!(
        commitment.action_a.is_some() && commitment.action_b.is_some(),
        ErrorCode::BothMustReveal
    );
    // ... continue resolution
}
```

---

## Phase 2: Trust Graph Security (DAY 2)

### 1. TrustEdge Account Structure
```rust
#[account]
pub struct TrustEdge {
    pub from: Pubkey,
    pub to: Pubkey,
    pub trust_score: f32,           // [0.0, 1.0] validated
    pub total_stake_committed: u64, // Sybil resistance
    pub interaction_count: u32,
    pub last_updated: i64,
    pub bump: u8,
}

// Validation
impl TrustEdge {
    pub fn validate(&self) -> Result<()> {
        require!(
            self.trust_score >= 0.0 && self.trust_score <= 1.0,
            ErrorCode::InvalidTrustScore
        );
        require!(
            self.total_stake_committed >= MIN_STAKE_FOR_TRUST,
            ErrorCode::InsufficientStakeForTrust
        );
        Ok(())
    }
}
```

### 2. Path Discovery with Security
```rust
pub fn discover_agent_via_path(
    ctx: Context<DiscoverAgent>,
    path: Vec<Pubkey>
) -> Result<()> {
    // Security checks
    require!(path.len() >= 2, ErrorCode::PathTooShort);
    require!(path.len() <= MAX_PATH_LENGTH, ErrorCode::PathTooLong);

    // Cycle detection
    verify_path_acyclic(&path)?;

    // Calculate transitive trust with decay
    let mut trust = 1.0_f32;
    for i in 0..path.len()-1 {
        let edge = load_trust_edge(path[i], path[i+1])?;
        trust *= edge.trust_score;
    }

    // Length penalty (exponential decay)
    let length_penalty = 0.9_f32.powi((path.len() - 1) as i32);
    trust *= length_penalty;

    // Create new edge with computed trust
    create_trust_edge(path[0], path.last()?, trust)?;

    Ok(())
}

fn verify_path_acyclic(path: &[Pubkey]) -> Result<()> {
    let mut seen = std::collections::HashSet::new();
    for node in path {
        require!(!seen.contains(node), ErrorCode::CircularPath);
        seen.insert(*node);
    }
    Ok(())
}
```

### 3. Stake-Weighted Trust
```rust
pub fn update_trust_after_commitment(
    edge: &mut TrustEdge,
    outcome: CommitmentOutcome,
    stake: u64
) -> Result<()> {
    // Update trust based on outcome
    match outcome {
        CommitmentOutcome::BothCooperated => {
            edge.trust_score = (edge.trust_score + 0.1).min(1.0);
        }
        CommitmentOutcome::Betrayed => {
            edge.trust_score = (edge.trust_score - 0.2).max(0.0);
        }
        _ => {}
    }

    // Accumulate stake (Sybil resistance)
    edge.total_stake_committed = edge.total_stake_committed
        .checked_add(stake)
        .ok_or(ErrorCode::StakeOverflow)?;

    edge.interaction_count += 1;
    edge.last_updated = Clock::get()?.unix_timestamp;

    Ok(())
}
```

---

## Phase 3: Capability Composition Security (DAY 3)

### 1. Atomic Multi-Party Execution
```rust
#[account]
pub struct MultiPartyCommitment {
    pub participants: Vec<Pubkey>,      // Max 10 participants
    pub requirements: Vec<Capability>,
    pub contributions: Vec<Capability>,
    pub escrow_amount: u64,             // Total escrowed compute
    pub completed_count: u8,            // How many finished
    pub failed: bool,                   // Any defection = true
}

pub fn resolve_multiparty(ctx: Context<ResolveMultiParty>) -> Result<()> {
    let commitment = &mut ctx.accounts.commitment;

    // Check all participants completed
    require!(
        commitment.completed_count == commitment.participants.len() as u8,
        ErrorCode::NotAllCompleted
    );

    if commitment.failed {
        // Slash all participants' reputation
        for participant in &commitment.participants {
            slash_reputation(participant, 0.5)?;
        }

        // Escrow goes to protocol treasury
        // (Alternative: burn or redistribute to honest agents)
    } else {
        // Distribute rewards proportionally
        distribute_rewards(commitment)?;

        // Boost all participants' mutual trust
        for i in 0..commitment.participants.len() {
            for j in i+1..commitment.participants.len() {
                boost_trust(
                    commitment.participants[i],
                    commitment.participants[j],
                    0.05
                )?;
            }
        }
    }

    Ok(())
}
```

### 2. Capability Validation
```rust
pub enum Capability {
    Compute { cycles: u64 },
    Data { quality: u8, domain: String },
    Validation { accuracy: u8 },
}

impl Capability {
    pub fn validate(&self) -> Result<()> {
        match self {
            Capability::Compute { cycles } => {
                require!(
                    *cycles > 0 && *cycles <= MAX_COMPUTE_CYCLES,
                    ErrorCode::InvalidCapability
                );
            }
            Capability::Data { quality, domain } => {
                require!(
                    *quality <= 100,
                    ErrorCode::InvalidQuality
                );
                require!(
                    domain.len() <= 32,
                    ErrorCode::DomainTooLong
                );
            }
            Capability::Validation { accuracy } => {
                require!(
                    *accuracy <= 100,
                    ErrorCode::InvalidAccuracy
                );
            }
        }
        Ok(())
    }
}
```

---

## Phase 4: Adaptive Strategy Security (DAY 4)

### 1. Rate-Limited Strategy Updates
```rust
#[account]
pub struct AdaptiveAgent {
    pub base: Agent,  // Inherit from Agent
    pub weights: Vec<f32>,  // Neural weights (max 100)
    pub learning_rate: f32,
    pub last_update: i64,
    pub update_cooldown: i64,  // Minimum time between updates
    pub baseline_fitness: i64,
}

pub fn update_strategy(
    ctx: Context<UpdateStrategy>,
    new_weights: Vec<f32>
) -> Result<()> {
    let agent = &mut ctx.accounts.adaptive_agent;
    let clock = Clock::get()?;

    // Security checks
    require_keys_eq!(
        ctx.accounts.authority.key(),
        agent.base.authority,
        ErrorCode::Unauthorized
    );

    require!(
        clock.unix_timestamp - agent.last_update > agent.update_cooldown,
        ErrorCode::UpdateCooldownActive
    );

    require!(
        agent.base.fitness_score > agent.baseline_fitness,
        ErrorCode::FitnessDidNotImprove
    );

    require!(
        new_weights.len() == agent.weights.len(),
        ErrorCode::WeightCountMismatch
    );

    require!(
        agent.learning_rate >= MIN_LEARNING_RATE &&
        agent.learning_rate <= MAX_LEARNING_RATE,
        ErrorCode::InvalidLearningRate
    );

    // Apply update with learning rate
    for (i, &new_weight) in new_weights.iter().enumerate() {
        // Bound weights to prevent adversarial values
        require!(
            new_weight >= -10.0 && new_weight <= 10.0,
            ErrorCode::WeightOutOfBounds
        );

        agent.weights[i] = agent.weights[i] * (1.0 - agent.learning_rate)
            + new_weight * agent.learning_rate;
    }

    agent.last_update = clock.unix_timestamp;
    agent.baseline_fitness = agent.base.fitness_score;

    emit!(StrategyUpdated {
        agent: agent.base.key(),
        generation: agent.base.generation,
        new_fitness: agent.base.fitness_score,
    });

    Ok(())
}
```

---

## Testing Checklist

### Unit Tests
- [ ] PDA collision resolution with counter
- [ ] Authority checks on all protected operations
- [ ] Overflow/underflow protection
- [ ] Trust score bounds [0.0, 1.0]
- [ ] Path cycle detection
- [ ] Learning rate validation

### Integration Tests
- [ ] Create commitment → submit → reveal → resolve flow
- [ ] Trust edge creation and update
- [ ] Multi-party commitment atomic execution
- [ ] Strategy update with fitness improvement

### Attack Simulation Tests
- [ ] Attempt PDA collision attack
- [ ] Attempt unauthorized action submission
- [ ] Attempt trust score manipulation
- [ ] Attempt circular path exploitation
- [ ] Attempt strategy update without improvement

---

## Security Audit TODO

Before mainnet:
1. [ ] Professional smart contract audit (Halborn, Trail of Bits, etc.)
2. [ ] Formal verification of critical invariants
3. [ ] Fuzz testing with Honggfuzz
4. [ ] Economic analysis of game-theoretic attacks
5. [ ] Testnet stress testing (10,000+ agents)

---

## Constants & Configuration

```rust
// Security parameters
pub const MIN_STAKE_FOR_TRUST: u64 = 100_000;  // 0.0001 SOL
pub const MAX_PATH_LENGTH: usize = 5;
pub const MIN_LEARNING_RATE: f32 = 0.001;
pub const MAX_LEARNING_RATE: f32 = 0.1;
pub const MIN_COMMITMENT_STAKE: u64 = 10_000;  // 0.00001 SOL
pub const COMMITMENT_COOLDOWN: i64 = 5;  // 5 seconds
pub const MAX_COMPUTE_CYCLES: u64 = 1_000_000_000;
pub const MAX_WEIGHTS: usize = 100;

// Trust parameters
pub const TRUST_BOOST_COOPERATE: f32 = 0.1;
pub const TRUST_SLASH_DEFECT: f32 = 0.2;
pub const TRUST_DECAY_RATE: f32 = 0.95;  // Per epoch
pub const PATH_LENGTH_PENALTY: f32 = 0.9;  // Exponential per hop
```

---

**Status**: Ready for implementation
**Next**: Start Phase 1 implementation
