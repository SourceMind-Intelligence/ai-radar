# The Embodied Harness: a living survey of the systems around robot foundation models

_Living document · revision 2026-09-29 · maintained with the daily radar (see [radar/](radar/))_

**TL;DR**

- For coding agents, the industry learned in 2025–26 that the model is only part of the system. The harness around it (loop, tools, context, permissions, tests as exit codes) decides much of the outcome. Robots are going through the same decomposition.
- We define the **embodied harness** as the software between a foundation model and a body. It decides what the model sees, what it can do, how actions execute, how outcomes are checked, and what it is not allowed to do. We organize it into a seven-layer stack (L0–L6).
- The field has moved through three phases:
  1. LLMs planning over fixed skills (2022–23);
  2. VLAs pulling the loop into the weights (2023–25);
  3. explicit harnesses around frontier models, with VLAs and other skills as tools (2025–26).

  In 2026 the harness became an object of study in its own right.
- The hardest open problems are no longer "which model". They are **exit codes for the physical world**, **world state as context**, **latency and asynchrony**, **safety of tool use**, and **benchmarks that measure harnesses rather than models**.

---

## 1. From agent harness to embodied harness

In software agents, *harness* names the scaffolding around a model: the control loop, the tool definitions, context management, permissions and sandboxing, and the tests that tell the agent whether it is done. Comparisons published in 2026 found that swapping the harness around a *fixed* model changes both the cost per solved task and *which* tasks get solved (see the ai-radar briefing of [2026-08-07](../807-AI/807-article.md)).

Robotics reached the same place from the other direction.

- **The first language-model robots were harnesses in all but name.** SayCan chose among fixed skills by combining language-model likelihood with learned affordance values. Inner Monologue closed the loop by feeding success detectors and scene descriptions back into the prompt. Code as Policies made generated code the action interface.
- **Vision-language-action models (VLAs) then pulled much of that loop into the weights.** RT-2, OpenVLA, π0 and their successors map pixels and instructions straight to actions.
- **Dual-system designs split slow deliberation from fast control.** Examples are Hi Robot, Helix, GR00T N1, and Gemini Robotics 1.5 with its embodied-reasoning orchestrator.
- **In 2026 a research line began naming the harness explicitly.** It builds agent loops that call robot capabilities as tools, keep world state as context, and treat evaluation as exit codes. This list tracks that line and everything it depends on.

## 2. Definition

> An **embodied harness** is the software between a foundation model (LLM, VLM, VLA or world model) and a physical, or physically simulated, body. It decides **what the model sees**, **what it can do**, **how actions are executed**, **how outcomes are checked**, and **what it is not allowed to do**.

In scope are the agent loop and orchestration, the action interface, world state and memory, verification and recovery, the safety envelope, human-in-the-loop, and multi-robot coordination. The offline flywheel that shapes a harness is also in scope: simulators, world models, benchmarks, datasets and training infrastructure. The models a harness calls are listed too, because a harness is designed around what its models can and cannot do.

## 3. The stack

