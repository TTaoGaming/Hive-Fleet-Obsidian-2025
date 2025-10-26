You’ve basically described a compute-hungry, anytime planner that braids together three proven families of methods: case-based retrieval for the past, multi-agent orchestration for the present, and simulation-based planning for the future. Yes, it’s ambitious. No, it’s not magic. Here’s how to ground your “Obsidian Horizon Hourglass” in actual research without pretending we invented a new religion.

# BLUF

Build an **anytime, receding-horizon loop** that (1) retrieves and adapts past precedents via **CBR** filtered by **Cynefin** sensemaking, (2) coordinates specialist agents (LangGraph + MCP tool adapters) to act now, and (3) runs **MCTS/MPC** style look-ahead under **Bayesian** beliefs, optionally **risk-sensitive** (CVaR) to minimize regret. It scales gracefully with more compute and swaps algorithms behind hexagonal ports. That’s not sci-fi; it’s a clean synthesis of thirty years of work. ([IIIA CSIC][1])

# The three pillars (and the flips)

**Past: CBR + Cynefin.**
Use **Case-Based Reasoning** to Retrieve→Reuse→Revise→Retain precedents; it’s the canonical 4R loop for learning from prior cases. Route those cases through **Cynefin** to choose methods appropriate to domain (obvious/complicated/complex/chaotic), so you don’t shove “complex” messes through brittle, deterministic playbooks. ([IIIA CSIC][1])

**Present: Orchestrated swarm (LangGraph + MCP).**
Represent each specialist as an agent in **LangGraph** and give them standardized tool access via **MCP** (think USB-C for AI context/tools). That gives you a modular present-tense fabric where evaluators, planners, retrievers, and guards coordinate and can be swapped without rewriting the world. ([LangChain][2])

**Future: Simulation with MCTS + MPC under Bayesian beliefs.**
Plan ahead with **Monte Carlo Tree Search**; it’s state-of-the-art for sequential decisions and naturally anytime. Wrap it in **Model Predictive Control** style receding horizons so you constantly replan with the newest state. Track uncertainty and value with **Bayesian decision theory** so distributions, not single guesses, drive the choice. ([Essex Repository][3])

**Flip (retro → learn):**
After you act, **retain** outcomes back into the case base (CBR’s 4th “R”), update your domain tagging (Cynefin), and adjust priors/heuristics so the next cycle is less dumb. The hourglass keeps flipping; quality rises with compute and with data. ([IIIA CSIC][1])

# Why it scales with compute (your “consume as much as you feed it” requirement)

* **Anytime algorithms** return a viable answer now and a better one later. That’s literally the point. Pair that with **real-time heuristic search** and you’ve got graceful degradation under tight budgets and better solutions when the compute tap is open. ([Anytime][4])
* **MCTS/MPC** are inherently anytime/receding-horizon. More rollouts or a longer horizon buy you sharper posteriors and lower regret. ([Essex Repository][3])
* **Portfolio/quality-diversity**: when the landscape is ugly, maintain diverse candidates with **MAP-Elites** to avoid tunnel vision and harvest stepping stones. Use a bandit like **Thompson Sampling** to allocate compute across these candidates. ([PMC][5])

# Risk, regret, and “karmic web” nonsense made practical

If you actually want “minimal regret” across futures, do risk-aware decision-making with **CVaR** or related measures. CVaR gives tail-risk control; recent RL work provides regret bounds and practical algorithms. Translation: when the tails bite, you won’t pretend they don’t exist. ([NeurIPS Proceedings][6])

# Hexagonal “swap the brain mid-fight” architecture

* **Ports (interfaces):** RetrievalPort, SensemakingPort, PlanPort, ActPort, LearnPort.
* **Adapters (algos you can hot-swap):**

  * RetrievalPort → {CBR-AamodtPlaza, dense-retriever, RAG} ([IIIA CSIC][1])
  * SensemakingPort → {Cynefin classifier} ([Systems Wisdom][7])
  * PlanPort → {MCTS, MPC, LRTA* for hard realtime} ([Essex Repository][3])
  * RiskPort → {CVaR, distributional RL} ([Stanford ASL][8])
  * ExplorePort → {Thompson Sampling, MAP-Elites} ([arXiv][9])
