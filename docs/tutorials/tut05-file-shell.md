# Tutorial 5 — File tools and the shell tool

After this tutorial the model can create and edit files and run commands,
so it can fix a bug and run the tests itself.

## In short

### The concepts

- **After tut04, before tut06.** Tut04 gave the model read tools; this adds write, edit and
  shell with no graph-edge change. The approval gate comes in tut06.
- **Edit is exact find-and-replace.** The model sends exact old and new text; you replace it
  only on exactly one match, else answer with error text. A failed edit is the textbook malformed
  argument (knowledge base: ModelOrHarnessFailureTaxonomy), so the error text must let the model
  recover. Models do best with the edit shapes they were trained on (knowledge base: OsmaniHarness).
- **Shell runs with a timeout in the working directory.** A command that never ends would hang
  your chat, so you kill it after a fixed number of seconds and say so. Every command runs in
  the folder you started in. A sandbox does the same: scoped working directory, timeout, exit code
  with the combined output (knowledge base: HarnessEngineeringCourse).
- **A process becomes text.** The model never sees your process, only text: output, error, exit
  code. The shell is the general-purpose tool (knowledge base: TheAnatomyOfAnAgentHarness).
- **Tricky paths, environment, size.** Every path goes through a shared resolver that rejects
  escapes. The shell inherits the environment so `pytest` resolves. Big outputs are capped in tut09.

### Scope

1. You write a tool that creates a file.
2. You write a tool that replaces one exact piece of text.
3. You write a shell tool with a timeout from settings.
4. You keep the tool line one line long even when an argument is a whole file.

Left out: asking before a side effect (tutorial 6) and capping big outputs (tutorial 9).

### The problem

```text
> Create a file hello.txt here containing the word hello.
I can't create files here — I only have a tool to read files.

You can create it yourself with:

`echo hello > hello.txt`
```

The model wants to act but only has a read tool, so it hands the command back to you.

### What changes

```text
src/harness/
+   tools/paths.py            resolves every path under the working directory
+   tools/write_file.py       creates or overwrites one file
+   tools/edit_file.py        replaces one exact piece of text
+   tools/shell.py            runs one command with a timeout
~   tools/registry.py         lists the four tools for the model
~   config.py                 carries the shell timeout setting
~   chat/prompts/system.txt   names the new tools
~   tui/render.py             shortens long tool arguments to one line
~   tests/                    offline tests for the new tools
```

## In detail

### How it works

1. Your line asks for the smallest fix to the buggy file.
2. The model calls `edit_file` with the exact old line and the new line.
3. The tool node resolves the path, checks the match is unique, writes, and returns `edited ...`.
4. The model calls `shell` with the pytest command.
5. Your harness starts the process in the working directory with the timeout from settings.
6. Standard output, error output, and the exit code come back as one text message.
7. The model reads `1 passed` and answers in one line.

The loop is the one from `tut04-tools.md`: nothing in the graph changed, only the tool list grew.

### Design decisions

- **Exact text, not line numbers or a diff.** The model quotes text it just read but miscounts
  lines, so you ask for text itself; the exactly-once rule turns a vague match into a clear error.
- **The exit code comes back every time.** The model cannot see your process, so a silent
  failure would look like success; all three harnesses in OPERATIONS.md 11 report the exit code.
- **The timeout is a setting, not a literal.** A suite that needs three minutes is normal, so
  you change `.env` instead of code.

### Run it

```bash
git checkout tut05
just tutorial
```

```text
harness · model muse-spark-1.3-contributor · session fba45f6d · /help for
commands
> Write scratch_math.py with a function add(a, b) that on purpose returns a - b,
and test_scratch_math.py with one test that add(2, 3) == 5. Then run pytest -q
test_scratch_math.py and tell me the result in one line.
Writing the off-by-subtraction files and running your failing test.
→ write_file content=def add(a, b): return a - b  path=scratch_math.py
→ write_file content=from scratch_math import add def test_add(): assert add(2, 3… path=test_scratch_math.py
Files are ready — running pytest now.
→ shell command=pytest -q test_scratch_math.py
1 failed — add(2, 3) returned -1 instead of 5.
> Now fix the bug in scratch_math.py with the smallest possible edit, run the same
pytest command again and tell me the result in one line.
Fixing the subtraction to addition and re-running the test.
→ edit_file new_text= return a + b old_text= return a - b path=scratch_math.py
Fix applied — verifying with pytest.
→ shell command=pytest -q test_scratch_math.py
1 passed — add(2, 3) now returns 5.
> /exit
```

### Under the hood

Your command runs through the system shell, so pipes and redirects work, and it inherits your
harness environment: `uv run` puts the virtual environment first, so `pytest` is found.

### Key takeaways

- An edit replaces text found exactly once; anything else returns error text the model can use.
- Every command runs in your working directory with a timeout, and the exit code always comes back.
- The model sees no process, only text, so a failing test is just the next thing it reads.

### What is still missing

The model now changes your files and runs your commands without asking you first.
Tutorial 6 puts a permission gate in front of every tool that has a side effect.