| Layer | Role | Coding-agent analogue | Sections of the list |
|---|---|---|---|
| **L6** Evaluation & data flywheel | Build, test and improve the harness offline | CI, eval suites, traces | [Simulators](README.md#sim), [World models](README.md#world-model), [Benchmarks](README.md#benchmark), [Data](README.md#data) |
| **L5** Verification & safety | Decide whether an action worked, whether it is allowed, and when to ask a human | Tests as exit codes, permission prompts, sandbox | [Verification](README.md#verification), [Safety](README.md#safety) |
| **L4** Reasoning & orchestration | The agent loop: plan, call tools, observe, replan, delegate | Agent loop, planner, sub-agents | [Harnesses](README.md#harness), [Reasoning models](README.md#brain), [Multi-robot](README.md#multi-agent) |
| **L3** World state & memory | What the model knows about the world right now and from before | Context window, repo map, memory files | [Memory](README.md#memory) |
| **L2** Action interface | How capabilities are exposed: skills, code APIs, constraints, protocols | Tool schemas, MCP | [Interfaces](README.md#interface) |
| **L1** Skill policies | Turn a short command into motor actions | The tools' implementations | [VLA models & policies](README.md#policy) |
| **L0** Embodiment & middleware | Hardware, drivers, ROS 2, real-time control | OS, filesystem, shell | [Frameworks & runtimes](README.md#framework) |

The layers are logical, not physical. An end-to-end VLA collapses L1–L4 into one network. A dual-system model spans L1 and L4. A coding-agent-style harness keeps them apart and connects them with explicit interfaces. The most useful question to ask of any system is *which layers it makes explicit, and which it leaves to the weights*.

## 4. Design dimensions

### 4.1 Where does the loop live?

| Design | What the harness does | Examples |
|---|---|---|
| **Model-centric** | Thin wrapper: instruction and observations in, actions out; little or no explicit state | RT-2, OpenVLA, π0 |
| **Hierarchical / dual-system** | A slow reasoning model issues sub-goals or language commands to a fast action model | Hi Robot, Helix, GR00T N1, Gemini Robotics 1.5 + ER |
| **Harness-centric** | A general model runs an explicit loop over tools, with world state and verification kept outside the model | Code as Policies, VoxPoser, Thea, Show-Harness |

### 4.2 What is a "tool call" for a robot?

- **Pick a skill in language.** Choose from a fixed skill set, scored for feasibility (SayCan).
- **Write code** against perception and control APIs (Code as Policies, ProgPrompt).
- **Emit spatial constraints or value maps** that a motion planner optimizes (VoxPoser, ReKep, MOKA).
- **Emit semantic action units** that per-robot interpreters turn into commands deterministically (Show-Harness).
- **Instruct a VLA in language** and let it execute (Hi Robot, Gemini Robotics 1.5).
- **Call a protocol bridge**, such as MCP servers that expose ROS topics, services and actions to any agent.

### 4.3 How is the world represented in context?

- **Raw frames** in the prompt.
- **Text feedback**: scene descriptions and success signals (Inner Monologue).
- **Scene graphs** (SayPlan, Thea).
- **3D semantic maps and feature fields** (VLMaps, ConceptGraphs).
- **Long-term memory**: episodic memory and object ledgers.

The choice decides what the model can reason about, and what goes stale.

### 4.4 Exit codes: how does the harness know it is done?

The ladder of verification runs from nothing to active checks:

1. Open-loop execution.
2. Textual success feedback.
3. Learned success detectors.
4. Failure explanation and recovery (REFLECT, AHA).
5. Evaluators that detect termination, assess success and diagnose failures before the next step.

Physical actions are not idempotent and there is no `git reset`, so verification matters more for robots than for code.

### 4.5 The safety envelope

Safety layers include:

- **affordance gating**: only propose feasible skills;
- **constitutions**: rules checked before execution (AutoRT);
- **runtime guardrails** that check plans against specifications (RoboGuard);
- **uncertainty-aware help-seeking** (KnowNo).

Jailbreak studies on LLM-controlled robots (RoboPAIR, BadRobot) show the envelope has to live *outside* the model, in the harness.

### 4.6 How does the harness improve?

Options range from static prompts and fixed skills, to growing skill libraries, to **self-evolving harnesses** that rewrite their own tools, prompts and memory from experience. Harnesses that improve themselves became one of the clearest themes of 2026.

<!-- SECTIONS 5-8 ARE WRITTEN AFTER THE DATA IMPORT -->

## Statistics

Counts by category and year of first release (generated from `data/`).

<!-- BEGIN GENERATED: stats -->
| Category | Layer | Total |  | open |
|---|---|---|---|---|
| [Surveys & Position Papers](README.md#survey) | meta | 0 | 0 |
| [Embodied Harnesses](README.md#harness) | L4 | 0 | 0 |
| [Open-Source Frameworks & Runtimes](README.md#framework) | L0-L4 | 0 | 0 |
| [Action Interfaces, Skills & Tool Protocols](README.md#interface) | L2 | 0 | 0 |
| [World State, Memory & Spatial Context](README.md#memory) | L3 | 0 | 0 |
| [Embodied Reasoning Models & Planners](README.md#brain) | L4 | 0 | 0 |
| [VLA Models & Skill Policies](README.md#policy) | L1 | 0 | 0 |
| [World Models](README.md#world-model) | L6 | 0 | 0 |
| [Verification, Failure Detection & Recovery](README.md#verification) | L5 | 0 | 0 |
| [Safety, Guardrails & Security](README.md#safety) | L5 | 0 | 0 |
| [Multi-Robot & Fleet Orchestration](README.md#multi-agent) | L4 | 0 | 0 |
| [Simulators & Environments](README.md#sim) | L6 | 0 | 0 |
| [Benchmarks & Evaluation](README.md#benchmark) | L6 | 0 | 0 |
| [Data, Teleoperation & Training Infrastructure](README.md#data) | L6 | 0 | 0 |
| **Total** |  | **0** | 0 |
<!-- END GENERATED: stats -->
