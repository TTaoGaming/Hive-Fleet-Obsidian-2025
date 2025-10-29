# HFO PettingZoo MAS scaffold (simple_tag_v3)

This scaffold makes it easy to plug in custom logic for each predator and prey.
You can mix heterogeneous predator policies or add a coordinator for hierarchical control.

## Concepts
- BasePolicy: implement `act(obs, ctx) -> action`.
- StepContext: agent name, step, episode, shared team dict, action/obs spaces, and RNG.
- MultiAgentController: assigns a policy per `env.agent` and calls it each step.
- Coordinator: optional team-level hooks (before_episode/step, after_step/episode).

## Quick start (random policies)

```bash
PYTHONPATH=. python3 scripts/run_pz_custom_mas.py --episodes 5 --seed 7 --continuous --pred-policies random,random --prey-policy random
```

## Per-agent custom hooks

Subclass `BasePolicy` or use `FnPolicy`:

```python
from hfo_petting_zoo_mas.policy_base import BasePolicy, StepContext, FnPolicy

class MyPredator(BasePolicy):
    def act(self, obs, ctx: StepContext):
        return ctx.action_space.sample()  # replace with your logic

my_fn = lambda obs, ctx: ctx.action_space.sample()
my_policy = FnPolicy(my_fn)
```

Heterogeneous predators:

```python
from hfo_petting_zoo_mas.simple_tag_runner import run_episodes
from hfo_petting_zoo_mas.policy_base import RandomPolicy

predators = [RandomPolicy(seed=1), RandomPolicy(seed=2), RandomPolicy(seed=3)]
prey = RandomPolicy(seed=4)

res = run_episodes(episodes=10, seed=42, predator_policies=predators, prey_policies=prey)
print(res)
```

## Coordinator example

```python
from hfo_petting_zoo_mas.controllers import Coordinator

class MyCoordinator(Coordinator):
    def before_episode(self, episode, shared):
        shared["formation"] = "spread"
```

Then pass it to `run_episodes(..., coordinator=MyCoordinator())`.

## Notes
- Role inference: names with `adversary_*` are predators; others are prey.
- Continuous actions default on; use `--discrete` to switch in the CLI.
- Extend `scripts/run_pz_custom_mas.py` to register your own policies by name, or import and use `run_episodes` directly.
