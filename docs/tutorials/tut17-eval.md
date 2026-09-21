# Tutorial 17 — Evaluation

After this tutorial you can run the harness against a fixed set of tasks with nobody
watching and get one table of pass, tokens, money and time.

## In short
### The concepts
- **You write tasks, repeat them, print one table.** A few small tasks with expected
  answers, each run several times unwatched, one table of pass, cost and time.
- **One run proves nothing.** A fixed suite before and after a change spread 4.4 percentage points
  across repeats of one task, as much as the effect (knowledge base: SignalOrNoiseAgentSkills).
- **The table has money and time columns.** The same 22 tasks through two harnesses moved
  cost by -41 percent, wall time by -44 percent and tokens by -38 percent, while quality
  stayed a wash at that size (knowledge base: TheHarnessEffect).
- **Only hermes-agent brings a task suite of its own.** Of the four harnesses in
  `docs/harnesses/OPERATIONS.md`, it runs 131 files of deterministic checks, repeated seven
  times by default. opencode tests its own functions, and the DeepSeek Harness measures time
  and memory against fixed budgets, and neither of those two scores an agent's answers.
- **Tutorial 16 added the last ability; each check so far was typing in and reading back.**
  This chapter is the first time the harness runs itself and scores the result.
- **Two traps the runner guards against.** Nobody answers the permission question, so the runner
  says yes to everything, safe only because each task runs in a throw-away folder. A shared
  session would leak the first answer into the next task, so each run starts fresh.

### Scope
1. You write the tasks and their expected answers in a settings-style file.
2. You read them with a loader that turns each entry into one task.
3. A runner starts a fresh session in a throw-away folder and says yes to every question.
4. You measure tokens, money and seconds around each run and repeat each task.
5. You print one table of pass, tokens, money and time per task.
Left out: no model grades answers, so only exact-answer tasks score; free-text judging waits.

### The problem

Asking the same question twice, before this chapter's code, shows what one turn gives you:

```text
51
in 2659 (cached 113) · out 118 (thinking 107) · turn $0.0003 · total $0.0003
51
in 2659 (cached 113) · out 50 (thinking 39) · turn $0.0003 · total $0.0003
```

The terminal shows the answer and the bill for one turn, then it is gone. Nothing records right
or wrong, nothing compares the two runs, asking again means typing again; the bills already differ.

### What changes
```text
+ src/harness/evals/__main__.py  runs the suite and prints one table
+ src/harness/evals/report.py    turns the results into one table
+ src/harness/evals/run.py       runs each task alone and measures it
+ src/harness/evals/tasks.py     reads the tasks and their expected answers
+ src/harness/evals/tasks.toml   the tasks and their expected answers
~ src/harness/config.py          how many times each task repeats
~ src/harness/settings.toml      how many times each task repeats
~ justfile                       the recipe that runs the suite
~ .env.example                   the repeat count beside the other settings
+ tests/test_evals.py            offline checks with a scripted model
```
