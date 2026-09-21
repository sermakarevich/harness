# Tutorial 11 — Memory files

After this tutorial the harness follows your project's own rules from the first word, because it
reads the instruction files that already sit in your directories.

## In short

### The concepts

- **A fresh session knows nothing about your project.** The weights never change, so each talk
  starts from the same beginner. Rules live in plain files pasted into the prompt before your
  first word. opencode reads one global file plus the first project-level match walking upward.
- **Project and personal notes share one mechanism.** A project note is shared with everyone;
  a home note is yours alone (knowledge base: CodexMemories). Nearer is read last, so it wins.
- **Notes are pasted, not learned, and you pay per call.** The model rereads the text every
  request, so long notes cost tokens each turn. Editable notes are writable instructions
  (knowledge base: ContextualAgenticMemoryIsAMemo). hermes-agent freezes notes at session start.
- **This chapter walks up from your working directory.** It takes the first matching name in
  each folder and appends the notes farthest-first after the filled template.
- **After tut10 this keeps standing rules outside the messages.** Tut10 replaces detail with a
  summary, and a summary can drop a rule. Notes outside the messages survive it.
- **Fill the template before you paste the notes.** You fill the template first.

### Scope

1. You put the file names to look for in settings.
2. You walk up from the working directory and take the first matching name in each directory.
3. You paste what you found into the system prompt, farthest first, so the nearest is read last.
4. You print at the start which notes were loaded.
Left out: a tool the model can write notes with, include directives, any trimming, re-reading a
note in the middle of a session, and turning one note off.

### The problem

The work tree root holds `AGENTS.md`, 4322 characters of coding rules. You rule out tools, so
the model has to answer from what it already knows:

```text
> Without using any tools: what should I name a file for small shared helper functions in this project? Reply with the file name only.
utils.py
in 929 (cached 881) · out 506 (thinking 494) · turn $0.0001 · total $0.0001
```

The rules file says a file is named for what it does and never `utils.py`, so the answer you get
is the one name the project forbids. Asked the same question with tools available, the model ran
a shell command, read `package.json`, `README.md` and `requirements.txt`, spent 4146 input tokens
and still answered `utils.py`, because it never thought to open the rules file.

### What changes

```text
src/harness/
  chat/
+   memory.py           collects one note per directory, farthest first
+   prompts/memory.txt  frames the notes as standing instructions
~   prompt.py           appends the notes after the filled template
  tui/
~   app.py              names the loaded notes at the start
~ config.py             carries the file names, AGENTS.md then CLAUDE.md
~ tests/                offline checks for finding and ordering notes
```

## In detail

### How it works

1. You start the harness.
2. Before anything is sent, it walks from your working directory up to the filesystem root.
3. Each directory gives at most one note: the first listed name found there.
4. It reads them farthest first and nearest last, each under a line naming the file.
5. It fills the template and appends the notes as standing instructions where the later one wins.
6. The terminal names what it loaded, and every call of that session carries it.

The notes are read when the prompt is built, which happens once per session, so `/new` is how
an edited note takes effect.

### Design decisions

- **Notes load once, when the session starts.** The text the model sees cannot change
  mid-session, so the cached prefix of every call stays the same. hermes-agent freezes its
  snapshot for the same reason, while opencode and pi re-read as they go.
- **One directory gives at most one note, the first name that matches.** Two names in one folder
  never arrive twice, so no include machinery is needed. This work tree holds both `AGENTS.md`
  and a one-line `CLAUDE.md`, and only the first is read.
- **The nearest note is read last, because the later line wins.** That is what makes a
  home-directory note a default and a project note its correction. When two notes disagree, you
  know which one the model follows.

### Run it

```bash
git checkout tut11
just tutorial
```

`just smoke` asks the same question you asked in the problem above, with the same words, and
nothing else has changed but where the model's knowledge comes from:

```text
harness · model muse-spark-1.3-contributor · session 4fddc9c1 · /help for commands
memory: AGENTS.md
> Without using any tools: what should I name a file for small shared helper functions in this project? Reply with the file name only.
Do not create one. Name each file for the single job it does and add a sibling file for the next job.
in 1985 (cached 113) · out 1984 (thinking 1950) · turn $0.0006 · total $0.0006
```

The answer now follows the project's rule instead of the habit other projects taught the model.
The `memory:` line names what was loaded, the part you check before you trust an answer.
`in 1985` against the `929` of the problem run is the price of the notes, paid on every call.

### Under the hood

The system prompt is built by filling a template, and a note is not a template. The work tree's
own `AGENTS.md` holds `{cwd}` and `{COMMAND_PREFIX}` in its examples, so you fill the template
first and append the notes after; the other order fails or quietly rewrites someone's note.

### Key takeaways

- Every session starts from zero, so you keep standing instructions in files pasted per prompt.
- You share project notes by checking them in and keep home-directory notes to yourself, and the
  nearer note wins.
- You pay for notes on every call, so you keep them short and let skills carry the rest.

### What is still missing

Everything in a note is paid for on every call of the session, so a note can only hold what is
worth that price. A long reference document does not belong there, and neither does anything you
need only now and then. Nothing trims the notes and nothing lets the model write one. Tutorial
12 adds skills: a short index in the prompt and the full text read only when you need it.