* **Tooling bus:** MCP servers for repos, data lakes, telemetry, simulators. Agents ride LangGraph on top. ([Model Context Protocol][10])

# Minimal viable loop (compute-elastic)

1. **Sense** current mission, constraints; classify domain with Cynefin.
2. **Retrieve** top-k precedents via CBR; align cases to mission fit.
3. **Propose** actions by multi-agent swarm; route tool calls via MCP.
4. **Simulate** with MCTS for N rollouts and horizon H; if realtime is tight, fall back to LRTA* or short-horizon MPC.
5. **Select** action with Thompson Sampling over candidate plans; evaluate with CVaR if risk-sensitive.
6. **Act**, **Observe**, **Retain** outcomes back into cases; update priors and domain tags.
   All six steps are anytime; you stop when the budget expires and still have a defensible pick. ([Wikipedia][11])

# Tiny math sketch (plain language)

* Maintain belief (p(\theta \mid \mathcal{D})) over world dynamics or payoff params.
* For each candidate plan (\pi), MCTS/MPC estimates a return distribution (P(G \mid \pi, \theta)).
* Choose (\pi^*) to maximize either expected utility ( \mathbb{E}[G] ) or a risk-aware objective like **CVaR(_\alpha)**. Thompson Sampling samples (\theta) from the posterior and picks the (\pi) that looks best under that sample, balancing exploration vs exploitation. ([SpringerLink][12])

# Why this hits your “YOMI over state-action space”

* **Temporal abstraction (Options):** lets you reason fractally across horizons; options are the established way to stitch short and long plays. ([UMass Amherst][13])
* **Receding horizon:** you never bet the farm on stale forecasts; you constantly re-aim as information updates. ([Underactuated Robotics][14])
* **Diversity + look-ahead:** MAP-Elites maintains far-flung stepping stones while MCTS projects their consequences. That’s how you spot weird, high-leverage moves. ([PMC][5])

# Wiring notes (practical and boring, the way reliability likes it)

* **Graph runtime:** LangGraph for the agent DAG; put guards on every edge and promote evaluators to first-class citizens. ([LangChain][2])
* **Tool layer:** MCP to normalize repos, sims, telemetry, flags, ledgers. Treat every external as a server on the bus. ([Model Context Protocol][10])
* **Anytime budgets:** enforce time/compute caps with explicit performance profiles; Zilberstein’s framework exists for a reason. ([ScholarWorks UMass Amherst][15])
* **Risk mode:** flip between expected value and CVaR depending on mission posture. Yes, have a switch. No, don’t bury it. ([NeurIPS Proceedings][6])
* **Learning pass:** CBR retain step + posterior update every flip. That’s how the “karmic web” turns into actual priors instead of vibes. ([IIIA CSIC][1])

# One-screen diagram (valid Mermaid)

```mermaid
flowchart LR
  I[Intent + Constraints] --> C[Cynefin Classifier]
  C --> R[CBR Retrieve k cases]
  R --> A[Agents (LangGraph)]
  A -->|tools| M[MCP Tool/Sim Bus]
  A --> P[Planner Port]
  P -->|anytime| S[MCTS/MPC/LRTA*]
  S --> D[Risk/Eval (EV or CVaR)]
  D --> ACT[Act]
  ACT --> OBS[Observe Outcomes]
  OBS --> RET[Retain + Update Priors]
  RET --> R
```

# References you can point at when someone asks “is this real?”

