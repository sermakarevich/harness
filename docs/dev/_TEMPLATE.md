# Tutorial NN — <name, two to four words>

<One sentence: what you can do after this tutorial that you could not before.>

## In short

<Part one. About one screen, plain language, no code. If you read only this part of
every tutorial you still get the whole story.>

### The concepts

<The two or three ideas this tutorial rests on, for an engineer who has not built an
agent before. Say what the idea is, why harnesses need it, and what goes wrong without
it. Lists, not long sentences. One analogy is allowed. One line each on how opencode, pi
and hermes-agent handle it, from `docs/harnesses/OPERATIONS.md`, and one line citing a
knowledge-base note when one applies.>

### Scope

<What you do in this tutorial, as a numbered list of steps. Not what the series builds;
that was tutorial 0. Then one line on what is deliberately left out and which tutorial
picks it up.>

### The problem

```text
<A real terminal exchange that fails or answers badly before this tutorial, copied from a
run at the tag before. One or two sentences under it say why it happens.>
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

<`+` is a new file, `~` a changed file, `-` a removed file. Name the files that carry the
idea; the rest is `git diff tutMM..tutNN`.>

## In detail

### How it works

<The mechanism, in prose. Walk one turn or one request through the new code: what the
model sees, what comes back, what the harness enforces. A short text diagram of the flow
is welcome. Name files in prose; do not quote them here.>

### Design decisions

<Two or three, each about harness behaviour, each two sentences: the choice, and what it
protects. Where the three harnesses in `docs/harnesses/` chose differently, say so.>

### The excerpt that carries the idea

<Optional. At most one short excerpt, only where reading the code says more than prose.
Introduced by a bold line naming the file, copied from the file at tag tutNN. A changed
file is shown as a `diff` hunk from `git diff tutMM..tutNN`.>

### Run it

```bash
git checkout tutNN
just tutorial
```

```text
<the last lines you see, copied from a real run at the tag, no timings>
```

### Under the hood

<Optional. One fact that surprises, such as a vendor quirk the code works around.>

### Key takeaways

- <Explained point one, restated as a fact you now know>
- <Explained point two>
- <Explained point three>

### What is still missing

<The limitation the next tutorial fixes, one short paragraph, ending with its number.>

---

## Rules for writing a tutorial (delete this section in the real file)

Audience and depth
- You are an engineer who knows Python, git, HTTP and environment files. The tutorial
  never explains those. It explains harness and LangGraph ideas, the why behind a design
  choice, and anything a model does that a programmer would not expect.
- Medium-plus depth: say the mechanism, the trade-off, and the failure it prevents.
  Skip anything the reader could guess from the name. No Captain Obvious.
- Agentic, not pythonic. Every paragraph is about what the model sees, what it can do,
  or what the harness enforces. A dataclass versus a library, a constant versus a
  literal, how a function is laid out: none of that belongs in a tutorial. If a
  sentence would read the same in a Django tutorial, delete it.
- "The concepts" and "Scope" carry the teaching in the first layer; "How it works" and
  "Design decisions" carry it in the second. Code appears only where it says more than
  prose. Never walk the diff file by file; the reader has git for that.
- Scope says what you do in this tutorial. The series-level story lives in tutorial 0
  and is not repeated.

Prose
- Address the reader as "you". The words "the reader" never appear in a tutorial.
- Structure over prose. A sentence that lists three or more items becomes a bullet
  list; steps become a numbered list. Lists are easier to remember.
- Plain English, short sentences, one idea per sentence. Paragraphs, not one sentence
  per line.
- Spell out a domain abbreviation the first time it appears (LLM, MCP, TUI). Everyday
  engineering ones (HTTP, API, URL, JSON, CLI) need no expansion.
- No marketing words. Say what it does.
- "In short" is under 60 lines. The whole tutorial is under 130 lines. Wrap prose at
  100 characters. The file tree names the files that carry the idea, one entry per line;
  markers, lockfiles and folders of docs collapse into one entry.

Code and commands
- Code runs at the tag, never from `main`. Every command in the document is run at the
  tag before the document is accepted, and its output is copied, not remembered. A
  count such as `4 passed` is checked again whenever the tag moves.
- Every excerpt is copied from the file at the tutorial's tag, never retyped, and is
  introduced by a bold line naming the file.
- A changed file is shown as a `diff` hunk from the real git diff, a new file as code.
  One excerpt per tutorial at most, and none is fine.
- Every command is followed by the output you see, trimmed to the last lines, with no
  timings or dates.
- Name a file in prose instead of linking to it; links to code do not survive the book.
- No local absolute paths and no user names. The repository is public.

Book rules, so the tutorials compile into one book
- Exactly one top-level heading per file, in the form `Tutorial N — Name`.
- Headings go no deeper than three levels.
- Fenced blocks always carry a language tag: `python`, `diff`, `bash`, `text`.
- Links between tutorials are relative file names such as `tut03-graph.md`.
- No raw HTML, no screenshots, no images.
