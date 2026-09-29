# The Embodied Harness: a living survey of the systems around robot foundation models

_Living document · revision 2026-09-29 · 890 systems catalogued in [the list](README.md) · kept current by the [daily radar](radar/)_

**TL;DR**

- **The harness matters as much as the model.** For coding agents, 2025–26 made this plain: the loop, tools, context, permissions and tests-as-exit-codes decide much of the outcome. Robots are going through the same decomposition.
- **Definition.** An **embodied harness** is the software between a foundation model and a body. It decides what the model sees, what it can do, how actions execute, how outcomes are checked, and what it is not allowed to do. We organize it into a seven-layer stack (L0–L6) and map 890 systems onto it.
- **Three phases so far:**
  1. LLMs planning over fixed skills (2022–23).
  2. VLAs pulling the loop into the weights (2023–25).
  3. Explicit harnesses around frontier models, with VLAs and other skills as tools (2025–26).
- **What changed in 2026:**
  - "Harness" became the object of study.
  - Unmodified coding agents became credible robot controllers.
  - VLAs became tools inside harnesses rather than replacements for them.
  - Harnesses started to improve themselves and then to distill themselves back into weights.
- **What is open:**
  - **Exit codes** for the physical world.
  - **Where world state lives.**
  - **Latency and asynchrony.**
  - **Safety of tool use.**
  - **Benchmarks that measure harnesses rather than models.**

## Contents

