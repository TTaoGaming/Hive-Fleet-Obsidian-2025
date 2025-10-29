# MAS scaffold for PettingZoo simple_tag_v3

This scaffold makes it easy to plug in custom logic for each predator and prey.
You can mix heterogeneous predator policies or add a coordinator for hierarchical control.

## Concepts
- BasePolicy: implement `act(obs, ctx) -> action`.
- StepContext: gives you agent name, step, episode, shared dict, and the agent's action/obs spaces.
- MultiAgentController: assigns a policy per `env.agent` and calls it each step.
- Coordinator: optional team-level hooks (before_episode/step, after_step/episode).

## Quick start (random policies)

Run a quick smoke test:

```bash
python scripts/run_pz_custom_mas.py --episodes 5 --seed 7 --continuous --pred-policies random,random --prey-policy random
```

## Per-agent custom hooks

Create a custom predator policy by subclassing `BasePolicy` or wrapping a function with `FnPolicy`:

```python
from hfo_mas.policy_base import BasePolicy, StepContext, FnPolicy

# Subclassing example
class MyPredator(BasePolicy):
    def act(self, obs, ctx: StepContext):
        # obs is a numpy array; return an action compatible with ctx.action_space
        return ctx.action_space.sample()  # TODO: your logic

# Functional style
my_fn = lambda obs, ctx: ctx.action_space.sample()
my_policy = FnPolicy(my_fn)
```

Assign different policies to each predator (heterogeneous):

```python
from hfo_mas.simple_tag_runner import run_episodes
from hfo_mas.policy_base import RandomPolicy

predators = [RandomPolicy(seed=1), RandomPolicy(seed=2), RandomPolicy(seed=3)]
prey = RandomPolicy(seed=4)

res = run_episodes(episodes=10, seed=42, predator_policies=predators, prey_policies=prey)
print(res)
```

## Hierarchical/Team logic

Use a `Coordinator` to share state or impose formations:

```python
from hfo_mas.controllers import Coordinator

class MyCoordinator(Coordinator):
    def before_episode(self, episode, shared):
        shared["formation"] = "spread"

    def before_step(self, t, shared):
        # update shared state or compute waypoints
        pass
```

Then pass it to `run_episodes(..., coordinator=MyCoordinator())`.

## Notes
- The runner infers roles by agent names ("adversary_*" as predators, others as prey).
- Continuous actions are on by default; pass `--discrete` to the CLI to switch.
- Extend `scripts/run_pz_custom_mas.py` to register your own policy names for the CLI, or import and call `run_episodes` directly in Python.
