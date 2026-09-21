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
or wrong, nothing compares the two runs, asking again means typing again.

### What changes

```text
+ src/harness/evals/__init__.py  the evaluation layer and what sits below it
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

## In detail

### How it works

One command runs every task and prints one table. __main__.py loads the settings,
tasks.py reads tasks.toml beside the code, run.py drives each task unwatched, and
report.py folds the results into one row per task.

1. just eval runs python -m harness.evals, which loads the settings and reads the task
   file that sits next to the code. Each task has a name, a prompt, the answer you
   expect back word for word, and the files, if any, the task needs in front of it.
2. Each task is run several times, and each run gets an empty throw-away folder with
   the task's files written into it. That folder is the working directory of the
   session, so every tool the model reaches for lands there.
3. The run starts a session whose conversation is held in memory only, sends the
   prompt, and streams the graph until it stops.
4. Then it asks the session whether a permission question is waiting. If one is, it
   answers "always" and streams again; it repeats that until nothing is waiting.
   Nobody is watching, so the loop is the person.
5. The newest model reply is trimmed of surrounding blank space and compared with the
   expected answer, character for character. That is the whole of the scoring. If the
   call itself dies, that run is recorded as a failure whose answer is the error, and
   the suite carries on.
6. Tokens are counted over the messages this run added and nothing older, turned into
   money with the same price table the terminal uses, and the seconds are measured
   around the loop.
7. The results are grouped by task, one row each, and printed as one table. The
   command exits non-zero when any run failed, so a machine can run it too.

### Design decisions

- **Yes to every question, inside a throw-away folder.** The runner answers every
  permission question with "always" because nobody is there to type; the empty folder
  is what makes that safe, because a wrong command has nothing of yours to touch.
  hermes-agent does the same for its own probes, giving each one a fresh temporary
  home directory.
- **A fresh session for every run.** Each run starts a new session held in memory. The
  second run of a task cannot read the first run's answer out of the conversation, and
  nothing the suite does is written into the session store on disk.
- **Exact match, and more than one run.** Only a task with one right answer can be
  scored this way, which is why the suite asks for a word or a number; and each task
  runs three times by default, because a single run tells you nothing about a model
  that answers differently on Tuesday. hermes-agent repeats seven times by default and
  lets a model grade answers in one place only, where remembering is the thing being
  measured.

### The excerpt that carries the idea

**The loop with the person taken out is run_once in src/harness/evals/run.py:**

```python
    try:
        request: dict | Command = {"messages": [HumanMessage(content=task.prompt)]}
        while True:
            events = session.graph.stream(request, session.config, stream_mode="messages")
            for _message, _meta in events:
                pass
            pending = session.pending_request()
            if pending is None:
                break
            request = Command(resume=AUTOMATIC_ANSWER)
        answer = last_answer(session)
        passed = answer.strip() == task.expect
    except Exception as exc:
        answer = ERROR_ANSWER.format(name=type(exc).__name__, message=exc)
        passed = False
```

This is the loop from the terminal front end with the person taken out: the same
stream, the same waiting question, a fixed answer instead of a keystroke. A call that
dies of a provider error becomes one failed row with the error as its answer, so twelve
runs are not lost to one bad minute.
