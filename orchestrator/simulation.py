"""
AEZ Evolution Local Simulation

Runs the evolution simulation locally for rapid testing.
Can be used to validate strategies before on-chain deployment.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import time

from .strategies import (
    Strategy, Action, StrategyState, STRATEGIES,
    get_strategy, calculate_payoff
)


@dataclass
class SimAgent:
    """Simulated agent"""
    id: str
    strategy_name: str
    compute_balance: int
    fitness_score: int = 0
    interactions: int = 0
    cooperations: int = 0
    defections: int = 0
    alive: bool = True
    generation: int = 0
    state: StrategyState = field(default_factory=StrategyState)
    
    @property
    def strategy(self) -> Strategy:
        return get_strategy(self.strategy_name)
    
    def decide(self, opponent_id: str) -> Action:
        return self.strategy.decide(opponent_id, self.state)
    
    def record_opponent_action(self, opponent_id: str, action: Action):
        self.state.record_action(opponent_id, action)
    
    def update_stats(self, action: Action, reward: int):
        self.compute_balance += reward
        self.fitness_score = self.compute_balance
        self.interactions += 1
        if action == Action.COOPERATE:
            self.cooperations += 1
        else:
            self.defections += 1


@dataclass
class SimCommitment:
    """Simulated commitment"""
    agent_a_id: str
    agent_b_id: str
    stake: int
    action_a: Optional[Action] = None
    action_b: Optional[Action] = None
    resolved: bool = False
    reward_a: int = 0
    reward_b: int = 0


@dataclass
class SimEvent:
    """Simulation event for logging"""
    round: int
    event_type: str
    data: Dict


@dataclass
class TrustEdge:
    """Trust edge between two agents"""
    from_agent: str
    to_agent: str
    trust_score: float = 0.5  # Start neutral [0.0, 1.0]
    total_stake_committed: int = 0
    interaction_count: int = 0

    def update(self, both_cooperated: bool, betrayed: bool, stake: int):
        """Update trust based on outcome"""
        if both_cooperated:
            self.trust_score = min(1.0, self.trust_score + 0.1)
        elif betrayed:
            self.trust_score = max(0.0, self.trust_score - 0.2)

        self.total_stake_committed += stake
        self.interaction_count += 1


class Simulation:
    """Local simulation engine"""
    
    def __init__(self, stake: int = 100):
        self.agents: Dict[str, SimAgent] = {}
        self.trust_edges: Dict[Tuple[str, str], TrustEdge] = {}  # (from, to) -> edge
        self.round_number: int = 0
        self.stake: int = stake
        self.events: List[SimEvent] = []
        self.running: bool = False
        self._id_counter: int = 0
    
    def create_agent(self, strategy_name: str, initial_compute: int = 1000) -> SimAgent:
        """Create a new agent"""
        self._id_counter += 1
        agent_id = f"agent_{self._id_counter:03d}"
        agent = SimAgent(
            id=agent_id,
            strategy_name=strategy_name,
            compute_balance=initial_compute,
        )
        self.agents[agent_id] = agent
        self._log("agent_created", {"id": agent_id, "strategy": strategy_name})
        return agent
    
    def _log(self, event_type: str, data: Dict):
        self.events.append(SimEvent(
            round=self.round_number,
            event_type=event_type,
            data=data
        ))
    
    def get_alive_agents(self) -> List[SimAgent]:
        return [a for a in self.agents.values() if a.alive]
    
    def run_commitment(self, agent_a: SimAgent, agent_b: SimAgent) -> SimCommitment:
        """Run a single commitment between two agents"""
        commitment = SimCommitment(
            agent_a_id=agent_a.id,
            agent_b_id=agent_b.id,
            stake=self.stake
        )
        
        # Both agents decide
        action_a = agent_a.decide(agent_b.id)
        action_b = agent_b.decide(agent_a.id)
        
        commitment.action_a = action_a
        commitment.action_b = action_b
        
        # Calculate rewards
        reward_a, reward_b = calculate_payoff(action_a, action_b, self.stake)
        commitment.reward_a = reward_a
        commitment.reward_b = reward_b
        
        # Update agents
        # First subtract stake, then add reward
        agent_a.compute_balance -= self.stake
        agent_b.compute_balance -= self.stake
        agent_a.update_stats(action_a, reward_a)
        agent_b.update_stats(action_b, reward_b)
        
        # Record opponent actions for strategy state
        agent_a.record_opponent_action(agent_b.id, action_b)
        agent_b.record_opponent_action(agent_a.id, action_a)

        # Update trust edges (bidirectional)
        self._update_trust(agent_a.id, agent_b.id, action_a, action_b)
        self._update_trust(agent_b.id, agent_a.id, action_b, action_a)

        commitment.resolved = True

        self._log("commitment_resolved", {
            "agent_a": agent_a.id,
            "agent_b": agent_b.id,
            "action_a": action_a.name,
            "action_b": action_b.name,
            "reward_a": reward_a,
            "reward_b": reward_b,
        })

        return commitment

    def _update_trust(self, from_id: str, to_id: str, my_action: Action, their_action: Action):
        """Update trust edge after interaction"""
        edge_key = (from_id, to_id)

        # Create edge if doesn't exist
        if edge_key not in self.trust_edges:
            self.trust_edges[edge_key] = TrustEdge(from_id, to_id)

        edge = self.trust_edges[edge_key]

        # Determine outcome
        both_cooperated = (my_action == Action.COOPERATE and their_action == Action.COOPERATE)
        betrayed = (my_action == Action.COOPERATE and their_action == Action.DEFECT)

        # Update edge
        edge.update(both_cooperated, betrayed, self.stake)
    
    def run_round(self) -> List[SimCommitment]:
        """Run one round - each agent plays against each other agent once"""
        self.round_number += 1
        alive = self.get_alive_agents()
        commitments = []
        
        # Random pairing
        random.shuffle(alive)
        pairs = [(alive[i], alive[i+1]) for i in range(0, len(alive)-1, 2)]
        
        for agent_a, agent_b in pairs:
            if agent_a.compute_balance >= self.stake and agent_b.compute_balance >= self.stake:
                commitment = self.run_commitment(agent_a, agent_b)
                commitments.append(commitment)
        
        self._log("round_complete", {
            "round": self.round_number,
            "commitments": len(commitments),
            "alive": len(alive)
        })
        
        return commitments
    
    def run_selection(self, kill_bottom_pct: float = 0.1, reproduce_top_pct: float = 0.2):
        """Selection pressure: kill worst performers, reproduce best"""
        alive = self.get_alive_agents()
        alive.sort(key=lambda a: a.fitness_score, reverse=True)
        
        n_alive = len(alive)
        n_kill = max(1, int(n_alive * kill_bottom_pct))
        n_reproduce = max(1, int(n_alive * reproduce_top_pct))
        
        # Kill bottom performers
        killed = []
        for agent in alive[-n_kill:]:
            agent.alive = False
            killed.append(agent.id)
        
        # Reproduce top performers
        reproduced = []
        for agent in alive[:n_reproduce]:
            child = self.create_agent(
                strategy_name=agent.strategy_name,
                initial_compute=1000  # Fresh start
            )
            child.generation = agent.generation + 1
            reproduced.append(child.id)
        
        self._log("selection", {
            "killed": killed,
            "reproduced": reproduced,
            "survivors": n_alive - n_kill
        })
    
    def get_strategy_distribution(self) -> Dict[str, int]:
        """Count agents per strategy"""
        dist = {}
        for agent in self.get_alive_agents():
            name = agent.strategy_name
            dist[name] = dist.get(name, 0) + 1
        return dist
    
    def get_leaderboard(self, limit: int = 10) -> List[SimAgent]:
        """Get top agents by fitness"""
        alive = self.get_alive_agents()
        alive.sort(key=lambda a: a.fitness_score, reverse=True)
        return alive[:limit]
    
    def get_status(self) -> Dict:
        """Get simulation status"""
        return {
            "round_number": self.round_number,
            "total_agents": len(self.agents),
            "alive_agents": len(self.get_alive_agents()),
            "running": self.running,
            "events_count": len(self.events),
            "strategies": [
                {"name": k, "count": v}
                for k, v in sorted(self.get_strategy_distribution().items())
            ]
        }

    def get_trust_network(self) -> Dict:
        """Get trust network data for visualization"""
        nodes = []
        for agent in self.agents.values():
            coop_rate = agent.cooperations / agent.interactions if agent.interactions > 0 else 0.5
            nodes.append({
                "id": agent.id,
                "strategy": agent.strategy_name,
                "fitness": agent.fitness_score,
                "compute": agent.compute_balance,
                "alive": agent.alive,
                "interactions": agent.interactions,
                "cooperations": agent.cooperations,
                "defections": agent.defections,
                "cooperation_rate": coop_rate
            })

        edges = []
        for (from_id, to_id), edge in self.trust_edges.items():
            # Only include edges with actual interactions
            if edge.interaction_count > 0:
                edges.append({
                    "source": from_id,
                    "target": to_id,
                    "trust": edge.trust_score,
                    "interactions": edge.interaction_count,
                    "total_stake": edge.total_stake_committed
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "round": self.round_number
        }


def create_default_simulation() -> Simulation:
    """Create simulation with default agent mix"""
    sim = Simulation(stake=100)

    # Create agents of each strategy (50 total: 10 of first 5, then 5 each of the remaining 2)
    for strategy_name in ["Cooperator", "Defector", "TitForTat", "Grudger", "Random"]:
        for _ in range(10):
            sim.create_agent(strategy_name, initial_compute=1000)

    # Add the additional strategies with fewer agents to keep total at ~50
    for strategy_name in ["Pavlov", "SuspiciousTitForTat"]:
        for _ in range(5):
            sim.create_agent(strategy_name, initial_compute=1000)

    return sim


def run_experiment(rounds: int = 100, selection_interval: int = 20):
    """Run a full experiment"""
    sim = create_default_simulation()
    
    print(f"Starting experiment: {len(sim.agents)} agents, {rounds} rounds")
    print(f"Selection every {selection_interval} rounds")
    print()
    
    for r in range(1, rounds + 1):
        sim.run_round()
        
        if r % selection_interval == 0:
            print(f"Round {r}: Selection cycle")
            sim.run_selection()
        
        if r % 10 == 0:
            dist = sim.get_strategy_distribution()
            print(f"Round {r}: {dict(sorted(dist.items()))}")
    
    print()
    print("Final Results:")
    print("-" * 40)
    
    dist = sim.get_strategy_distribution()
    for name, count in sorted(dist.items(), key=lambda x: -x[1]):
        pct = count / len(sim.get_alive_agents()) * 100
        print(f"  {name}: {count} ({pct:.1f}%)")
    
    print()
    print("Leaderboard:")
    for i, agent in enumerate(sim.get_leaderboard(5), 1):
        print(f"  {i}. {agent.id} ({agent.strategy_name}): {agent.fitness_score}")
    
    return sim


if __name__ == "__main__":
    run_experiment()
