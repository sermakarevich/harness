# Tutorial 6 — Permission gate

After this tutorial nothing that changes your files or runs a command happens
until you allow it.

## In short

### The concepts

- **You add a human yes-or-no gate before side effects.** Reading is safe. Writing
  and running are not, so everything else waits for your answer, with default ask on unknown
  tools added later (knowledge base: APracticalGuideToBuildingAgents). opencode checks ordered
  rules, pi fires a veto event.
- **This gate wraps the tut05 tools.** The tool node checks before it runs, then
  freezes the turn. Your answer resumes it from its first line, so a resumed node must
  not run the tool twice (knowledge base: ModelOrHarnessFailureTaxonomy, OsmaniHarness).
- **A no is text the model reads, not a crash.** The refused call still gets a
  tool message saying it was denied. The model answers from there, so the
  loop never breaks (knowledge base: HarnessEngineeringCourse).

### Scope

1. You write a policy that says which tools need a question.
2. You write your own tool node that asks first and runs afterwards.
3. You ask in the terminal with yes, always, and no answers.
4. You remember the always answers for the rest of the session.
Left out: per-command rules, a model judging instead of you, and undo.

### The problem

```text
> Create a file notes.txt here with the word hello, then delete it with a shell
command, and tell me what you did in one line.
I'll create notes.txt with your text, then delete it.
→ write_file content=hello path=notes.txt
Created the file; now I'll remove it.
→ shell command=rm notes.txt
Created notes.txt with hello then deleted it with rm notes.txt.
```

Nothing asked you first, and the file was gone before you read the answer.

### What changes

```text
src/harness/
  chat/
+   run_tools.py          asks first, runs the tools after
~   graph.py              uses the asking tool node
~   state.py              keeps the always answers
~   session.py            exposes the waiting question
  tools/
+   permission.py         lists the tools that need no question
~   read_file.py          carries its own tool name
  tui/
+   ask.py                asks yes, always, or no
~   app.py                reads one echoed line
~   render.py             pauses the stream to ask, then resumes
~ tests/                  offline tests for asking, denying, and always
```

## In detail

### How it works

1. Your line enters the graph as a user message.
2. The model asks for `write_file` instead of answering.
3. The router sends the turn to your own tool node.
4. The node sees a tool missing from the safe list and pauses the turn with the call attached.
5. The stream ends, and the terminal finds the waiting question in the saved state and prints it.
6. You type `y`, and the harness resumes the graph with that answer.
7. The node starts again, takes your answer, writes the file, and sends the tool message back.
8. The model reads the tool message and answers with text.

The loop and the tools are the ones from `tut04-tools.md` and `tut05-file-shell.md`.
What is new is who decides: the harness asks you before each side effect.

### Design decisions

- **Every question comes before any tool runs.** A resumed node starts again from
  its first line, so a tool run before the pause would run twice after you answer.
- **A tool nobody listed as safe needs a question.** Forgetting to classify a new
  tool costs one question instead of a deleted file.
- **A denial is a tool message, not an exception.** The model reads what it could
  not do and answers, so you keep the conversation instead of debugging a crash.

### Run it

```bash
git checkout tut06
just tutorial
```

```text
harness · model muse-spark-1.3-contributor · session d22f4335 · /help for
commands
> Create a file hello.txt here containing the word hello. Do not run any other
tool afterwards.
Creating your hello.txt file.
allow write_file content=hello path=hello.txt? [y]es/[a]lways/[n]o y
→ write_file content=hello path=hello.txt
Done — hello.txt contains hello.
> Now delete hello.txt with a shell command.
Deleting hello.txt as requested.
allow shell command=rm hello.txt? [y]es/[a]lways/[n]o n
Couldn't delete hello.txt — the shell command was denied.
> /exit
```

### Under the hood

When the graph pauses, the stream of messages simply ends, with no event and no
error. The harness asks the saved state whether a question is waiting, and the
tool messages of the whole reply arrive only in the stream after your answer.

### Key takeaways

- Only `read_file` runs without asking; writes and commands wait for your answer.
- Yes runs this call, always covers that tool for the session, no sends a denial.
- A denial is a tool message, so the loop never breaks on a refused call.

### What is still missing

The answers, like the conversation itself, live in memory only, so closing the
terminal loses both. Tutorial 7 moves the session to disk.