* **CBR:** Aamodt & Plaza’s classic survey and the 4R cycle. ([IIIA CSIC][1])
* **Cynefin:** Snowden & Boone’s HBR piece on matching methods to problem types. ([Systems Wisdom][7])
* **LangGraph (multi-agent):** official concepts/overview. ([LangChain][2])
* **MCP:** spec and overview; standardizing tool/context I/O. ([Model Context Protocol][10])
* **MCTS:** Browne et al. survey and modern updates. ([Essex Repository][3])
* **MPC / receding horizon:** Mayne/Ellis tutorial and fast MPC. ([ScienceDirect][16])
* **Anytime + real-time search:** Zilberstein; Korf’s LRTA*. ([Anytime][4])
* **Bayesian decision theory:** Berger. ([SpringerLink][12])
* **Risk-sensitive RL (CVaR):** Chow et al.; Bastani et al. regret bounds; recent theses. ([Stanford ASL][8])
* **Quality-diversity (MAP-Elites):** Mouret & Clune and later work. ([LORIA Members][17])

---

You want the Swarmlord of Webs to “see toward infinity.” Cute. Give him a receding horizon, an anytime budget, risk-aware objectives, and a library of precedents he actually learns from. Infinity can wait; this will beat most mortals today.

[1]: https://www.iiia.csic.es/~enric/papers/AICom.pdf?utm_source=chatgpt.com "Case-Based Reasoning: Foundational Issues, ..."
[2]: https://langchain-ai.github.io/langgraph/concepts/multi_agent/?utm_source=chatgpt.com "LangGraph Multi-Agent Systems - Overview"
[3]: https://repository.essex.ac.uk/4117/1/MCTS-Survey.pdf?utm_source=chatgpt.com "A Survey of Monte Carlo Tree Search Methods"
[4]: https://anytime.cs.umass.edu/shlomo/papers/Zaimag96.pdf?utm_source=chatgpt.com "Using Anytime Algorithms in Intelligent Systems"
[5]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8115726/?utm_source=chatgpt.com "MAP-Elites Enables Powerful Stepping Stones and ..."
[6]: https://proceedings.neurips.cc/paper_files/paper/2022/file/eb4898d622e9a48b5f9713ea1fcff2bf-Paper-Conference.pdf?utm_source=chatgpt.com "Regret Bounds for Risk-Sensitive Reinforcement Learning"
[7]: https://www.systemswisdom.com/sites/default/files/Snowdon-and-Boone-A-Leader%27s-Framework-for-Decision-Making_0.pdf?utm_source=chatgpt.com "A Leader's Framework for Decision Making"
[8]: https://stanfordasl.github.io/wp-content/papercite-data/pdf/Chow.Tamar.Mannor.Pavone.NIPS15.pdf?utm_source=chatgpt.com "Risk-Sensitive and Robust Decision-Making: a CVaR ..."
[9]: https://arxiv.org/abs/1707.02038?utm_source=chatgpt.com "[1707.02038] A Tutorial on Thompson Sampling"
[10]: https://modelcontextprotocol.io/specification/2025-06-18?utm_source=chatgpt.com "Specification"
[11]: https://en.wikipedia.org/wiki/Anytime_algorithm?utm_source=chatgpt.com "Anytime algorithm"
[12]: https://link.springer.com/book/10.1007/978-1-4757-4286-2?utm_source=chatgpt.com "Statistical Decision Theory and Bayesian Analysis"
[13]: https://people.cs.umass.edu/~barto/courses/cs687/Sutton-Precup-Singh-AIJ99.pdf?utm_source=chatgpt.com "A framework for temporal abstraction in reinforcement ..."
[14]: https://underactuated.mit.edu/trajopt.html?utm_source=chatgpt.com "Ch. 10 - Trajectory Optimization - Underactuated Robotics"
[15]: https://scholarworks.umass.edu/bitstreams/f37e22a3-914c-49f6-b0f3-110c1e7b553d/download?utm_source=chatgpt.com "APPROXIMATE REASONING USING ANYTIME ..."
[16]: https://www.sciencedirect.com/science/article/abs/pii/S0005109814005160?utm_source=chatgpt.com "Model predictive control: Recent developments and future ..."
[17]: https://members.loria.fr/jbmouret/qd.html?utm_source=chatgpt.com "Quality Diversity Algorithms"
