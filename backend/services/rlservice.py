"""
rlservice.py - Reinforcement Learning Optimization Agent
─────────────────────────────────────────────────────────
Uses a tabular Q-learning agent (no gym dependency required) that:
  - Learns which optimization strategy works best for each FPGA design profile
  - Updates Q-table after each real design upload (actual reward signal)
  - Persists and reloads Q-table across sessions

State space: discretized (timing_risk, power_risk, congestion, drc_flag)
Action space: 5 optimization strategies (maps to Vivado strategy strings)
Reward: improvement in health_score after applying strategy
"""

import os
import json
import logging
import numpy as np
from typing import Dict, Any, Tuple, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RL_AGENT_PATH, MODEL_FOLDER

logger = logging.getLogger(__name__)

# ─── Q-Table persistence path ─────────────────────────────────────────────────
QTABLE_PATH = os.path.join(MODEL_FOLDER, "rlagent", "qtable.json")
os.makedirs(os.path.dirname(QTABLE_PATH), exist_ok=True)

# ─── Action Space ─────────────────────────────────────────────────────────────
ACTIONS = [
    "Performance_Explore",
    "Performance_NetDelay_high",
    "Congestion_SpreadLogic_high",
    "Power_DefaultOpt",
    "Flow_RuntimeOptimized",
]
N_ACTIONS = len(ACTIONS)

# ─── Hyperparameters ──────────────────────────────────────────────────────────
ALPHA      = 0.15   # learning rate
GAMMA      = 0.90   # discount factor
EPSILON    = 0.10   # exploration rate (decays over time)
MIN_EPSILON = 0.02


class FPGAQLearningAgent:
    """Tabular Q-Learning agent for FPGA optimization strategy selection."""

    def __init__(self):
        self.q_table: Dict[str, list] = {}
        self.episode_count: int = 0
        self.epsilon = EPSILON
        self._load()

    def _state_key(self, features: Dict) -> str:
        """Discretize continuous features into a string state key."""
        wns   = features.get("worst_negative_slack_ns", 0)
        power = features.get("total_power_w", 5)
        cong  = features.get("congested_regions_count", 0)
        drc   = int(features.get("drc_error_flag", 0))

        t_risk = 0 if wns >= 0 else (1 if wns > -0.5 else (2 if wns > -1.5 else 3))
        p_risk = 0 if power < 3 else (1 if power < 6 else (2 if power < 10 else 3))
        c_risk = 0 if cong == 0 else (1 if cong <= 3 else 2)
        return f"{t_risk}_{p_risk}_{c_risk}_{drc}"

    def _get_q(self, state: str) -> list:
        if state not in self.q_table:
            self.q_table[state] = [0.0] * N_ACTIONS
        return self.q_table[state]

    def select_action(self, features: Dict) -> Tuple[int, str]:
        """ε-greedy action selection."""
        state = self._state_key(features)
        if np.random.random() < self.epsilon:
            idx = np.random.randint(N_ACTIONS)
        else:
            q = self._get_q(state)
            idx = int(np.argmax(q))
        return idx, ACTIONS[idx]

    def update(self, features_before: Dict, action_idx: int,
               reward: float, features_after: Dict):
        """Q-Table update after observing actual reward."""
        s  = self._state_key(features_before)
        s2 = self._state_key(features_after)
        q  = self._get_q(s)
        q2 = self._get_q(s2)
        # Q(s,a) ← Q(s,a) + α[r + γ max Q(s',·) - Q(s,a)]
        q[action_idx] += ALPHA * (reward + GAMMA * max(q2) - q[action_idx])
        self.q_table[s] = q
        self.episode_count += 1
        # Decay epsilon
        self.epsilon = max(MIN_EPSILON, EPSILON * (0.995 ** self.episode_count))
        self._save()
        logger.info(f"RL update: state={s}, action={ACTIONS[action_idx]}, reward={reward:.2f}")

    def _save(self):
        try:
            with open(QTABLE_PATH, "w") as f:
                json.dump({"q_table": self.q_table, "episodes": self.episode_count,
                           "epsilon": self.epsilon}, f)
        except Exception as e:
            logger.warning(f"Q-table save failed: {e}")

    def _load(self):
        try:
            if os.path.exists(QTABLE_PATH):
                with open(QTABLE_PATH) as f:
                    data = json.load(f)
                self.q_table   = data.get("q_table", {})
                self.episode_count = data.get("episodes", 0)
                self.epsilon   = data.get("epsilon", EPSILON)
                logger.info(f"Q-table loaded: {len(self.q_table)} states, {self.episode_count} episodes")
        except Exception as e:
            logger.warning(f"Q-table load failed: {e}")

    def get_best_strategy_for(self, features: Dict) -> Dict[str, Any]:
        state = self._state_key(features)
        q = self._get_q(state)
        best_idx = int(np.argmax(q))
        confidence = float(np.exp(q[best_idx]) / sum(np.exp(q_i) for q_i in q) if any(q) else 1/N_ACTIONS)
        return {
            "strategy":       ACTIONS[best_idx],
            "action_idx":     best_idx,
            "q_values":       {a: round(v, 3) for a, v in zip(ACTIONS, q)},
            "episodes_seen":  self.episode_count,
            "confidence":     round(confidence, 3),
            "exploration_rate": round(self.epsilon, 4),
        }

    def compute_reward(self, features_before: Dict, features_after: Dict) -> float:
        """Compute reward signal: α*slack_improvement + β*power_reduction - γ*area_increase."""
        α, β, γ = 2.0, 1.5, 0.5
        slack_delta = (features_after.get("worst_negative_slack_ns", 0)
                       - features_before.get("worst_negative_slack_ns", 0))
        power_delta = (features_before.get("total_power_w", 0)
                       - features_after.get("total_power_w", 0))
        lut_delta   = (features_after.get("lut_util_percent", 0)
                       - features_before.get("lut_util_percent", 0))
        return α * slack_delta + β * power_delta - γ * max(0, lut_delta)


# ─── Singleton agent ──────────────────────────────────────────────────────────
_agent: Optional[FPGAQLearningAgent] = None


def load_agent():
    global _agent
    _agent = FPGAQLearningAgent()
    logger.info("RL Q-Learning agent initialized.")


def get_agent() -> FPGAQLearningAgent:
    global _agent
    if _agent is None:
        _agent = FPGAQLearningAgent()
    return _agent


def get_rl_recommendation(features: Dict[str, Any]) -> Dict[str, Any]:
    agent = get_agent()
    result = agent.get_best_strategy_for(features)
    result["source"] = "q_learning"
    return result


def record_outcome(features_before: Dict, action_idx: int, features_after: Dict):
    """Call this when a new design is uploaded after an RL strategy was applied."""
    agent = get_agent()
    reward = agent.compute_reward(features_before, features_after)
    agent.update(features_before, action_idx, reward, features_after)
    return reward


