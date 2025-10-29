"""PettingZoo MAS scaffold for MPE simple_tag_v3.

Key pieces:
- BasePolicy: per-agent policy contract (act)
- Coordinator: optional hook for hierarchical/team logic
- MultiAgentController: maps env agents to policies
- simple_tag_runner: utilities to run episodes
"""

from .policy_base import BasePolicy, RandomPolicy, FnPolicy
from .controllers import MultiAgentController, Coordinator
from .heuristics import HeuristicChasePolicy, PreyFleePolicy
