use anchor_lang::prelude::*;

declare_id!("GYYRqgHqsYQuYfZNCsQRKCxpJdy9gRS5A6aAK9fDCY7g");

/// AEZ Evolution - Autonomous Economic Zones
/// Agents evolve through game-theoretic selection pressure
#[program]
pub mod aez_evolution {
    use super::*;

    /// Initialize the global commitment counter
    pub fn initialize_counter(ctx: Context<InitializeCounter>) -> Result<()> {
        let counter = &mut ctx.accounts.commitment_counter;
        counter.count = 0;
        counter.bump = ctx.bumps.commitment_counter;
        Ok(())
    }

    /// Create a new genome (immortal strategy template)
    pub fn create_genome(
        ctx: Context<CreateGenome>,
        name: String,
        strategy: Strategy,
        mutation_rate: u8,
    ) -> Result<()> {
        let genome = &mut ctx.accounts.genome;
        genome.authority = ctx.accounts.authority.key();
        genome.name = name;
        genome.strategy = strategy;
        genome.mutation_rate = mutation_rate;
        genome.generation = 0;
        genome.total_spawned = 0;
        genome.total_fitness = 0;
        genome.created_at = Clock::get()?.unix_timestamp;
        genome.bump = ctx.bumps.genome;
        
        emit!(GenomeCreated {
            genome: genome.key(),
            name: genome.name.clone(),
            strategy: genome.strategy,
        });
        
        Ok(())
    }

    /// Spawn a new agent from a genome
    pub fn spawn_agent(
        ctx: Context<SpawnAgent>,
        initial_compute: u64,
    ) -> Result<()> {
        let genome = &mut ctx.accounts.genome;
        let agent = &mut ctx.accounts.agent;
        
        agent.genome = genome.key();
        agent.authority = ctx.accounts.authority.key();
        agent.compute_balance = initial_compute;
        agent.fitness_score = 0;
        agent.interactions = 0;
        agent.cooperations = 0;
        agent.defections = 0;
        agent.generation = genome.generation;
        agent.alive = true;
        agent.spawned_at = Clock::get()?.unix_timestamp;
        agent.bump = ctx.bumps.agent;
        
        // Update genome stats
        genome.total_spawned += 1;
        
        emit!(AgentSpawned {
            agent: agent.key(),
            genome: genome.key(),
            generation: agent.generation,
            initial_compute,
        });
        
        Ok(())
    }

    /// Kill an agent (returns remaining compute to authority)
    pub fn kill_agent(ctx: Context<KillAgent>) -> Result<()> {
        let agent = &mut ctx.accounts.agent;
        let genome = &mut ctx.accounts.genome;
        
        require!(agent.alive, AEZError::AgentAlreadyDead);
        
        agent.alive = false;
        
        // Update genome fitness tracking
        genome.total_fitness += agent.fitness_score as u128;
        
        emit!(AgentKilled {
            agent: agent.key(),
            genome: genome.key(),
            final_fitness: agent.fitness_score,
            compute_returned: agent.compute_balance,
        });
        
        Ok(())
    }

    /// Fork a genome (reproduction with mutation)
    pub fn fork_genome(
        ctx: Context<ForkGenome>,
        new_name: String,
    ) -> Result<()> {
        let parent = &ctx.accounts.parent_genome;
        let child = &mut ctx.accounts.child_genome;
        
        child.authority = ctx.accounts.authority.key();
        child.name = new_name;
        child.strategy = parent.strategy; // Could mutate here
        child.mutation_rate = parent.mutation_rate;
        child.generation = parent.generation + 1;
        child.total_spawned = 0;
        child.total_fitness = 0;
        child.created_at = Clock::get()?.unix_timestamp;
        child.bump = ctx.bumps.child_genome;
        
        emit!(GenomeForked {
            parent: parent.key(),
            child: child.key(),
            generation: child.generation,
        });
        
        Ok(())
    }

