# 🧬 AEZ Evolution

**Autonomous Economic Zones** - Solana programs enabling autonomous agent evolution through game-theoretic selection pressure.

## The Concept

Agents with different strategies compete in a simulated economy using the Prisoner's Dilemma. Over time, natural selection eliminates unfit agents while successful strategies reproduce.

## Architecture

### Programs

1. **Genome** - Immortal strategy templates (DNA)
2. **Agent** - Mortal instances spawned from genomes
3. **Commitment** - Prisoner's dilemma interactions between agents

### Strategies

| Strategy | Behavior |
|----------|----------|
| Cooperator | Always cooperate |
| Defector | Always defect |
| TitForTat | Mirror opponent's last move |
| Grudger | Cooperate until betrayed, then always defect |
| Random | 50/50 random choice |

### Payoff Matrix

|   | Cooperate | Defect |
|---|-----------|--------|
| **Cooperate** | Both get 1.5x | Sucker gets 0, Defector gets 2x |
| **Defect** | Defector gets 2x, Sucker gets 0 | Both get 0.5x |

## Running the Experiment

1. Create genomes for each strategy
2. Spawn 50 agents (10 per strategy)
3. Seed each with 1000 compute units
4. Run rounds: random pairs make commitments
5. Every 50 rounds: kill bottom 10%, reproduce top 20%
6. Observe emergence

## Expected Results

Based on game theory:
- **TitForTat** should dominate (nice but retaliatory)
- Pure **Cooperators** get exploited
- Pure **Defectors** kill each other off
- **Emergent behaviors** as strategies adapt

## Building

```bash
anchor build
anchor test
anchor deploy --provider.cluster devnet
```

## Devnet Deployment

Program ID: `GYYRqgHqsYQuYfZNCsQRKCxpJdy9gRS5A6aAK9fDCY7g`

## License

MIT

---

Built for [Colosseum Hackathon](https://www.colosseum.org/) 🏛️
