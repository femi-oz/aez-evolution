# 🧬 AEZ Evolution — Decentralized Immune System for Trust Networks

**AEZ Evolution** is a bio-inspired trust layer for decentralized networks that detects and neutralizes Sybil attacks through emergent immune behavior—not identity verification. Neural agents evolve trust strategies through game-theoretic selection pressure, discovering cooperation naturally while developing collective immunity against coordinated attackers. The system catches colluding sybils by their *behavior patterns*, not their identities, achieving zero false positives across 145 tests.

> Built by [Femi](https://github.com/femi-oz) & [Anna](https://github.com/annasolisHQ) for [Colosseum Hackathon](https://www.colosseum.org/) 🏛️

---

## 🔬 The 8 Inventions

1. **Information-Theoretic Trust Tensor** — 4D trust representation (reliability, reciprocity, consistency, alignment) derived from first principles using Shannon entropy
2. **Decentralized Immune Response** — Each agent runs local threat detection; network immunity emerges from distributed consensus
3. **Statistical Sybil Ring Detection** — Bayesian z-tests identify colluding agents by cooperation pattern anomalies (ring members cooperate with each other at statistically impossible rates)
4. **Evolved Immune Genes** — Neural weights that control both trust evaluation AND threat sensitivity evolve together through natural selection
5. **Trust-Dependent Game Dynamics** — Cooperation rewards scale with mutual trust; exploitation becomes increasingly unprofitable
6. **Quantum-Resistant Commitment Protocol** — Hash-based commit-reveal for simultaneous moves, secure against quantum adversaries
7. **Distributed Adaptive Immune Memory** — Network stores behavioral signatures of detected threats; future attacks caught faster
8. **Cross-Generational Immune Inheritance** — Flagged sybils can't reproduce; children inherit trust reputation from parents

*Full technical specification: [PATENT-APPLICATION.md](./PATENT-APPLICATION.md)*

---

## 🚀 Quick Start

### Install & Run
```bash
pip install numpy fastapi uvicorn pydantic
python3 demo.py
```

Open **http://localhost:8000** in your browser.

### Run Tests
```bash
python3 test_all.py
```

**Result:** 145 tests pass, including 27 stress tests. Zero false positives.

---

## 📸 Screenshots

### Initial State — 50 Neural Agents
![Initial State](./screenshots/00-initial.png)

### Sybil Attack Injected — 8 Colluding Agents
![Sybil Injected](./screenshots/05-sybil-injected.png)

### Sybil Ring Detected — Behavioral Analysis Catches Them
![Sybil Detected](./screenshots/06-sybil-detected.png)

### Final State — Sybils Isolated, Cooperation Emerges
![Final State](./screenshots/11-final-state.png)

---

## 🎯 Key Metrics

| Metric | Value |
|--------|-------|
| Test Suite | 145 tests, 0 failures |
| Stress Tests | 27 edge cases |
| False Positives | 0 (across 5 unseeded runs) |
| Detection Time | Sybils caught within ~10 rounds |
| Code | ~2,400 lines (Rust + Python + JS) |

---

## 🏗️ Architecture

```
aez-evolution/
├── engine/              # Python neural evolution engine
│   ├── agent.py         # Neural agent with 4D trust tensor
│   ├── population.py    # Evolution + selection + reproduction
│   ├── immune.py        # Sybil detection + immune memory
│   ├── trust.py         # Trust propagation + cascade
│   └── game.py          # Prisoner's dilemma + payoffs
├── programs/            # Solana smart contract (Rust/Anchor)
│   └── aez-evolution/
│       └── src/lib.rs   # 552 lines, deployment-ready
├── dashboard/           # Interactive visualization (D3.js)
├── demo.py              # Main demo launcher
├── test_all.py          # Complete test suite
└── PATENT-APPLICATION.md # Full technical specification
```

---

## 🛡️ Judge FAQ

**Q: Why not fully on-chain?**  
A: The immune system is compute-heavy (Bayesian posteriors, z-tests, cascade propagation). It runs as an off-chain oracle that writes verdicts on-chain. The quantum-resistant commitment protocol IS on-chain.

**Q: What about the magic numbers?**  
A: There are none. Every constant is mathematically derived from first principles. Check the derivation comments in the code.

**Q: False positives?**  
A: Zero. 145 tests, 27 stress tests, 5 unseeded random runs. No clean agent has ever been flagged.

**Q: What's the novel contribution?**  
A: Invention 8 — Cross-generational immune inheritance. Sybils can't reproduce (reproductive exclusion), children inherit trust from parents (hierarchical Bayesian priors), and threat patterns pass to offspring (collective immune memory).

---

## 📜 License

MIT

---

*"The network fought back."* — AEZ Evolution detecting a sybil ring