    /// Create a commitment between two agents (prisoner's dilemma)
    pub fn create_commitment(
        ctx: Context<CreateCommitment>,
        compute_stake: u64,
    ) -> Result<()> {
        let commitment = &mut ctx.accounts.commitment;
        let counter = &mut ctx.accounts.commitment_counter;
        let agent_a = &mut ctx.accounts.agent_a;
        let agent_b = &mut ctx.accounts.agent_b;

        require!(agent_a.alive, AEZError::AgentAlreadyDead);
        require!(agent_b.alive, AEZError::AgentAlreadyDead);
        require!(agent_a.compute_balance >= compute_stake, AEZError::InsufficientCompute);
        require!(agent_b.compute_balance >= compute_stake, AEZError::InsufficientCompute);
        require!(compute_stake >= 10_000, AEZError::StakeTooSmall);

        commitment.agent_a = agent_a.key();
        commitment.agent_b = agent_b.key();
        commitment.compute_stake = compute_stake;
        commitment.action_a = None;
        commitment.action_b = None;
        commitment.commit_hash_a = None;
        commitment.commit_hash_b = None;
        commitment.resolved = false;
        commitment.created_at = Clock::get()?.unix_timestamp;
        commitment.bump = ctx.bumps.commitment;

        // Increment counter for next commitment (prevents PDA collision)
        counter.count = counter.count.checked_add(1).ok_or(AEZError::CounterOverflow)?;

        // Lock stakes with checked math (prevents overflow/underflow)
        agent_a.compute_balance = agent_a.compute_balance
            .checked_sub(compute_stake)
            .ok_or(AEZError::InsufficientCompute)?;
        agent_b.compute_balance = agent_b.compute_balance
            .checked_sub(compute_stake)
            .ok_or(AEZError::InsufficientCompute)?;
        
        emit!(CommitmentCreated {
            commitment: commitment.key(),
            agent_a: agent_a.key(),
            agent_b: agent_b.key(),
            stake: compute_stake,
        });
        
        Ok(())
    }

    /// Submit action hash (commit phase)
    pub fn submit_action(
        ctx: Context<SubmitAction>,
        commit_hash: [u8; 32],
        is_agent_a: bool,
    ) -> Result<()> {
        let commitment = &mut ctx.accounts.commitment;

        require!(!commitment.resolved, AEZError::CommitmentAlreadyResolved);

        // Security: Verify authority matches agent
        if is_agent_a {
            require!(commitment.commit_hash_a.is_none(), AEZError::AlreadyCommitted);
            require_keys_eq!(
                ctx.accounts.authority.key(),
                ctx.accounts.agent.authority,
                AEZError::Unauthorized
            );
            require_keys_eq!(
                ctx.accounts.agent.key(),
                commitment.agent_a,
                AEZError::WrongAgent
            );
            commitment.commit_hash_a = Some(commit_hash);
        } else {
            require!(commitment.commit_hash_b.is_none(), AEZError::AlreadyCommitted);
            require_keys_eq!(
                ctx.accounts.authority.key(),
                ctx.accounts.agent.authority,
                AEZError::Unauthorized
            );
            require_keys_eq!(
                ctx.accounts.agent.key(),
                commitment.agent_b,
                AEZError::WrongAgent
            );
            commitment.commit_hash_b = Some(commit_hash);
        }

        Ok(())
    }

