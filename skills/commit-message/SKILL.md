---
description: The house format for a commit message in this repository.
---

# Commit messages

A commit message here is one line. It names the scope, then says in plain English what the
commit does for a reader.

## The subject line

    <scope>: <summary>

- `scope` is the tag of the tutorial the work belongs to, written `tut07`, `tut11`, and so on.
  A change that belongs to no tutorial uses `docs`.
- `summary` starts with a lower-case letter and ends without a full stop.
- Keep the whole line under seventy characters.
- Say what the commit does, not which files it touched: `tut10: keep the recap short and show
  what it buys`, never `update summary.txt and justfile`.

## The body

Most commits have no body. Add one only when the change needs a reason the subject line cannot
hold, and then write two or three plain sentences wrapped at one hundred characters.

## Words to avoid

Never use `feat:`, `fix:`, `chore:` or any other Conventional Commits prefix; the scope is the
tutorial tag. Never use an em dash. Never write "various", "misc", "stuff", "improvements" or
"updates": name the thing that changed.

## Examples

    tut09: tool output offloading
    tut09: name the spilled file once
    docs: the README counts four harnesses, as the tutorials do
