"""
AEZ Evolution - Simulation Engine

Runs the evolutionary simulation with agents playing prisoner's dilemma.
"""

import random
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from strategies import (
    Strategy, Action, InteractionHistory, 
    get_strategy, calculate_payoff, STRATEGIES
)


console = Console()


@dataclass
class Agent:
    """A mortal agent instance"""
    id: str
    genome_id: str
    strategy: Strategy
    compute_balance: int
    generation: int = 0
    fitness_score: int = 0
    interactions: int = 0
    cooperations: int = 0
    defections: int = 0
    alive: bool = True
    spawned_at: datetime = field(default_factory=datetime.now)
    history: dict[str, InteractionHistory] = field(default_factory=dict)
    
    def get_history_with(self, opponent_id: str) -> Optional[InteractionHistory]:
        return self.history.get(opponent_id)
    
    def record_interaction(self, opponent_id: str, my_action: Action, their_action: Action):
        if opponent_id not in self.history:
            self.history[opponent_id] = InteractionHistory(
                agent_id=self.id,
                opponent_id=opponent_id,
                my_actions=[],
                opponent_actions=[]
            )
        self.history[opponent_id].my_actions.append(my_action)
        self.history[opponent_id].opponent_actions.append(their_action)
        
        self.interactions += 1
        if my_action == Action.COOPERATE:
            self.cooperations += 1
        else:
            self.defections += 1


@dataclass
class Genome:
    """Immortal strategy template"""
    id: str
    name: str
    strategy_name: str
    generation: int = 0
    total_spawned: int = 0
    total_fitness: int = 0


@dataclass
class Commitment:
    """A pending interaction between two agents"""
    agent_a: Agent
    agent_b: Agent
    stake: int
    action_a: Optional[Action] = None
    action_b: Optional[Action] = None
    resolved: bool = False


@dataclass
class RoundResult:
    """Results from a single round"""
    round_number: int
    commitments: int
    total_compute_moved: int
    cooperations: int
    defections: int
    agents_killed: int = 0
    agents_spawned: int = 0