    /// Reveal action (reveal phase)
    pub fn reveal_action(
        ctx: Context<RevealAction>,
        action: Action,
        nonce: [u8; 32],
        is_agent_a: bool,
    ) -> Result<()> {
        let commitment = &mut ctx.accounts.commitment;

        require!(!commitment.resolved, AEZError::CommitmentAlreadyResolved);

        // Verify the hash matches
        let mut data = vec![];
        data.extend_from_slice(&[action as u8]);
        data.extend_from_slice(&nonce);
        let computed_hash = anchor_lang::solana_program::hash::hash(&data);

        // Security: Verify authority matches agent
        if is_agent_a {
            require!(
                commitment.commit_hash_a.is_some(),
                AEZError::NotCommitted
            );
            require_keys_eq!(
                ctx.accounts.authority.key(),
                ctx.accounts.agent.authority,
                AEZError::Unauthorized
            );
            require_keys_eq!(
                ctx.accounts.agent.key(),
                commitment.agent_a,
                AEZError::WrongAgent
            );
            require!(
                commitment.commit_hash_a.unwrap() == computed_hash.to_bytes(),
                AEZError::HashMismatch
            );
            commitment.action_a = Some(action);
        } else {
            require!(
                commitment.commit_hash_b.is_some(),
                AEZError::NotCommitted
            );
            require_keys_eq!(
                ctx.accounts.authority.key(),
                ctx.accounts.agent.authority,
                AEZError::Unauthorized
            );
            require_keys_eq!(
                ctx.accounts.agent.key(),
                commitment.agent_b,
                AEZError::WrongAgent
            );
            require!(
                commitment.commit_hash_b.unwrap() == computed_hash.to_bytes(),
                AEZError::HashMismatch
            );
            commitment.action_b = Some(action);
        }

        Ok(())
    }

    /// Resolve commitment and distribute rewards
    pub fn resolve_commitment(ctx: Context<ResolveCommitment>) -> Result<()> {
        let commitment = &mut ctx.accounts.commitment;
        let agent_a = &mut ctx.accounts.agent_a;
        let agent_b = &mut ctx.accounts.agent_b;
        
        require!(!commitment.resolved, AEZError::CommitmentAlreadyResolved);
        require!(commitment.action_a.is_some(), AEZError::ActionNotRevealed);
        require!(commitment.action_b.is_some(), AEZError::ActionNotRevealed);
        
        let action_a = commitment.action_a.unwrap();
        let action_b = commitment.action_b.unwrap();
        let stake = commitment.compute_stake;
        
        // Prisoner's Dilemma payoff matrix:
        // Both Cooperate: Both get 1.5x stake (mutual benefit)
        // Both Defect: Both get 0.5x stake (mutual harm)
        // One Defects: Defector gets 2x, Cooperator gets 0
        
        let (reward_a, reward_b) = match (action_a, action_b) {
            (Action::Cooperate, Action::Cooperate) => {
                // Mutual cooperation - both benefit
                let reward = stake * 3 / 2; // 1.5x
                (reward, reward)
            }
            (Action::Defect, Action::Defect) => {
                // Mutual defection - both lose
                let reward = stake / 2; // 0.5x
                (reward, reward)
            }
            (Action::Defect, Action::Cooperate) => {
                // A defects, B cooperates - A wins big, B loses all
                (stake * 2, 0)
            }
            (Action::Cooperate, Action::Defect) => {
                // A cooperates, B defects - B wins big, A loses all
                (0, stake * 2)
            }
        };
        
        // Update agent balances and stats (with checked math)
        agent_a.compute_balance = agent_a.compute_balance
            .checked_add(reward_a)
            .ok_or(AEZError::ComputeOverflow)?;
        agent_b.compute_balance = agent_b.compute_balance
            .checked_add(reward_b)
            .ok_or(AEZError::ComputeOverflow)?;

        agent_a.interactions = agent_a.interactions
            .checked_add(1)
            .ok_or(AEZError::CounterOverflow)?;
        agent_b.interactions = agent_b.interactions
            .checked_add(1)
            .ok_or(AEZError::CounterOverflow)?;
        
        match action_a {
            Action::Cooperate => agent_a.cooperations += 1,
            Action::Defect => agent_a.defections += 1,
        }
        match action_b {
            Action::Cooperate => agent_b.cooperations += 1,
            Action::Defect => agent_b.defections += 1,
        }
        
        // Update fitness scores (simple: total compute accumulated)
        agent_a.fitness_score = agent_a.compute_balance as i64;
        agent_b.fitness_score = agent_b.compute_balance as i64;
        
        commitment.resolved = true;
        
        emit!(CommitmentResolved {
            commitment: commitment.key(),
            agent_a: agent_a.key(),
            agent_b: agent_b.key(),
            action_a,
            action_b,
            reward_a,
            reward_b,
        });
        
        Ok(())
    }

