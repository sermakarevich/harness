# Tutorial 12 — Skills

After this tutorial the harness can hold far more instruction than fits in a prompt, because
a skill puts one line in front of the model and keeps the rest on disk until it is wanted.

## In short

### The concepts

- **Some instructions are needed sometimes, not always.** Tutorial 11 put notes in the prompt, where
  you pay for every word on every call. That price fits a rule the model must never break, not a
  paper you need once a week. A skill keeps one line up front and loads the rest only when the model
  asks. All four harnesses agree: name and description first, body on demand. In this chapter we
  index each SKILL.md name-plus-description in the prompt and load the body via one tool call.
- **A skill keeps the model on the rails; it rarely teaches a fact.** Across 528 matched
  runs, skills beat a memory from the same attempts by 6.06 points, and judges credited
  procedure in 65.7 percent of cases against 4.5 for knowledge (knowledge base:
  DemystifyingAgentSkills). Misapplied guidance rose from 0.8 percent of runs to 10.0.
  opencode injects a body on a skill call; pi loads it when the model reads the file.
- **More skills is not more capability, and a loaded skill can cost you.** As the pool grew
  from 5 to 100, the right-skill share fell from 29.6 percent to 3.3, success flat.
  Of 20,664 comparisons, 307 confirmed skill-caused damage: 125 wrong answers, 182 passing
  runs at more than twice the cost (knowledge base: AgentSkillsCanBeHarmful). hermes-agent
  bundles skills, and the DeepSeek Harness merges packs into one on-demand catalogue.

### Scope

1. You put the folder the skills live in into settings, one directory per skill inside it.
2. You put each skill's name and one-line description from its `SKILL.md` in the prompt.
3. You give the model one tool that loads a skill's full text by name.
4. You print at the start which skills were found.
Left out: home skills, bundles, extra files, a tool that writes skills, and any check of its pick.

### The problem

```text
> Do not run shell commands. Write the commit message for adding the skills loader. Reply with the message only.
Add skills loader
in 1980 (cached 113) · out 533 (thinking 520) · turn $0.0003 · total $0.0003
```

Every commit here names a scope and a lower-case summary, which `Add skills loader` is not.
With the shell allowed the model read thirteen files and asked to run `ls -la`, and still had
nothing: the format sits in no file it opened. In `AGENTS.md` it would cost you every turn.

### What changes

```text
src/harness/
  chat/
+   prompts/skills.txt  frames the index as instructions to load on demand
~   prompt.py           appends the index after the notes
  tools/
+   skills.py           finds skill folders and reads their descriptions
+   read_skill.py       loads one skill's full text by name
~   registry.py         offers the loader to the model
~   permission.py       lets a skill read pass without asking
  tui/
~   app.py              names the skills found at the start
~ config.py             carries the folder the skills live in
+ skills/commit-message/SKILL.md  the house commit format, loaded on demand
~ tests/                offline checks for the index and the loader
```

## In detail

### How it works

1. You start the harness, and it looks in the skills folder for folders with a `SKILL.md`.
2. Each skill lends one prompt line: its folder name and the `description` fenced at the top.
3. The body stays on disk, and nothing else about it is in the prompt.
4. You ask for something, and when a listed skill matches the model calls it by name.
5. The text comes back as a tool result, and the model answers with it in front of it.
6. A turn that needs no skill never pays for one.

Reading a skill never stops to ask. It is on the safe list, because the prompt advertised it.

### Design decisions

- **Index in the prompt, body behind a tool.** All four harnesses landed there on their own.
- **A skill is an ordinary tool call, so the graph does not change.** The loop from
  tutorial 4 already runs a tool and recalls the model with the result.
- **The directory name is the skill name.** No description means no skill: nothing half-listed.

### Run it

```bash
git checkout tut12
just tutorial
```

`just smoke` asks two questions: first about nothing, then the problem question word for word.

```text
harness · model muse-spark-1.3-contributor · session 208c5670 · /help for commands
memory: AGENTS.md
skills: commit-message
> What is 2 plus 2? Reply with just the number.
4
in 2116 (cached 113) · out 61 (thinking 50) · turn $0.0002 · total $0.0002

> Do not run shell commands. Write the commit message for adding the skills loader. Reply with the message only.
I'll load the commit-message skill to get the house format.
→ read_skill name=commit-message
docs: add the skills loader
in 4969 (cached 4194) · out 753 (thinking 665) · turn $0.0002 · total $0.0004
```

The first turn never reaches for a skill, so you pay only for the index. The second loads the
body, and its `in` counts both calls of that turn. The answer now has the shape the skill asked
for, a scope and a colon and a lower-case summary, though the scope itself is wrong: nothing
said which tutorial this is, and a skill shapes an answer more than it supplies a fact.

### Under the hood

The skills block in the system prompt is 380 characters: 75 for this skill's own line,
the rest three-line framing every skill shares. Its body is 1195 characters, read only
when asked; as a note from tutorial 11 it would cost 1195 characters on every call.

### Key takeaways

- You keep in the prompt only what every turn needs.
- The body arrives when the model asks for it, so an unused skill costs you one line.
- A longer list is not more capable, because the model's aim gets worse as it grows.

### What is still missing

Skills and notes both assume the call comes back. A provider times out, a rate limit
rejects you, a connection dies, and this harness has one try and no plan. It runs one
tool call at a time. Tutorial 13 adds reliability and parallel tool calls.