class Simulation:
    """Main simulation engine"""
    
    def __init__(self, initial_compute: int = 1000, stake_size: int = 100):
        self.genomes: dict[str, Genome] = {}
        self.agents: dict[str, Agent] = {}
        self.round_number: int = 0
        self.initial_compute = initial_compute
        self.stake_size = stake_size
        self.history: list[RoundResult] = []
        self.events: list[dict] = []
        
    def create_genome(self, name: str, strategy_name: str) -> Genome:
        """Create a new genome"""
        genome_id = f"genome_{len(self.genomes)}"
        genome = Genome(
            id=genome_id,
            name=name,
            strategy_name=strategy_name
        )
        self.genomes[genome_id] = genome
        self._emit("GenomeCreated", {"genome_id": genome_id, "name": name, "strategy": strategy_name})
        return genome
    
    def spawn_agent(self, genome: Genome) -> Agent:
        """Spawn a new agent from a genome"""
        agent_id = f"agent_{len(self.agents)}"
        agent = Agent(
            id=agent_id,
            genome_id=genome.id,
            strategy=get_strategy(genome.strategy_name),
            compute_balance=self.initial_compute,
            generation=genome.generation
        )
        self.agents[agent_id] = agent
        genome.total_spawned += 1
        
        self._emit("AgentSpawned", {
            "agent_id": agent_id, 
            "genome_id": genome.id,
            "strategy": genome.strategy_name,
            "generation": agent.generation
        })
        return agent
    
    def kill_agent(self, agent: Agent):
        """Kill an agent"""
        if not agent.alive:
            return
        agent.alive = False
        genome = self.genomes[agent.genome_id]
        genome.total_fitness += agent.fitness_score
        
        self._emit("AgentKilled", {
            "agent_id": agent.id,
            "final_fitness": agent.fitness_score,
            "interactions": agent.interactions
        })
    
    def get_alive_agents(self) -> list[Agent]:
        """Get all living agents"""
        return [a for a in self.agents.values() if a.alive]
    
    def run_commitment(self, agent_a: Agent, agent_b: Agent) -> tuple[int, int]:
        """Run a single commitment between two agents"""
        stake = min(self.stake_size, agent_a.compute_balance, agent_b.compute_balance)
        if stake <= 0:
            return 0, 0
        
        # Agents decide based on history
        history_a = agent_a.get_history_with(agent_b.id)
        history_b = agent_b.get_history_with(agent_a.id)
        
        action_a = agent_a.strategy.decide(history_a)
        action_b = agent_b.strategy.decide(history_b)
        
        # Calculate payoffs
        payoff_a, payoff_b = calculate_payoff(action_a, action_b)
        
        # Apply payoffs (scaled by stake)
        reward_a = (payoff_a * stake) // 3  # Normalize around stake
        reward_b = (payoff_b * stake) // 3
        
        # Update balances
        agent_a.compute_balance = agent_a.compute_balance - stake + reward_a
        agent_b.compute_balance = agent_b.compute_balance - stake + reward_b
        
        # Record history
        agent_a.record_interaction(agent_b.id, action_a, action_b)
        agent_b.record_interaction(agent_a.id, action_b, action_a)
        
        # Update fitness
        agent_a.fitness_score = agent_a.compute_balance
        agent_b.fitness_score = agent_b.compute_balance
        
        self._emit("CommitmentResolved", {
            "agent_a": agent_a.id,
            "agent_b": agent_b.id,
            "action_a": action_a.name,
            "action_b": action_b.name,
            "reward_a": reward_a,
            "reward_b": reward_b
        })
        
        return (1 if action_a == Action.COOPERATE else 0,
                1 if action_b == Action.COOPERATE else 0)
    
    def run_round(self) -> RoundResult:
        """Run a single round of the simulation"""
        self.round_number += 1
        alive = self.get_alive_agents()
        
        if len(alive) < 2:
            return RoundResult(self.round_number, 0, 0, 0, 0)
        
        # Shuffle and pair up
        random.shuffle(alive)
        pairs = [(alive[i], alive[i+1]) for i in range(0, len(alive) - 1, 2)]
        
        total_cooperations = 0
        total_defections = 0
        total_compute = 0
        
        for agent_a, agent_b in pairs:
            coops_a, coops_b = self.run_commitment(agent_a, agent_b)
            total_cooperations += coops_a + coops_b
            total_defections += (2 - coops_a - coops_b)
            total_compute += self.stake_size * 2
        
        result = RoundResult(
            round_number=self.round_number,
            commitments=len(pairs),
            total_compute_moved=total_compute,
            cooperations=total_cooperations,
            defections=total_defections
        )
        self.history.append(result)
        return result
    
    def selection_cycle(self, kill_bottom_pct: float = 0.1, reproduce_top_pct: float = 0.2):
        """Run natural selection: kill bottom performers, reproduce top performers"""
        alive = self.get_alive_agents()
        if len(alive) < 5:
            return 0, 0
        
        # Sort by fitness
        sorted_agents = sorted(alive, key=lambda a: a.fitness_score)
        
        # Kill bottom performers
        kill_count = max(1, int(len(sorted_agents) * kill_bottom_pct))
        killed = 0
        for agent in sorted_agents[:kill_count]:
            self.kill_agent(agent)
            killed += 1
        
        # Reproduce top performers
        reproduce_count = max(1, int(len(sorted_agents) * reproduce_top_pct))
        spawned = 0
        for agent in sorted_agents[-reproduce_count:]:
            genome = self.genomes[agent.genome_id]
            self.spawn_agent(genome)
            spawned += 1
        
        self._emit("SelectionCycle", {
            "killed": killed,
            "spawned": spawned,
            "population": len(self.get_alive_agents())
        })
        
        return killed, spawned
    
    def _emit(self, event_type: str, data: dict):
        """Emit an event"""
        self.events.append({
            "type": event_type,
            "round": self.round_number,
            "timestamp": datetime.now().isoformat(),
            **data
        })
    
    def print_status(self):
        """Print current simulation status"""
        alive = self.get_alive_agents()
        
        table = Table(title=f"Round {self.round_number} Status")
        table.add_column("Strategy", style="cyan")
        table.add_column("Alive", justify="right")
        table.add_column("Avg Fitness", justify="right")
        table.add_column("Avg Coop%", justify="right")
        
        strategy_stats = {}
        for agent in alive:
            name = agent.strategy.name
            if name not in strategy_stats:
                strategy_stats[name] = {"count": 0, "fitness": 0, "coop_rate": 0}
            strategy_stats[name]["count"] += 1
            strategy_stats[name]["fitness"] += agent.fitness_score
            if agent.interactions > 0:
                strategy_stats[name]["coop_rate"] += agent.cooperations / agent.interactions
        
        for name, stats in sorted(strategy_stats.items(), key=lambda x: -x[1]["count"]):
            count = stats["count"]
            avg_fitness = stats["fitness"] // count if count > 0 else 0
            avg_coop = (stats["coop_rate"] / count * 100) if count > 0 else 0
            table.add_row(name, str(count), str(avg_fitness), f"{avg_coop:.1f}%")
        
        console.print(table)
        console.print(f"Total alive: {len(alive)}")


def run_demo():
    """Run a quick demo simulation"""
    console.print("[bold green]🧬 AEZ Evolution Demo[/bold green]\n")
    
    sim = Simulation(initial_compute=1000, stake_size=100)
    
    # Create genomes for each strategy
    strategies = ["Cooperator", "Defector", "TitForTat", "Grudger", "Random"]
    genomes = []
    
    console.print("[cyan]Creating genomes...[/cyan]")
    for strategy_name in strategies:
        genome = sim.create_genome(f"{strategy_name}-Prime", strategy_name)
        genomes.append(genome)
        console.print(f"  Created {genome.name}")
    
    # Spawn agents
    console.print("\n[cyan]Spawning agents...[/cyan]")
    for genome in genomes:
        for i in range(10):  # 10 agents per strategy = 50 total
            sim.spawn_agent(genome)
    console.print(f"  Spawned {len(sim.agents)} agents")
    
    # Run simulation
    console.print("\n[cyan]Running simulation...[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running rounds...", total=100)
        
        for round_num in range(1, 101):
            result = sim.run_round()
            progress.update(task, advance=1, description=f"Round {round_num}")
            
            # Selection every 20 rounds
            if round_num % 20 == 0:
                killed, spawned = sim.selection_cycle()
                console.print(f"\n[yellow]Selection @ round {round_num}: killed {killed}, spawned {spawned}[/yellow]")
                sim.print_status()
    
    # Final status
    console.print("\n[bold green]Final Results:[/bold green]")
    sim.print_status()
    
    # Show top agents
    alive = sim.get_alive_agents()
    top_5 = sorted(alive, key=lambda a: -a.fitness_score)[:5]
    
    console.print("\n[bold]Top 5 Agents:[/bold]")
    for i, agent in enumerate(top_5, 1):
        console.print(f"  {i}. {agent.strategy.name}: fitness={agent.fitness_score}, interactions={agent.interactions}")
    
    return sim


if __name__ == "__main__":
    run_demo()
