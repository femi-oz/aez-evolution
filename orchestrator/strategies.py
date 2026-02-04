"""
AEZ Evolution - Agent Strategies

Each strategy decides: Cooperate or Defect?
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import random
import hashlib
import os


class Action(Enum):
    COOPERATE = 0
    DEFECT = 1


@dataclass
class InteractionHistory:
    """History of interactions between two agents"""
    agent_id: str
    opponent_id: str
    my_actions: list[Action]
    opponent_actions: list[Action]
    
    def last_opponent_action(self) -> Optional[Action]:
        return self.opponent_actions[-1] if self.opponent_actions else None
    
    def opponent_ever_defected(self) -> bool:
        return Action.DEFECT in self.opponent_actions


class Strategy(ABC):
    """Base strategy interface"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def decide(self, history: Optional[InteractionHistory]) -> Action:
        """Decide whether to cooperate or defect"""
        pass
    
    def commit(self, action: Action) -> tuple[bytes, bytes]:
        """Create commit hash for action (for commit-reveal scheme)"""
        nonce = os.urandom(32)
        data = bytes([action.value]) + nonce
        commit_hash = hashlib.sha256(data).digest()
        return commit_hash, nonce


class Cooperator(Strategy):
    """Always cooperate - the naive optimist"""
    
    @property
    def name(self) -> str:
        return "Cooperator"
    
    def decide(self, history: Optional[InteractionHistory]) -> Action:
        return Action.COOPERATE


class Defector(Strategy):
    """Always defect - the pure exploiter"""
    
    @property
    def name(self) -> str:
        return "Defector"
    
    def decide(self, history: Optional[InteractionHistory]) -> Action:
        return Action.DEFECT


class TitForTat(Strategy):
    """Mirror opponent's last move - cooperate first, then reciprocate
    
    The legendary strategy that won Axelrod's tournament.
    Nice (cooperates first), retaliatory (punishes defection),
    forgiving (returns to cooperation), and clear (easy to understand).
    """
    
    @property
    def name(self) -> str:
        return "TitForTat"
    
    def decide(self, history: Optional[InteractionHistory]) -> Action:
        if history is None or not history.opponent_actions:
            # First interaction - be nice
            return Action.COOPERATE
        # Mirror opponent's last move
        return history.last_opponent_action()


class Grudger(Strategy):
    """Cooperate until betrayed, then always defect
    
    Also known as "Grim Trigger" - unforgiving but simple.
    """
    
    @property
    def name(self) -> str:
        return "Grudger"
    
    def decide(self, history: Optional[InteractionHistory]) -> Action:
        if history is None:
            return Action.COOPERATE
        if history.opponent_ever_defected():
            return Action.DEFECT
        return Action.COOPERATE


class RandomStrategy(Strategy):
    """50/50 random choice - the baseline"""
    
    @property
    def name(self) -> str:
        return "Random"
    
    def decide(self, history: Optional[InteractionHistory]) -> Action:
        return random.choice([Action.COOPERATE, Action.DEFECT])


class TitForTwoTats(Strategy):
    """Only defect after opponent defects twice in a row
    
    More forgiving than TitForTat - handles noise better.
    """
    
    @property
    def name(self) -> str:
        return "TitForTwoTats"
    
    def decide(self, history: Optional[InteractionHistory]) -> Action:
        if history is None or len(history.opponent_actions) < 2:
            return Action.COOPERATE
        # Only defect if opponent defected last two times
        if (history.opponent_actions[-1] == Action.DEFECT and 
            history.opponent_actions[-2] == Action.DEFECT):
            return Action.DEFECT
        return Action.COOPERATE


class Pavlov(Strategy):
    """Win-stay, lose-shift
    
    Repeat last action if it led to a good outcome (CC or DC),
    switch if it led to a bad outcome (CD or DD).
    """
    
    @property
    def name(self) -> str:
        return "Pavlov"
    
    def decide(self, history: Optional[InteractionHistory]) -> Action:
        if history is None or not history.my_actions:
            return Action.COOPERATE
        
        my_last = history.my_actions[-1]
        their_last = history.last_opponent_action()
        
        # Good outcome = both same action
        if my_last == their_last:
            return my_last  # Win-stay
        else:
            # Lose-shift
            return Action.DEFECT if my_last == Action.COOPERATE else Action.COOPERATE


# Strategy registry
STRATEGIES = {
    "Cooperator": Cooperator,
    "Defector": Defector,
    "TitForTat": TitForTat,
    "Grudger": Grudger,
    "Random": RandomStrategy,
    "TitForTwoTats": TitForTwoTats,
    "Pavlov": Pavlov,
}


def get_strategy(name: str) -> Strategy:
    """Get strategy instance by name"""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}")
    return STRATEGIES[name]()


# Payoff matrix constants
PAYOFF_MATRIX = {
    (Action.COOPERATE, Action.COOPERATE): (3, 3),   # Mutual cooperation
    (Action.COOPERATE, Action.DEFECT): (0, 5),      # Sucker's payoff
    (Action.DEFECT, Action.COOPERATE): (5, 0),      # Temptation
    (Action.DEFECT, Action.DEFECT): (1, 1),         # Mutual defection
}


def calculate_payoff(action_a: Action, action_b: Action) -> tuple[int, int]:
    """Calculate payoff for both players"""
    return PAYOFF_MATRIX[(action_a, action_b)]