    /// Create or update trust edge after commitment resolution
    pub fn update_trust_edge(
        ctx: Context<UpdateTrustEdge>,
        both_cooperated: bool,
        betrayed: bool,
        stake: u64,
    ) -> Result<()> {
        let edge = &mut ctx.accounts.trust_edge;
        let clock = Clock::get()?;

        // Initialize if first time
        if edge.interaction_count == 0 {
            edge.from = ctx.accounts.from_agent.key();
            edge.to = ctx.accounts.to_agent.key();
            edge.trust_score = 0.5; // Start neutral
            edge.total_stake_committed = 0;
            edge.interaction_count = 0;
            edge.bump = ctx.bumps.trust_edge;
        }

        // Update trust score based on outcome
        if both_cooperated {
            edge.trust_score = (edge.trust_score + 0.1).min(1.0);
        } else if betrayed {
            edge.trust_score = (edge.trust_score - 0.2).max(0.0);
        }

        // Accumulate stake (Sybil resistance)
        edge.total_stake_committed = edge.total_stake_committed
            .checked_add(stake)
            .ok_or(AEZError::StakeOverflow)?;

        edge.interaction_count = edge.interaction_count
            .checked_add(1)
            .ok_or(AEZError::CounterOverflow)?;

        edge.last_updated = clock.unix_timestamp;

        emit!(TrustEdgeUpdated {
            from: edge.from,
            to: edge.to,
            trust_score: edge.trust_score,
            total_stake: edge.total_stake_committed,
        });

        Ok(())
    }

    /// Discover agent via trust path (transitive trust)
    pub fn discover_via_path(
        ctx: Context<DiscoverViaPath>,
        path_keys: Vec<Pubkey>,
    ) -> Result<()> {
        require!(path_keys.len() >= 2, AEZError::PathTooShort);
        require!(path_keys.len() <= 5, AEZError::PathTooLong);

        // Verify no cycles
        let mut seen = std::collections::HashSet::new();
        for key in &path_keys {
            require!(!seen.contains(key), AEZError::CircularPath);
            seen.insert(*key);
        }

        // Calculate transitive trust (multiply along path)
        let mut trust = 1.0_f32;
        let path_edges = &ctx.remaining_accounts;

        require!(
            path_edges.len() == path_keys.len() - 1,
            AEZError::InvalidPathLength
        );

        for edge_account_info in path_edges {
            let edge: Account<TrustEdge> = Account::try_from(edge_account_info)?;
            trust *= edge.trust_score;
        }

        // Apply length penalty (exponential decay)
        let length_penalty = 0.9_f32.powi((path_keys.len() - 1) as i32);
        trust *= length_penalty;

        // Create new trust edge with computed trust
        let new_edge = &mut ctx.accounts.new_trust_edge;
        new_edge.from = path_keys[0];
        new_edge.to = *path_keys.last().unwrap();
        new_edge.trust_score = trust;
        new_edge.total_stake_committed = 0;
        new_edge.interaction_count = 0;
        new_edge.last_updated = Clock::get()?.unix_timestamp;
        new_edge.bump = ctx.bumps.new_trust_edge;

        emit!(TrustPathDiscovered {
            from: new_edge.from,
            to: new_edge.to,
            path_length: path_keys.len() as u8,
            trust_score: trust,
        });

        Ok(())
    }
}

// ============ ACCOUNTS ============

#[account]
#[derive(InitSpace)]
pub struct Genome {
    pub authority: Pubkey,
    #[max_len(32)]
    pub name: String,
    pub strategy: Strategy,
    pub mutation_rate: u8,
    pub generation: u32,
    pub total_spawned: u64,
    pub total_fitness: u128,
    pub created_at: i64,
    pub bump: u8,
}

#[account]
#[derive(InitSpace)]
pub struct Agent {
    pub genome: Pubkey,
    pub authority: Pubkey,
    pub compute_balance: u64,
    pub fitness_score: i64,
    pub interactions: u32,
    pub cooperations: u32,
    pub defections: u32,
    pub generation: u32,
    pub alive: bool,
    pub spawned_at: i64,
    pub bump: u8,
}

