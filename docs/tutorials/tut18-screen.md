# Tutorial 18 — Full-screen shell

After this chapter the harness opens as a full-screen terminal app where the reply
streams into a log, the input box stays alive while the model works, permission is a
pop-up you answer with one key, and the cost of the turn sits in a status bar instead
of scrolling away.

## In short

### The concepts

- **A second front end beside the line-mode chat.** You add a full-screen interactive app
  beside the line-mode chat, and both drive the same conversation code underneath.
- **Front ends stay thin because the core is shared.** hermes-agent runs one shared core
  behind a terminal program, a one-shot scripted entry and messaging gateways, and every
  one of them hands the same string to the same conversation function
  (knowledge base: HermesAgent). The conversation layer never learns which screen is asking.
- **Other harnesses attach screens to a shared session.** opencode's full-screen app
  is one client of a server that owns the sessions and pushes events, so a web page
  and a desktop app attach to the same session. The DeepSeek Harness boots one
  profile per front end (terminal, web, headless, client library), and hermes-agent
  pairs an in-process terminal with a gateway for messaging apps. This chapter builds
  the screen only; the server behind it is tutorial 23.
- **Tutorial 17 ran with nobody watching; every chapter before it used one
  line-mode chat.** That chat prints the reply and then blocks on the next line:
  nothing on screen moves while the model works, and the cost line scrolls away with
  the text. This chapter keeps the screen alive while the model works.
- **A synchronous stream meets an event loop.** The graph stream is synchronous and
  the screen is an event loop, so the turn runs in a thread worker and every screen
  update crosses back through one call.
- **The worker cannot await a dialog.** The worker thread has no event loop, so it
  blocks on a threading event that the dialog sets when the person answers.

### Scope

1. You move the three text-line helpers both front ends print into `chat/lines.py`.
2. You add Textual and build the app: a log, an input box and a status bar.
3. You run the turn in a thread worker that mirrors line mode.
4. You ask permission in a pop-up the worker blocks on.
5. `python -m harness` opens the screen on a terminal and line mode on a pipe.

Left out: tool calls are plain lines with no spinner or todo panel yet (tutorial 19),
slash commands beyond exit wait for the palette (tutorial 20), and multi-line input
waits for the editor (tutorial 21).

### The problem

Line mode prints each turn as one scroll that is gone as soon as the next turn lands:

```text
harness · model muse-spark-1.3-contributor · session d30492bc · /help for
commands
memory: AGENTS.md
skills: commit-message
> List the files in this folder, then tell me how many there are.
→ shell command=ls -1
Here are the items in this folder:

- AGENTS.md
- CLAUDE.md
- docs
- justfile
- pyproject.toml
- README.md
- skills
- src
- tests
- uv.lock

There are 10 in total.
in 5460 (cached 2658) · out 239 (thinking 102) · turn $0.0003 · total $0.0003
```

Everything arrives in one scroll: the arrow line and the cost line are gone as soon as
the next answer prints, there is no place on screen that always shows the bill, and
while the tool runs the terminal shows nothing and accepts nothing.

### What changes

```text
+ src/harness/chat/lines.py        the text lines both front ends print
+ src/harness/screen/__init__.py the full-screen layer and what sits below it
+ src/harness/screen/app.py        the log, the input box and the status bar
+ src/harness/screen/keys.py       the commands the full-screen front end accepts
+ src/harness/screen/permission.py the permission pop-up the worker blocks on
+ src/harness/screen/turn.py       one turn in a thread worker, mirroring line mode
~ src/harness/__main__.py          the screen on a terminal, line mode on a pipe
~ src/harness/tui/app.py           the banner lines move to the shared helper
~ src/harness/tui/render.py        the text lines move to the shared helper
~ pyproject.toml                   the Textual dependency
~ uv.lock                          the Textual dependency
+ tests/test_screen.py             offline checks with a scripted app
```

## In detail

### How it works

`python -m harness` checks `isatty` in `__main__.py`: on a terminal it builds
`ScreenApp`, on a pipe it builds the line-mode `App`. Both start a `Session` the
same way, so the conversation layer never learns which front end is asking.

The screen is three widgets, top to bottom: a `RichLog` holding the conversation,
an `Input` box, and a `Static` status line. On mount the banner lines go into the
log and the cursor lands in the input box.

Pressing Enter submits the text: an empty line is ignored, the exit command closes
the app, and anything else is echoed with `> ` and handed to `run_turn`, a
`@work(thread=True)` method. Textual runs the screen on an event loop while the
graph's `stream` is a plain blocking call, so the turn runs on a second thread and
the loop keeps drawing and reading keys.

Inside the thread, `stream_turn` is a mirror of line mode's `run_turn`: it streams
the graph and collects the text of one reply, writes it to the log when the reply
ends, and prints a tool line when a tool result arrives. Every write crosses back
to the loop through `app.call_from_thread`, the one door between the thread and
the screen.

When the graph stops at a permission request, `permission.ask` pushes a modal
screen from the loop and then waits on a `threading.Event`. The modal's dismiss
callback stores the answer and sets the event, and the thread wakes and resumes
the graph with `Command(resume=...)`.

When no request is waiting, the thread counts the same token, money and total
figures as line mode and puts them in the status line, which stays put at the
bottom while the log scrolls above it.

```text
loop:    draw · keys · modal screen
  |  call_from_thread carries writes, status and the modal push down
  |  threading.Event carries the answer back up: the thread waits,
  |  the modal's dismiss callback sets it
thread:  stream · ask · resume · cost
```

### Design decisions

- **A thread, not async.** The whole conversation layer is synchronous, and LangGraph
  offers `astream`, but switching means every tool, every store call and every test
  goes async for one front end. One thread costs one decorator.
- **An event, not an awaitable.** Textual's `push_screen_wait` needs an event loop in
  the calling task; a thread worker has none. A `threading.Event` blocks the thread
  only, which is exactly what should wait.
- **One line per reply, not per chunk.** A `RichLog` writes whole lines; writing each
  streamed chunk would put every few words on their own line. The turn collects the
  text of one reply and writes it when the reply ends. What streams today is the tool
  lines and the modal; tutorial 19 replaces the log with widgets that update in place.
- **Line mode stays.** Pipes, the eval suite and every earlier document use it, and a
  full-screen app cannot run without a terminal. `python -m harness` picks by `isatty`.

### The excerpt that carries the idea

The whole trick is `ask` in `src/harness/screen/permission.py`:

```python
def ask(app, call: str) -> Answer:
    """Block the turn worker until the person answers. Call only from the worker thread."""
    box: dict = {}
    done = threading.Event()

    def on_done(answer: Answer) -> None:
        box["answer"] = answer
        done.set()

    app.call_from_thread(app.push_screen, PermissionScreen(call), on_done)
    done.wait()
    return box["answer"]
```

It runs on the worker thread: the lines that touch the screen go through
`app.call_from_thread`, and the wait blocks nothing but the thread.
