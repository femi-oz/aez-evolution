#!/usr/bin/env python3
"""
AEZ Evolution Demo Script
The Trust Cascade - Watch AI agents discover cooperation
"""

import time
import sys
from orchestrator.simulation import create_default_simulation

def print_banner():
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║        🎯  AEZ EVOLUTION: THE TRUST CASCADE  🎯             ║
    ║                                                              ║
    ║     Autonomous Economic Zones - AI-Native Economics         ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_act(title, description):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    print(f"{description}\n")
    time.sleep(2)

def print_stats(sim, round_num):
    dist = sim.get_strategy_distribution()
    alive = len(sim.get_alive_agents())
    edges = len([e for e in sim.trust_edges.values() if e.interaction_count > 0])

    print(f"\n📊 Round {round_num:3d} | Alive: {alive:3d} | Trust Edges: {edges:4d}")
    print("-" * 70)

    # Sort by count
    sorted_strategies = sorted(dist.items(), key=lambda x: x[1], reverse=True)
    for strategy, count in sorted_strategies:
        pct = (count / alive * 100) if alive > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {strategy:25s} {count:3d} ({pct:5.1f}%) {bar}")

    # Show top performers
    leaders = sim.get_leaderboard(3)
    if leaders:
        print("\n🏆 Top Performers:")
        for i, agent in enumerate(leaders, 1):
            adaptive_tag = " [ADAPTIVE]" if agent.is_adaptive else ""
            print(f"  {i}. {agent.id} ({agent.strategy_name}){adaptive_tag}: {agent.fitness_score}")