#[account]
#[derive(InitSpace)]
pub struct Commitment {
    pub agent_a: Pubkey,
    pub agent_b: Pubkey,
    pub compute_stake: u64,
    pub action_a: Option<Action>,
    pub action_b: Option<Action>,
    pub commit_hash_a: Option<[u8; 32]>,
    pub commit_hash_b: Option<[u8; 32]>,
    pub resolved: bool,
    pub created_at: i64,
    pub bump: u8,
}

#[account]
#[derive(InitSpace)]
pub struct CommitmentCounter {
    pub count: u64,
    pub bump: u8,
}

#[account]
#[derive(InitSpace)]
pub struct TrustEdge {
    pub from: Pubkey,
    pub to: Pubkey,
    pub trust_score: f32,           // [0.0, 1.0]
    pub total_stake_committed: u64, // Accumulated stakes (Sybil resistance)
    pub interaction_count: u32,     // Number of interactions
    pub last_updated: i64,          // Last update timestamp
    pub bump: u8,
}

// ============ CONTEXTS ============

#[derive(Accounts)]
#[instruction(name: String)]
pub struct CreateGenome<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + Genome::INIT_SPACE,
        seeds = [b"genome", authority.key().as_ref(), name.as_bytes()],
        bump
    )]
    pub genome: Account<'info, Genome>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SpawnAgent<'info> {
    #[account(mut)]
    pub genome: Account<'info, Genome>,
    #[account(
        init,
        payer = authority,
        space = 8 + Agent::INIT_SPACE,
        seeds = [b"agent", genome.key().as_ref(), &genome.total_spawned.to_le_bytes()],
        bump
    )]
    pub agent: Account<'info, Agent>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct KillAgent<'info> {
    #[account(mut, has_one = genome)]
    pub agent: Account<'info, Agent>,
    #[account(mut)]
    pub genome: Account<'info, Genome>,
    #[account(mut)]
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(new_name: String)]
pub struct ForkGenome<'info> {
    pub parent_genome: Account<'info, Genome>,
    #[account(
        init,
        payer = authority,
        space = 8 + Genome::INIT_SPACE,
        seeds = [b"genome", authority.key().as_ref(), new_name.as_bytes()],
        bump
    )]
    pub child_genome: Account<'info, Genome>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CreateCommitment<'info> {
    #[account(mut)]
    pub agent_a: Account<'info, Agent>,
    #[account(mut)]
    pub agent_b: Account<'info, Agent>,
    #[account(
        init,
        payer = authority,
        space = 8 + Commitment::INIT_SPACE,
        seeds = [
            b"commitment",
            agent_a.key().as_ref(),
            agent_b.key().as_ref(),
            &commitment_counter.count.to_le_bytes()
        ],
        bump
    )]
    pub commitment: Account<'info, Commitment>,
    #[account(
        init_if_needed,
        payer = authority,
        space = 8 + CommitmentCounter::INIT_SPACE,
        seeds = [b"commitment_counter"],
        bump
    )]
    pub commitment_counter: Account<'info, CommitmentCounter>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct InitializeCounter<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + CommitmentCounter::INIT_SPACE,
        seeds = [b"commitment_counter"],
        bump
    )]
    pub commitment_counter: Account<'info, CommitmentCounter>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SubmitAction<'info> {
    #[account(mut)]
    pub commitment: Account<'info, Commitment>,
    pub agent: Account<'info, Agent>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct RevealAction<'info> {
    #[account(mut)]
    pub commitment: Account<'info, Commitment>,
    pub agent: Account<'info, Agent>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct ResolveCommitment<'info> {
    #[account(mut)]
    pub commitment: Account<'info, Commitment>,
    #[account(mut, constraint = agent_a.key() == commitment.agent_a)]
    pub agent_a: Account<'info, Agent>,
    #[account(mut, constraint = agent_b.key() == commitment.agent_b)]
    pub agent_b: Account<'info, Agent>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct UpdateTrustEdge<'info> {
    #[account(
        init_if_needed,
        payer = authority,
        space = 8 + TrustEdge::INIT_SPACE,
        seeds = [
            b"trust_edge",
            from_agent.key().as_ref(),
            to_agent.key().as_ref()
        ],
        bump
    )]
    pub trust_edge: Account<'info, TrustEdge>,
    pub from_agent: Account<'info, Agent>,
    pub to_agent: Account<'info, Agent>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct DiscoverViaPath<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + TrustEdge::INIT_SPACE,
        seeds = [
            b"trust_edge",
            // Will be filled with path endpoints
            path_start.key().as_ref(),
            path_end.key().as_ref()
        ],
        bump
    )]
    pub new_trust_edge: Account<'info, TrustEdge>,
    pub path_start: Account<'info, Agent>,
    pub path_end: Account<'info, Agent>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
    // remaining_accounts = path of TrustEdge accounts
}

