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

### How it works

<The mechanism, in prose. Walk one turn or one request through the new code: what is
called, what state moves where, what the model sees and what comes back. A short text
diagram of the flow is welcome. Name files in prose; do not quote them here.>

### Design decisions

<Why this shape and not another. Two to five decisions, each with the trade-off and
the alternative we rejected. Where the three harnesses in `docs/harnesses/` chose
differently, say so and why we still chose ours. This is the section that earns
medium-plus depth.>

### The excerpt that carries the idea

<At most one or two short excerpts, only where reading the code says more than prose.
Each introduced by a bold line naming the file, copied from the file at tag tutNN. A
changed file is shown as a `diff` hunk from `git diff tutMM..tutNN`. The rest of the
change is `git diff tutMM..tutNN`, which the reader runs.>

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
- "The concepts" and "Scope" carry the teaching in the first layer; "How it works" and
  "Design decisions" carry it in the second. Code appears only where it says more
  than prose. Never walk the diff file by file; the reader has git for that.

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
- A changed file is shown as a `diff` hunk from the real git diff, a new file as code.
  Two excerpts per tutorial at most.
- Every command is followed by the output the reader sees, trimmed to the last lines,
  with no timings or dates.
- Name a file in prose instead of linking to it; links to code do not survive the book.

Book rules, so the tutorials compile into one book
- Exactly one top-level heading per file, in the form `Tutorial N — Name`.
- Headings go no deeper than three levels.
- Fenced blocks always carry a language tag: `python`, `diff`, `bash`, `text`.
- Links between tutorials are relative file names such as `tut03-graph.md`.
- No raw HTML, no screenshots, no images.
