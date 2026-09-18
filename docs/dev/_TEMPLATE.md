# Tutorial NN — <name, two to four words>

<One sentence: what the chat can do after this tutorial that it could not before.>

## In short

<Part one. About one screen, plain language, no code. A reader who reads only this
part of every tutorial still gets the whole story.>

### The concepts

<The two or three ideas this tutorial rests on, explained in plain language for an
engineer who has not built an agent before. Say what the idea is, why harnesses need
it, and what goes wrong without it. One analogy is allowed. One line each on how
opencode, pi and hermes-agent handle it, from `docs/harnesses/OPERATIONS.md`, and one
line citing a knowledge-base note when one applies.>

### Scope

<What we build in this tutorial and why now. What we deliberately leave out and which
later tutorial picks it up. Three to six sentences.>

### The problem

```text
<A real terminal exchange that fails or answers badly before this tutorial.>
```

### What changes

```text
src/harness/
  chat/
+   tools.py          <one plain phrase>
~   graph.py          <what changed, one phrase>
tests/
+   test_tools.py
```

<`+` is a new file, `~` a changed file. Every file in `git diff tutMM..tutNN` appears here.>

## In detail

### The change, file by file

<For each file in the tree above, in the order the reader should meet them: one or two
sentences on why it exists or why it changed, then the excerpt.>

**New file `src/harness/<layer>/<file>.py`**

```python
<the code, copied from the file at tag tutNN>
```

**Changed `src/harness/<layer>/<file>.py`**

```diff
<the hunk, copied from `git diff tutMM..tutNN -- <file>`, trimmed to the lines that matter>
```

### Run it

```bash
git checkout tutNN
just tutNN
```

```text
<the last lines the reader sees, no timings>
```

### Tests

<What each new test proves, one line per test. `just test` runs them without network.>

### Under the hood

<Optional. One fact that surprises, such as a vendor quirk the code works around.>

### Key takeaways

- <Explained point one, restated as a fact the reader now knows>
- <Explained point two>
- <Explained point three>

### What is still missing

<The limitation the next tutorial fixes, one short paragraph, ending with its number.>

---

## Rules for writing a tutorial (delete this section in the real file)

Audience and depth
- The reader is an engineer who knows Python, git, HTTP and environment files. Never
  explain those. Explain harness and LangGraph ideas, the why behind a design choice,
  and anything a model does that a programmer would not expect.
- Medium-plus depth: say the mechanism, the trade-off, and the failure it prevents.
  Skip anything the reader could guess from the name.
- "The concepts" and "Scope" carry the teaching. "The change" shows the code and
  explains only what the code cannot say.

Prose
- Plain English, short sentences, one idea per sentence. Paragraphs, not one sentence
  per line.
- Spell out a domain abbreviation the first time it appears (LLM, MCP, TUI). Everyday
  engineering ones (HTTP, API, URL, JSON, CLI) need no expansion.
- No marketing words. Say what it does.
- "In short" is under 50 lines. The whole tutorial is under 220 lines. Wrap prose at
  100 characters. The file tree has one entry per line, never several on one line.

Code and commands
- Every excerpt is copied from the file at the tutorial's tag, never retyped, and is
  introduced by a bold line naming the file.
- Changed files are shown as `diff` blocks from the real git diff. New files as code.
- Every command is followed by the output the reader sees, trimmed to the last lines,
  with no timings or dates.
- Name a file in prose instead of linking to it; links to code do not survive the book.

Book rules, so the tutorials compile into one book
- Exactly one top-level heading per file, in the form `Tutorial N — Name`.
- Headings go no deeper than three levels.
- Fenced blocks always carry a language tag: `python`, `diff`, `bash`, `text`.
- Links between tutorials are relative file names such as `tut03-graph.md`.
- No raw HTML, no screenshots, no images.