1. [From agent harness to embodied harness](#1-from-agent-harness-to-embodied-harness)
2. [Definition](#2-definition)
3. [The stack](#3-the-stack)
4. [Design dimensions](#4-design-dimensions)
5. [Representative harnesses compared](#5-representative-harnesses-compared)
6. [What 2026 changed](#6-what-2026-changed)
7. [Open problems](#7-open-problems)
8. [Reading path](#8-reading-path)
9. [Statistics](#9-statistics)

---

## 1. From agent harness to embodied harness

In software agents, *harness* names the scaffolding around a model: the control loop, the tool definitions, context management, permissions and sandboxing, and the tests that tell the agent whether it is done. Comparisons published in 2026 found that swapping the harness around a *fixed* model changes both the cost per solved task and *which* tasks get solved (see the ai-radar briefing of [2026-08-07](../807-AI/807-article.md)).

Robotics reached the same place from the other direction.

- **The first language-model robots were harnesses in all but name.**
  - [SayCan](https://arxiv.org/abs/2204.01691) chose among fixed skills by combining language-model likelihood with learned affordance values.
  - [Inner Monologue](https://arxiv.org/abs/2207.05608) closed the loop by feeding success detection and scene descriptions back into the prompt.
  - [Code as Policies](https://arxiv.org/abs/2209.07753) made generated code the action interface.
- **VLAs then pulled much of that loop into the weights.** [RT-2](https://arxiv.org/abs/2307.15818), [OpenVLA](https://arxiv.org/abs/2406.09246), [π0 (pi0)](https://arxiv.org/abs/2410.24164) and their successors map pixels and instructions straight to actions.
- **Dual-system designs split slow deliberation from fast control.** Examples are [Hi Robot](https://arxiv.org/abs/2502.19417), [Helix](https://www.figure.ai/news/helix), [GR00T N1](https://arxiv.org/abs/2503.14734), and [Gemini Robotics 1.5](https://arxiv.org/abs/2510.03342), where an embodied-reasoning model orchestrates a VLA.
- **In 2026 the harness itself became the subject of research.** [Thea](https://arxiv.org/abs/2608.11246) carried the coding-agent harness to robots. Its argument is that the physical world "withholds two abilities that software grants for free: reading the state of the world, and judging the outcome of an action." Around the same time [Zetta](https://arxiv.org/abs/2608.16590), [Show-Harness](https://arxiv.org/abs/2609.10522), [HarnessPAI](https://arxiv.org/abs/2609.29166), [HarnessVLN](https://arxiv.org/abs/2609.15195), [NavHarness](https://arxiv.org/abs/2609.34276), [RegenHarness](https://arxiv.org/abs/2609.27612) and others appeared, many with "harness" in the title.

## 2. Definition

> An **embodied harness** is the software between a foundation model (LLM, VLM, VLA or world model) and a physical, or physically simulated, body. It decides **what the model sees**, **what it can do**, **how actions are executed**, **how outcomes are checked**, and **what it is not allowed to do**.

In scope are the agent loop and orchestration, the action interface, world state and memory, verification and recovery, the safety envelope, human-in-the-loop, and multi-robot coordination. The offline flywheel that shapes a harness is also in scope: simulators, world models, benchmarks, datasets and training infrastructure. The models a harness calls are listed too, because a harness is designed around what its models can and cannot do.

## 3. The stack

| Layer | Role | Coding-agent analogue | Sections of the list |
|---|---|---|---|
| **L6** Evaluation & data flywheel | Build, test and improve the harness offline | CI, eval suites, traces | [Simulators](categories/sim.md), [World models](categories/world-model.md), [Benchmarks](categories/benchmark.md), [Data](categories/data.md) |
| **L5** Verification & safety | Decide whether an action worked, whether it is allowed, and when to ask a human | Tests as exit codes, permission prompts, sandbox | [Verification](categories/verification.md), [Safety](categories/safety.md) |
| **L4** Reasoning & orchestration | The agent loop: plan, call tools, observe, replan, delegate | Agent loop, planner, sub-agents | [Harnesses](categories/harness.md), [Reasoning models](categories/brain.md), [Multi-robot](categories/multi-agent.md) |
| **L3** World state & memory | What the model knows about the world right now and from before | Context window, repo map, memory files | [Memory](categories/memory.md) |
| **L2** Action interface | How capabilities are exposed: skills, code APIs, constraints, protocols | Tool schemas, MCP | [Interfaces](categories/interface.md) |
| **L1** Skill policies | Turn a short command into motor actions | The tools' implementations | [VLA models & policies](categories/policy.md) |
| **L0** Embodiment & middleware | Hardware, drivers, ROS 2, real-time control | OS, filesystem, shell | [Frameworks & runtimes](categories/framework.md) |

The layers are logical, not physical. An end-to-end VLA collapses L1–L4 into one network. A dual-system model spans L1 and L4. A coding-agent-style harness keeps them apart and connects them with explicit interfaces. The most useful question to ask of any system is *which layers it makes explicit, and which it leaves to the weights*.

## 4. Design dimensions

### 4.1 Where does the loop live?

| Design | What the harness does | Examples |
|---|---|---|
| **Model-centric** | Thin wrapper: instruction and observations in, actions out; little or no explicit state | [RT-2](https://arxiv.org/abs/2307.15818), [OpenVLA](https://arxiv.org/abs/2406.09246), [π0 (pi0)](https://arxiv.org/abs/2410.24164) |
| **Hierarchical / dual-system** | A slow reasoning model issues sub-goals or language commands to a fast action model | [Hi Robot](https://arxiv.org/abs/2502.19417), [Helix](https://www.figure.ai/news/helix), [GR00T N1](https://arxiv.org/abs/2503.14734), [Gemini Robotics 1.5](https://arxiv.org/abs/2510.03342) |
| **Harness-centric** | A general model runs an explicit loop over tools, with world state and verification kept outside the model | [Code as Policies](https://arxiv.org/abs/2209.07753), [VoxPoser](https://arxiv.org/abs/2307.05973), [FAEA](https://arxiv.org/abs/2601.20334), [Thea](https://arxiv.org/abs/2608.11246), [Show-Harness](https://arxiv.org/abs/2609.10522) |

### 4.2 What is a "tool call" for a robot?

| Interface | How it works | Examples |
|---|---|---|
| **Pick a skill in language** | Choose from a fixed skill set, scored for feasibility | [SayCan](https://arxiv.org/abs/2204.01691) |
| **Write code** | Programs against perception and control APIs | [Code as Policies](https://arxiv.org/abs/2209.07753), [ProgPrompt](https://arxiv.org/abs/2209.11302) |
| **Emit constraints or value maps** | A motion planner optimizes them | [VoxPoser](https://arxiv.org/abs/2307.05973), [ReKep](https://arxiv.org/abs/2409.01652), [MOKA](https://arxiv.org/abs/2403.03174) |
| **Semantic action units** | Per-robot interpreters ground them deterministically | [Show-Harness](https://arxiv.org/abs/2609.10522) |
| **Instruct a VLA in language** | The VLA executes the step | [Hi Robot](https://arxiv.org/abs/2502.19417), [Gemini Robotics 1.5](https://arxiv.org/abs/2510.03342) |
| **Protocol bridges** | ROS topics, services and actions exposed to any agent | [ROS MCP Server](https://robotmcp.ai/blog/ros-mcp-server-release), [RoboNeuron](https://arxiv.org/abs/2512.10394) |

### 4.3 How is the world represented in context?

| Representation | Examples |
|---|---|
| Raw frames in the prompt | — |
| Text feedback: scene descriptions, success signals | [Inner Monologue](https://arxiv.org/abs/2207.05608) |
| Scene graphs | [SayPlan](https://arxiv.org/abs/2307.06135), [Thea](https://arxiv.org/abs/2608.11246) |
| 3D semantic maps and feature fields | [VLMaps](https://arxiv.org/abs/2210.05714), [ConceptGraphs](https://arxiv.org/abs/2309.16650) |
| Long-term memory: episodic memory, object ledgers | [ReMEmbR](https://arxiv.org/abs/2409.13682), [Ledger](https://arxiv.org/abs/2609.34554) |

The choice decides what the model can reason about, and what goes stale.

### 4.4 Exit codes: how does the harness know it is done?

The ladder of verification runs from nothing to active checks:

1. Open-loop execution.
2. Textual success feedback: [Inner Monologue](https://arxiv.org/abs/2207.05608).
3. Learned success detectors and progress estimators: [GVL](https://arxiv.org/abs/2411.04549).
4. Failure explanation and recovery: [REFLECT](https://arxiv.org/abs/2306.15724), [AHA](https://arxiv.org/abs/2410.00371).
5. Checks before acting:
   - [RoboMonkey](https://arxiv.org/abs/2506.17811) samples candidate actions and has a verifier pick one.
   - [GAVEL](https://arxiv.org/abs/2609.19315) predicts a plan's consequences against a graph world model.
   - [World Action Agent (WAA)](https://arxiv.org/abs/2609.29964) rehearses each action before executing it.
6. Evaluators that detect termination, assess success and diagnose failures before the next step: [Thea](https://arxiv.org/abs/2608.11246).

Physical actions are not idempotent, so verification matters more for robots than for code. There is no `git reset`; the closest analogue is [SafeLoop](https://arxiv.org/abs/2609.26313), which saves safety checkpoints and rolls back in joint space.

### 4.5 The safety envelope

| Layer of the envelope | Examples |
|---|---|
| Affordance gating: only propose feasible skills | [SayCan](https://arxiv.org/abs/2204.01691) |
| Constitutions checked before execution | [AutoRT](https://arxiv.org/abs/2401.12963) |
| Runtime guardrails that check plans against specifications | [RoboGuard](https://arxiv.org/abs/2503.07885) |
| Uncertainty-aware help-seeking | [KnowNo](https://arxiv.org/abs/2307.01928) |

Jailbreak studies on LLM-controlled robots ([RoboPAIR](https://arxiv.org/abs/2410.13691), [BadRobot](https://arxiv.org/abs/2407.20242)) show that the envelope has to live *outside* the model, in the harness and below it.

### 4.6 How does the harness improve?

Options range from static prompts and fixed skills, to growing skill libraries, to **self-evolving harnesses**. The last kind rewrites its own tools, programs, prompts and memory from experience (see §6.5).

## 5. Representative harnesses compared

The table uses only what each system's paper or official post states. "—" means the source does not describe that layer as a distinct component.

| System | Reasoner | Action interface (L2) | World state (L3) | Exit codes / verification (L5) | Improvement loop |
|---|---|---|---|---|---|
| [SayCan](https://arxiv.org/abs/2204.01691) (2022) | LLM | Choose among language-described skills; value functions score feasibility | Implicit in affordance values | — | Static |
| [Inner Monologue](https://arxiv.org/abs/2207.05608) (2022) | LLM | Language skill calls | Text scene descriptions | Success detection and human answers fed back into the prompt | Static |
| [Code as Policies](https://arxiv.org/abs/2209.07753) (2022) | Code-writing LLM | Python over perception and control-primitive APIs | Perception API outputs | — | Static |
| [VoxPoser](https://arxiv.org/abs/2307.05973) (2023) | LLM + VLM | Code that composes 3D value maps for a motion planner | 3D value maps | Closed-loop trajectory synthesis | Static |
| [OK-Robot](https://arxiv.org/abs/2401.12202) (2024) | Open-knowledge models | Navigation and grasping primitives | Semantic memory | — | Static |
| [Hi Robot](https://arxiv.org/abs/2502.19417) (2025) | High-level VLM | Language commands to a low-level VLA | Images and situated user feedback | User corrections | Static |
| [Gemini Robotics 1.5](https://arxiv.org/abs/2510.03342) (2025) | Gemini Robotics-ER 1.5 | Natural-language steps to a VLA; tools such as web search | Images; tracked progress | Progress tracking by the ER model | Static |
| [FAEA](https://arxiv.org/abs/2601.20334) (2026) | Unmodified coding agent (Claude Agent SDK) | Scripts over perception and control tools | Privileged simulator state | Write–run–debug on execution results | Generates training trajectories |
| [RoboClaw](https://arxiv.org/abs/2603.11558) (2026) | VLM agent loop | Policies triggered as MCP-style tools | — | Monitors progress; retries, replans or escalates to humans | Self-resetting data collection feeds policy learning |
| [Thea](https://arxiv.org/abs/2608.11246) (2026) | Frontier model in an agentic loop | Robot capabilities as tools (navigation, grasping, VLA skills) | Scene Graph as Context | Evaluation as Exit Codes: termination, success, diagnosis | — |
| [Show-Harness](https://arxiv.org/abs/2609.10522) (2026) | Frontier or small VLM | Semantic action units, deterministic per-robot interpreters | Visual observations | — | Few-GPU-hour fine-tuning of small VLMs |
| [Pigey](https://arxiv.org/abs/2607.21725) (2026) | VLM orchestrator | Frozen VLAs and parameterized skills | Observations | Verifies outcomes and recovers | None needed: no new data or post-training |
| [VoLo](https://arxiv.org/abs/2606.07723) (2026) | VLM agent | VLA or world-action model as an interruptible tool | — | Monitors and recovers mid-rollout | — |
| [NavHarness](https://arxiv.org/abs/2609.34276) (2026) | Frontier multimodal model | Navigation tools | Maps, task records and house knowledge, checked against observations | Outcome verification and run-end summaries | Experience carried across sessions |
| [HarnessPAI](https://arxiv.org/abs/2609.29166) (2026) | Coding agent | Code over action primitives | Program state | A fixed program guides and checks each rollout | Programs revised across rollouts; failures distilled into skills |
| [World Action Agent (WAA)](https://arxiv.org/abs/2609.29964) (2026) | Multi-agent VLMs | Basic tools in a visual action workspace | Auto-selected contact views | Action rehearsal before execution; in-view correction | Skills evolved from videos and teaching; traces train smaller VLMs |
| [RoboFoundry](https://arxiv.org/abs/2609.32862) (2026) | Model-agnostic frontier LLM | Hierarchical skill system behind a semantic interface | Context system and file-system memory | Validated system updates | Evolves the whole system as the policy |
| [HexaAnything (Physical Coding)](https://arxiv.org/abs/2609.35432) (2026) | Coding agent | Perception, planning and control tools, including VLA/WAM policies | Code as World | In-the-loop decisions from external feedback | Verified traces become data and memory |

## 6. What 2026 changed

### 6.1 The harness became the object of study

Before 2026, papers presented "a framework" or "a system". Of the 2026 systems in this list (surveys excluded), 29 put "harness" in their title, 15 of them in September alone. These include [Thea](https://arxiv.org/abs/2608.11246), [Show-Harness](https://arxiv.org/abs/2609.10522), [HarnessPAI](https://arxiv.org/abs/2609.29166), [HarnessVLN](https://arxiv.org/abs/2609.15195), [NavHarness](https://arxiv.org/abs/2609.34276), [Zetta](https://arxiv.org/abs/2608.16590), [RegenHarness](https://arxiv.org/abs/2609.27612), [AdaHVLA](https://arxiv.org/abs/2609.29204), [KnowBody](https://arxiv.org/abs/2609.28530), [MaskHarness-WAM](https://arxiv.org/abs/2609.19974), [Harness VLA](https://arxiv.org/abs/2607.08448), [Guava](https://arxiv.org/abs/2606.18363), [RoboHarness](https://arxiv.org/abs/2607.18060), [Harness Robotic OS (HROS)](https://arxiv.org/abs/2609.11225) and [Robo-Harness K1](https://arxiv.org/abs/2609.29389).

Industry framed products the same way: [GRID Auto Engineering](https://www.generalrobotics.company/post/introducing-auto-engineering-for-robotics) calls itself a robotics harness, and [Waddle](https://www.waddlelabs.ai/research/introducing-waddle) has agents write robot code and call VLAs as tools.

### 6.2 Coding agents became credible robot controllers, within limits

- **The evidence for:**
  - [FAEA](https://arxiv.org/abs/2601.20334) ran an unmodified Claude Agent SDK on LIBERO, ManiSkill3 and MetaWorld. It reports success approaching VLAs trained on under 100 demonstrations per task (with privileged simulator state; first-party).
  - The same pattern appears in [CaP-X](https://arxiv.org/abs/2603.22435), [AGP (Agent as Policy)](https://arxiv.org/abs/2609.12541), [RHO](https://arxiv.org/abs/2606.16458) ("your coding agent is secretly a roboticist"), [Teach and Grow (TGL)](https://arxiv.org/abs/2608.17209), [ENPIRE](https://arxiv.org/abs/2606.19980), [Project Fetch: Phase two](https://www.anthropic.com/research/project-fetch-phase-two) and [Claude Plays Robotics](https://www.anthropic.com/research/claude-plays-robotics).
- **The limits are clear:**
  - [Claude Plays Robotics](https://www.anthropic.com/research/claude-plays-robotics) found torque-level control lags higher-level interfaces.
  - [SafeHarness](https://arxiv.org/abs/2609.20822) found coding-agent controllers usually touch obstacles they were told to avoid.
  - In [CodeActionBench](https://arxiv.org/abs/2609.33807), the best model–harness configuration solved 22 of 25 tasks at least once in three attempts. Failures came from spatial alignment, object retention and judging completion.

### 6.3 VLAs became tools

Instead of replacing the planner, VLAs are increasingly wrapped as callable primitives:

- [Harness VLA](https://arxiv.org/abs/2607.08448) turns a frozen VLA into a retryable primitive with a learned operating range.
- [Pigey](https://arxiv.org/abs/2607.21725) names the "orchestration gap" between frozen skills and what a closed-loop orchestrator gets from them.
- [VoLo](https://arxiv.org/abs/2606.07723) treats the VLA as an *interruptible* tool, because the world does not pause while the model reasons.
- [RoboHarness](https://arxiv.org/abs/2607.18060) routes among heterogeneous policies with a memory bridge at handoffs.
- [MaskHarness-WAM](https://arxiv.org/abs/2609.19974) grounds a world-action policy through instance masks.
- [Hi-VLA design study](https://arxiv.org/abs/2606.10267) benchmarks the design choices of such hierarchical agents systematically.

### 6.4 Interface design became a first-class lever

- **Action and observation interfaces:**
  - [Show-Harness](https://arxiv.org/abs/2609.10522) uses semantic action units.
  - [RoboDawn](https://arxiv.org/abs/2609.22966) gives a frozen agentic VLM a compact set of discrete commands.
  - [Guava](https://arxiv.org/abs/2606.18363) searched the harness design space. It found that iterative perception–reasoning–action loops, semantic action abstractions and multimodal observations matter most.
  - [Robo-Harness K1](https://arxiv.org/abs/2609.29389) exposes perception as tools, [AgenticNav](https://arxiv.org/abs/2606.10577) exposes action, depth and memory as tools, and [KnowBody](https://arxiv.org/abs/2609.28530) gives the model an explicit, revisable body model.
- **Protocols.** MCP reached robots through [ROS MCP Server](https://robotmcp.ai/blog/ros-mcp-server-release) and [RoboNeuron](https://arxiv.org/abs/2512.10394). Other work defines context protocols ([Robot Context Protocol (RCP)](https://arxiv.org/abs/2506.11650), [Embodied Context Protocol (ECP)](https://doi.org/10.34133/research.1047)) and hardware standards ([Model Hardware Standard (MHS)](https://www.modelhardwarestandard.com/)). Skills in the Agent Skills format appear in [Isaac ROS 5.0 agent skills](https://blogs.nvidia.com/blog/isaac-ros-5-0-agentic-open-source-robotics/).

### 6.5 Harnesses started to improve themselves

Improvement moved from weights to the harness. Each system below rewrites its own programs, skills, critics or memory from experience:

- [HarnessPAI](https://arxiv.org/abs/2609.29166), [RoboFoundry](https://arxiv.org/abs/2609.32862), [SHAPER](https://arxiv.org/abs/2608.11350)
- [Zetta](https://arxiv.org/abs/2608.16590): validation-gated skill updates.
- [RegenHarness](https://arxiv.org/abs/2609.27612): evidence-gated self-improvement with regression checks and rollback.
- [AdaHVLA](https://arxiv.org/abs/2609.29204), [RACaP](https://arxiv.org/abs/2609.29394), [ASPIRE](https://arxiv.org/abs/2607.00272), [RATs (Playful Agentic Robot Learning)](https://arxiv.org/abs/2606.19419), [GaP (Graph-as-Policy)](https://arxiv.org/abs/2607.05369)
- [ENPIRE](https://arxiv.org/abs/2606.19980): agents run the physical research loop.
- [Recursive Harness Distillation](https://arxiv.org/abs/2609.33378): playbooks passed from strong to light agents.
- [RE-0](https://arxiv.org/abs/2609.32416)
- [SUN / Kuafu](https://arxiv.org/abs/2608.31167): persistent task programs.

### 6.6 …and then distilled themselves back into weights

Harness traces are becoming the data engine:

- [Guava](https://arxiv.org/abs/2606.18363) distills a harness into a 4B model.
- [Robo-Harness K1](https://arxiv.org/abs/2609.29389) and [RACaP](https://arxiv.org/abs/2609.29394) distill tool-call traces or ReAct decisions into small VLMs.
- The traces of [World Action Agent (WAA)](https://arxiv.org/abs/2609.29964) train smaller VLMs.
- The converged programs of [HarnessPAI](https://arxiv.org/abs/2609.29166) collect expert data that improves π0.5.
- [RoboClaw](https://arxiv.org/abs/2603.11558) runs one agent loop across data collection, policy learning and deployment.
- [HexaAnything (Physical Coding)](https://arxiv.org/abs/2609.35432) frames the path as evolving "from tools and Harness to model weights".

## 7. Open problems

1. **Exit codes are the bottleneck.**
   - [FailBench](https://arxiv.org/abs/2609.03611) found the best of 13 VLM judges reaches only 0.77 balanced accuracy, is near chance on contact-rich tasks, and leans toward "success".
   - [ARS](https://arxiv.org/abs/2609.34484) found several reward baselines credit progress for manipulating the wrong object.
   - [CodeActionBench](https://arxiv.org/abs/2609.33807) traces show completion-judgment failures.

   Harnesses need calibrated verifiers ([RoboMonkey](https://arxiv.org/abs/2506.17811), [GVL](https://arxiv.org/abs/2411.04549)) and a verification budget they can spend like any other tool.
2. **Where should state live?**
   - [Ledger](https://arxiv.org/abs/2609.34554) argues that short-term perceptual memory belongs inside the policy, while long-term object memory belongs outside as a readable record.
   - [NavHarness](https://arxiv.org/abs/2609.34276) found that structured recovery handovers beat summaries of the same length.
   - Scene graphs and memories go stale. There is no standard protocol for reconciling them with new observations.
3. **Latency and asynchrony.** The world does not pause for reasoning.
   - Some harnesses move deliberation offline: [RHO](https://arxiv.org/abs/2606.16458) and [HarnessPAI](https://arxiv.org/abs/2609.29166) need no online LLM loop at deployment.
   - Others interrupt policies mid-rollout ([VoLo](https://arxiv.org/abs/2606.07723)).
   - Agent frameworks are only starting to support asynchronous inference. No tool-calling protocol yet models long-running physical actions with side effects, preemption and partial completion.
4. **Safety of tool use.**
   - **Attacks:** jailbreaks ([RoboPAIR](https://arxiv.org/abs/2410.13691), [BadRobot](https://arxiv.org/abs/2407.20242)), and prompt injection through the scene itself ([SHAWSHANK](https://arxiv.org/abs/2511.16347)).
   - **Coding-agent carelessness:** [SafeHarness](https://arxiv.org/abs/2609.20822).
   - **Governance:** [EmbodiedGovBench](https://arxiv.org/abs/2604.11174).
   - **Standards:** [ISO 25785-1](https://www.iso.org/standard/91469.html).

   All point the same way: enforce the envelope below the model. Examples are pre-execution validation in [ROSClaw (OpenClaw-ROS 2)](https://arxiv.org/abs/2603.26997), a server-side safety layer in [DroneServer](https://arxiv.org/abs/2601.15486), and device-level safeguards in [Model Hardware Standard (MHS)](https://www.modelhardwarestandard.com/).
5. **Measure harnesses, not only models.** As with coding agents, the unit of evaluation is "model *M* in harness *H*".
   - [CaP-X](https://arxiv.org/abs/2603.22435) and [CodeActionBench](https://arxiv.org/abs/2609.33807) compare model–harness configurations.
   - [EmbodiedBench](https://arxiv.org/abs/2502.09560) and [Embodied Agent Interface (EAI)](https://arxiv.org/abs/2410.07166) evaluate language-model agents.
   - Most VLA benchmarks ([LIBERO](https://arxiv.org/abs/2306.03310), [SimplerEnv (SIMPLER)](https://arxiv.org/abs/2405.05941)) still measure policies alone.
   - Real-world evaluation is where harness effects will show: [RoboArena](https://arxiv.org/abs/2506.18123), [AutoEval](https://arxiv.org/abs/2503.24278), and [HALTER](https://arxiv.org/abs/2609.19413), which automates resets for long-horizon tasks.
   - Success rates can hide weak instruction following ([RoboFollow](https://arxiv.org/abs/2609.25636)).
6. **Governing self-improvement.** Evidence gates, regression checks and rollback ([RegenHarness](https://arxiv.org/abs/2609.27612)), safety-gated evolution ([Harness Robotic OS (HROS)](https://arxiv.org/abs/2609.11225)) and validation-gated updates ([Zetta](https://arxiv.org/abs/2608.16590)) are early versions of what software calls CI. Robot harnesses need that discipline before they rewrite themselves in homes and factories.
7. **Interface standards.** Many MCP bridges and context protocols exist, but they share no semantics for physical preconditions, units, effects or safety envelopes.

## 8. Reading path

| Theme | Read in this order |
|---|---|
| **Foundations** | [SayCan](https://arxiv.org/abs/2204.01691) → [Inner Monologue](https://arxiv.org/abs/2207.05608) → [Code as Policies](https://arxiv.org/abs/2209.07753) → [ChatGPT for Robotics (PromptCraft)](https://arxiv.org/abs/2306.17582) → [VoxPoser](https://arxiv.org/abs/2307.05973) |
| **Policies a harness calls** | [RT-2](https://arxiv.org/abs/2307.15818) → [OpenVLA](https://arxiv.org/abs/2406.09246) → [π0 (pi0)](https://arxiv.org/abs/2410.24164) → [π0.5 (pi0.5)](https://arxiv.org/abs/2504.16054) → [GR00T N1](https://arxiv.org/abs/2503.14734) → [Gemini Robotics 1.5](https://arxiv.org/abs/2510.03342) |
| **The explicit harness line** | [FAEA](https://arxiv.org/abs/2601.20334) → [CaP-X](https://arxiv.org/abs/2603.22435) → [Thea](https://arxiv.org/abs/2608.11246) → [Show-Harness](https://arxiv.org/abs/2609.10522) → [HarnessPAI](https://arxiv.org/abs/2609.29166) → [RoboFoundry](https://arxiv.org/abs/2609.32862) |
| **Tools and protocols** | [ROS MCP Server](https://robotmcp.ai/blog/ros-mcp-server-release) → [RoboNeuron](https://arxiv.org/abs/2512.10394) → [Model Hardware Standard (MHS)](https://www.modelhardwarestandard.com/) |
| **Verification and safety** | [KnowNo](https://arxiv.org/abs/2307.01928) → [REFLECT](https://arxiv.org/abs/2306.15724) → [AHA](https://arxiv.org/abs/2410.00371) → [FailBench](https://arxiv.org/abs/2609.03611); [RoboPAIR](https://arxiv.org/abs/2410.13691) → [RoboGuard](https://arxiv.org/abs/2503.07885) → [ASIMOV Benchmark](https://arxiv.org/abs/2503.08663) |
| **Evaluation** | [LIBERO](https://arxiv.org/abs/2306.03310) → [SimplerEnv (SIMPLER)](https://arxiv.org/abs/2405.05941) → [EmbodiedBench](https://arxiv.org/abs/2502.09560) → [RoboArena](https://arxiv.org/abs/2506.18123) → [CodeActionBench](https://arxiv.org/abs/2609.33807) |
| **Surveys to go wider** | [Externalization in LLM Agents](https://arxiv.org/abs/2604.08224), [Towards Embodied Agentic AI](https://arxiv.org/abs/2508.05294) |

## 9. Statistics

Counts by category and year of first release, generated from `data/`.

<!-- BEGIN GENERATED: stats -->
| Category | Layer | Total | ≤2021 | 2022 | 2023 | 2024 | 2025 | 2026 | open |
|---|---|---|---|---|---|---|---|---|---|
| [Surveys & Position Papers](categories/survey.md) | meta | 83 | 1 | 1 | 8 | 10 | 30 | 33 | 12 |
| [Embodied Harnesses](categories/harness.md) | L4 | 140 | 0 | 10 | 30 | 23 | 14 | 63 | 67 |
| [Open-Source Frameworks & Runtimes](categories/framework.md) | L0-L4 | 26 | 0 | 1 | 5 | 11 | 5 | 4 | 25 |
| [Action Interfaces, Skills & Tool Protocols](categories/interface.md) | L2 | 43 | 0 | 0 | 5 | 10 | 12 | 16 | 22 |
| [World State, Memory & Spatial Context](categories/memory.md) | L3 | 51 | 0 | 4 | 6 | 15 | 10 | 16 | 31 |
| [Embodied Reasoning Models & Planners](categories/brain.md) | L4 | 47 | 0 | 0 | 5 | 4 | 18 | 20 | 28 |
| [VLA Models & Skill Policies](categories/policy.md) | L1 | 82 | 0 | 1 | 5 | 7 | 42 | 27 | 53 |
| [World Models](categories/world-model.md) | L6 | 64 | 0 | 1 | 3 | 7 | 26 | 27 | 38 |
| [Verification, Failure Detection & Recovery](categories/verification.md) | L5 | 40 | 0 | 0 | 4 | 7 | 14 | 15 | 24 |
| [Safety, Guardrails & Security](categories/safety.md) | L5 | 41 | 0 | 0 | 1 | 9 | 15 | 16 | 21 |
| [Multi-Robot & Fleet Orchestration](categories/multi-agent.md) | L4 | 44 | 0 | 0 | 5 | 8 | 13 | 18 | 22 |
| [Simulators & Environments](categories/sim.md) | L6 | 42 | 12 | 1 | 6 | 5 | 10 | 8 | 38 |
| [Benchmarks & Evaluation](categories/benchmark.md) | L6 | 98 | 5 | 1 | 4 | 19 | 31 | 38 | 71 |
| [Data, Teleoperation & Training Infrastructure](categories/data.md) | L6 | 89 | 5 | 0 | 9 | 18 | 35 | 22 | 63 |
| **Total** |  | **890** | 23 | 20 | 96 | 153 | 275 | 323 | 515 |
<!-- END GENERATED: stats -->

---

_Corrections and additions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md)._