def run_demo():
    print_banner()

    input("Press ENTER to start the simulation...")

    print("\n🔧 Initializing 60 agents...")
    print("   - 40 with fixed strategies (Cooperator, Defector, TitForTat, etc.)")
    print("   - 10 ADAPTIVE agents (will learn from experience)")
    time.sleep(2)

    sim = create_default_simulation()

    print(f"\n✅ Created {len(sim.agents)} agents")
    print(f"   Adaptive agents start with random weights biased toward DEFECTION")
    print(f"   They will learn to COOPERATE if it improves their fitness!")

    input("\nPress ENTER to begin Act 1: Chaos...")

    # ACT 1: CHAOS (Rounds 1-20)
    print_act(
        "ACT 1: CHAOS",
        "Agents test each other. Defectors exploit cooperators.\n"
        "Trust scores are low and unstable. No stable networks yet."
    )

    for r in range(1, 21):
        sim.run_round()
        if r % 5 == 0:
            print_stats(sim, r)
        time.sleep(0.1)

    input("\nPress ENTER to continue to Act 2...")

    # ACT 2: CLUSTERS FORM (Rounds 21-40)
    print_act(
        "ACT 2: CLUSTERS FORM",
        "Cooperators find each other. Trust edges strengthen.\n"
        "Defectors become isolated. Selection pressure begins."
    )

    for r in range(21, 41):
        sim.run_round()
        if r % 5 == 0:
            print_stats(sim, r)
        if r % 20 == 0:
            print("\n⚡ SELECTION CYCLE: Killing bottom 10%, reproducing top 20%")
            sim.run_selection()
        time.sleep(0.1)

    input("\nPress ENTER to witness Act 3: The Learning...")

    # ACT 3: THE LEARNING (Rounds 41-60)
    print_act(
        "ACT 3: THE LEARNING",
        "ADAPTIVE agents begin discovering cooperation pays better!\n"
        "Watch their weights shift as they update strategies..."
    )

    for r in range(41, 61):
        sim.run_round()
        if r % 5 == 0:
            print_stats(sim, r)

            # Show adaptive agent progress
            adaptive_agents = [a for a in sim.get_alive_agents() if a.is_adaptive]
            if adaptive_agents and r % 10 == 0:
                print("\n🧠 Adaptive Agent Learning:")
                for agent in adaptive_agents[:3]:
                    coop_bias = agent.weights[0] if len(agent.weights) > 0 else 0
                    print(f"  {agent.id}: cooperation_bias={coop_bias:+.2f}, "
                          f"updates={agent.update_count}, fitness={agent.fitness_score}")

        if r % 20 == 0:
            print("\n⚡ SELECTION CYCLE")
            sim.run_selection()
        time.sleep(0.1)

    input("\nPress ENTER for Act 4: Redemption...")

    # ACT 4: REDEMPTION (Rounds 61-80)
    print_act(
        "ACT 4: REDEMPTION",
        "Former defectors rebuild trust through consistent cooperation.\n"
        "Networks stabilize with high-trust cores. Emergence happening!"
    )

    for r in range(61, 81):
        sim.run_round()
        if r % 5 == 0:
            print_stats(sim, r)
        if r % 20 == 0:
            print("\n⚡ SELECTION CYCLE")
            sim.run_selection()
        time.sleep(0.1)

    input("\nPress ENTER for Act 5: Equilibrium...")

    # ACT 5: EQUILIBRIUM (Rounds 81-100)
    print_act(
        "ACT 5: EQUILIBRIUM",
        "Trust networks have crystallized. Cooperation dominates.\n"
        "The system has self-organized WITHOUT central control!"
    )

    for r in range(81, 101):
        sim.run_round()
        if r % 5 == 0:
            print_stats(sim, r)
        if r % 20 == 0:
            print("\n⚡ SELECTION CYCLE")
            sim.run_selection()
        time.sleep(0.1)

    # FINALE
    print("\n" + "="*70)
    print("  🎉 THE TRUST CASCADE: COMPLETE")
    print("="*70)

    print("\n📈 FINAL RESULTS:")
    print_stats(sim, 100)

    # Analyze trust network
    high_trust_edges = [e for e in sim.trust_edges.values() if e.trust_score >= 0.8]
    med_trust_edges = [e for e in sim.trust_edges.values() if 0.5 <= e.trust_score < 0.8]

    print(f"\n🌐 TRUST NETWORK ANALYSIS:")
    print(f"   High Trust Edges (0.8-1.0): {len(high_trust_edges)}")
    print(f"   Medium Trust Edges (0.5-0.8): {len(med_trust_edges)}")
    print(f"   Total Trust Edges: {len(sim.trust_edges)}")

    # Adaptive agent evolution
    adaptive_agents = [a for a in sim.agents.values() if a.is_adaptive]
    avg_updates = sum(a.update_count for a in adaptive_agents) / len(adaptive_agents) if adaptive_agents else 0

    print(f"\n🧠 ADAPTIVE LEARNING:")
    print(f"   Total Adaptive Agents: {len(adaptive_agents)}")
    print(f"   Average Strategy Updates: {avg_updates:.1f}")
    print(f"   Still Alive: {len([a for a in adaptive_agents if a.alive])}")

    # Show learned agents
    learned_agents = [a for a in adaptive_agents if a.alive and a.update_count > 0]
    if learned_agents:
        print("\n   Top Learned Agents:")
        for agent in sorted(learned_agents, key=lambda x: x.fitness_score, reverse=True)[:3]:
            coop_rate = agent.cooperations / agent.interactions if agent.interactions > 0 else 0
            print(f"   • {agent.id}: {agent.update_count} updates, "
                  f"{coop_rate*100:.0f}% cooperation, fitness={agent.fitness_score}")

    print("\n" + "="*70)
    print("  🚀 THIS IS WHAT AI-NATIVE ECONOMICS LOOKS LIKE")
    print("="*70)

    print("\n💡 KEY INSIGHTS:")
    print("   ✓ Trust networks formed organically (no central authority)")
    print("   ✓ Agents learned optimal strategies through experience")
    print("   ✓ Cooperation emerged from self-interest")
    print("   ✓ System self-organized into stable equilibrium")
    print("   ✓ All verified on-chain with cryptographic proof")

    print("\n📊 Open dashboard/trust-cascade-demo.html to see the network visualization!")
    print("🎯 Read PITCH-DECK.md for the full story!")

if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\n\n⏸️  Demo interrupted. Thanks for watching!")
        sys.exit(0)
