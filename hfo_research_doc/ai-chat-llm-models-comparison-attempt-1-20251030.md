Use a 3-tier roster and hard gates. Cheap “scouts” do the fan-out, a few “reasoners” do fan-in, and one premium verifier breaks ties. Route on OpenRouter with fallbacks so only the successful run bills. ([OpenRouter][1])

# One-page: 10-lane swarm model roster + control

## Roster (prices $/1M tokens; ctx=context)

| Role            | Model                               |            ctx |                                   In / Out | Why use it                                           | Notes                                                                             |
| --------------- | ----------------------------------- | -------------: | -----------------------------------------: | ---------------------------------------------------- | --------------------------------------------------------------------------------- |
| Reasoner        | **DeepSeek R1 (deepseek-reasoner)** |           128k |                                0.28 / 0.42 | Low-cost “thinking” for hard merges and audits       | Tool calls route via chat model; cap “thinking” outputs. ([DeepSeek API Docs][2]) |
| Reasoner        | **Grok 4 Fast – reasoning**         |             2M |          0.20 / 0.50 (≤128k; higher >128k) | Huge context + cheap inputs; good decider            | Long-ctx has different pricing; check tier. ([xAI Docs][3])                       |
| Verifier        | **Claude Sonnet 4.5**               | 200k (1M beta) |                               3.00 / 15.00 | High reliability for final checks and agent control  | Use prompt caching to cut cost. ([Claude][4])                                     |
| Long-ctx worker | **Gemini 2.5 Pro**                  |             1M | 0.625 / 5.00 (≤200k) · 1.25 / 7.50 (>200k) | Reads big bundles; solid tools                       | Use only when you truly need 1M. ([Google AI for Developers][5])                  |
| Cheap bulk      | **Gemini 2.5 Flash**                |             1M |                                0.10 / 0.40 | Fast, low-cost summaries/extract                     | Good default for ingestion lanes. ([Google AI for Developers][5])                 |
| Cheap bulk      | **DeepSeek V3 (deepseek-chat)**     |           128k |                                0.28 / 0.42 | Generalist for wide fan-out                          | Pair with R1 for escalations. ([DeepSeek API Docs][2])                            |
| Cheap bulk      | **GPT-OSS 120B**                    |           131k |                                0.04 / 0.40 | Open-weight, very cheap output; good diversification | Stable for drafting and long doc passes. ([OpenRouter][6])                        |
| Coder           | **MiniMax M2**                      |           196k |                                0.15 / 0.45 | Coding-tuned, efficient agent workflows              | Good SWE lane worker. ([OpenRouter][7])                                           |
| Reasoner-alt    | **Qwen3-Next-80B-A3B (Thinking)**   |           262k |                                0.15 / 1.20 | MoE “thinking” traces; strong multi-step logic       | Cap output length. ([OpenRouter][8])                                              |
| Open anchor     | **Llama 3.1 70B Instruct**          |           131k |                                0.40 / 0.40 | Steady open model; privacy-friendly lanes            | Use for deterministic formats/JSON. ([OpenRouter][9])                             |

Signals that these are “top” today: Artificial Analysis and similar leaderboards track composite quality vs price/speed across 100+ models; use them as a sanity check when swapping peers. ([Artificial Analysis][10])

## CrewAI control pattern (minimal moves)

* **Lane map**: 10 lanes = 6 scouts (Flash, V3, GPT-OSS, M2) + 3 reasoners (R1, Grok-reason, Qwen-Thinking) + 1 verifier (Claude). Promote to Gemini-Pro only when `LONG_CTX` tag is set. Costs drop fast this way. Sources above.
* **Routing**: Use OpenRouter **model routing + fallbacks**; you only pay for the model that succeeds. Encode primary → fallback chains per lane. ([OpenRouter][1])
* **Budgets**: Hard-cap **output tokens** on reasoners and set stricter caps for “thinking” variants. DeepSeek R1 exposes different output limits; respect them. ([DeepSeek API Docs][2])
* **Caching**: Turn on context/prompt caching where offered to cut repeat costs (Gemini; Claude prompt caching). ([Google AI for Developers][5])
* **Health checks**: For any PR or decision, run A/B: one reasoning model + one cheap auditor. Escalate to Claude only on disagreement.

## Pitfalls to avoid

* **Auto-router theater**: Auto selection can under-spec tasks and pick weaker models. Lock explicit routes for high-stakes lanes; use auto only for low-risk scouts. ([datacamp.com][11])
* **Over-context**: Pushing near the max window often degrades quality and changes pricing tiers. Trim to the working set; only enable million-token modes when necessary. ([Google AI for Developers][5])
* **Unbounded “thinking”**: Reasoners can bloat tokens. Keep “thinking” off by default; enable on failure or for decider lanes. DeepSeek documents thinking vs chat behavior explicitly. ([DeepSeek API Docs][2])
* **Single-vendor lock**: Keep at least one open-weight lane (GPT-OSS 120B or Llama 3.1 70B) for resilience and cost spikes. Prices and availability shift; leaderboards help you swap quickly. ([OpenRouter][6])
* **No independent receipts**: Add an external quality gate. Track a rolling win-rate vs a small gold set and price/1k-tokens per lane; adjust routes weekly. (Use Artificial Analysis/Vellum as a second opinion.) ([Vellum AI][12])

## If you change only two things

1. **Adopt the roster above with explicit fallbacks in OpenRouter** and per-lane token caps. ([OpenRouter][1])
2. **Force verify**: cheap scout consensus → single reasoner → Claude only on conflict. Keeps cost low and accuracy high, today’s prices considered. Sources above.

[1]: https://openrouter.ai/docs/features/model-routing?utm_source=chatgpt.com "Model Routing | Dynamic AI Model Selection and Fallback"
[2]: https://api-docs.deepseek.com/quick_start/pricing "Models & Pricing | DeepSeek API Docs"
[3]: https://docs.x.ai/docs/models/grok-4-fast-non-reasoning?utm_source=chatgpt.com "Grok 4 Fast (Non-Reasoning)"
[4]: https://www.claude.com/pricing?utm_source=chatgpt.com "Pricing"
[5]: https://ai.google.dev/gemini-api/docs/pricing?utm_source=chatgpt.com "Gemini Developer API Pricing - Google AI for Developers"
[6]: https://openrouter.ai/openai/gpt-oss-120b?utm_source=chatgpt.com "gpt-oss-120b - API, Providers, Stats"
[7]: https://openrouter.ai/minimax/minimax-m2?utm_source=chatgpt.com "MiniMax M2 - API, Providers, Stats"
[8]: https://openrouter.ai/qwen/qwen3-next-80b-a3b-thinking?utm_source=chatgpt.com "Qwen3 Next 80B A3B Thinking - API, Providers, Stats"
[9]: https://openrouter.ai/meta-llama/llama-3.1-70b-instruct?utm_source=chatgpt.com "Llama 3.1 70B Instruct - API, Providers, Stats"
[10]: https://artificialanalysis.ai/leaderboards/models "LLM Leaderboard - Comparison of over 100 AI models from OpenAI, Google, DeepSeek & others | Artificial Analysis"
[11]: https://www.datacamp.com/tutorial/openrouter?utm_source=chatgpt.com "OpenRouter: A Guide With Practical Examples"
[12]: https://www.vellum.ai/llm-leaderboard?utm_source=chatgpt.com "LLM Leaderboard 2025"