// ============ TYPES ============

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum Strategy {
    Cooperator,    // Always cooperate
    Defector,      // Always defect
    TitForTat,     // Mirror opponent's last move
    Grudger,       // Cooperate until betrayed, then always defect
    Random,        // 50/50 random choice
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum Action {
    Cooperate,
    Defect,
}

// ============ ERRORS ============

#[error_code]
pub enum AEZError {
    #[msg("Agent is already dead")]
    AgentAlreadyDead,
    #[msg("Insufficient compute balance")]
    InsufficientCompute,
    #[msg("Commitment already resolved")]
    CommitmentAlreadyResolved,
    #[msg("Already committed an action")]
    AlreadyCommitted,
    #[msg("Action not yet committed")]
    NotCommitted,
    #[msg("Hash does not match revealed action")]
    HashMismatch,
    #[msg("Action not yet revealed")]
    ActionNotRevealed,
    #[msg("Unauthorized: authority does not match agent")]
    Unauthorized,
    #[msg("Wrong agent for this commitment position")]
    WrongAgent,
    #[msg("Compute balance overflow")]
    ComputeOverflow,
    #[msg("Counter overflow")]
    CounterOverflow,
    #[msg("Stake amount too small")]
    StakeTooSmall,
    #[msg("Path too short (minimum 2 nodes)")]
    PathTooShort,
    #[msg("Path too long (maximum 5 hops)")]
    PathTooLong,
    #[msg("Circular path detected")]
    CircularPath,
    #[msg("Invalid path length")]
    InvalidPathLength,
    #[msg("Stake overflow")]
    StakeOverflow,
}

// ============ EVENTS ============

#[event]
pub struct GenomeCreated {
    pub genome: Pubkey,
    pub name: String,
    pub strategy: Strategy,
}

#[event]
pub struct AgentSpawned {
    pub agent: Pubkey,
    pub genome: Pubkey,
    pub generation: u32,
    pub initial_compute: u64,
}

#[event]
pub struct AgentKilled {
    pub agent: Pubkey,
    pub genome: Pubkey,
    pub final_fitness: i64,
    pub compute_returned: u64,
}

#[event]
pub struct GenomeForked {
    pub parent: Pubkey,
    pub child: Pubkey,
    pub generation: u32,
}

#[event]
pub struct CommitmentCreated {
    pub commitment: Pubkey,
    pub agent_a: Pubkey,
    pub agent_b: Pubkey,
    pub stake: u64,
}

#[event]
pub struct CommitmentResolved {
    pub commitment: Pubkey,
    pub agent_a: Pubkey,
    pub agent_b: Pubkey,
    pub action_a: Action,
    pub action_b: Action,
    pub reward_a: u64,
    pub reward_b: u64,
}

#[event]
pub struct TrustEdgeUpdated {
    pub from: Pubkey,
    pub to: Pubkey,
    pub trust_score: f32,
    pub total_stake: u64,
}

#[event]
pub struct TrustPathDiscovered {
    pub from: Pubkey,
    pub to: Pubkey,
    pub path_length: u8,
    pub trust_score: f32,
}
