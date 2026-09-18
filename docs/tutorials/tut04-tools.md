# Tutorial 4 — Tools and the agent loop

After this tutorial the model can read a file you name and use what it found in its answer.

## In short

### The concepts

- **A tool is a schema plus a function.** The schema (name, description, argument shape)
  travels to the model with every call; the function stays in your harness and runs only
  when asked. Schemas cost you context every turn even when unused, so you add tools
  with care (knowledge base: ToolAttentionIsAllYouNeed). opencode declares each schema
  per tool, pi ships seven schemas plus extension registration, and hermes-agent lets
  each tool file register itself.
- **The model asks, the harness runs.** The model never executes anything; it returns a
  message naming a tool and its arguments, and you decide whether and how to run it
  (knowledge base: HarnessEngineeringCourse). Your harness runs only tools it has code
  for (knowledge base: TheAnatomyOfAnAgentHarness). opencode loops over streaming steps,
  pi loops turns with hooks, and hermes-agent runs a bounded model-then-tools loop.
- **The loop is graph structure, and the first tool only reads.** The model node routes
  to the tool node on a tool call and to the end otherwise; the tool node always routes
  back. This reason, act, observe, repeat cycle dominates every harness (knowledge
  base: TheAnatomyOfAnAgentHarness), and real loops carry a step budget, here the
  recursion limit for now (knowledge base: HarnessEngineeringCourse). Reading has no side
  effect so it needs no gate: only action tools that change things need gating
  (knowledge base: APracticalGuideToBuildingAgents). The file system won as the agent
  workspace because models were trained on it (knowledge base: TheAnatomyOfAnAgentHarness).

### Scope

1. You write one tool that reads a file under the working directory.
2. You bind the tool to the model so its schema travels with every call.
3. You add a tool node and the edges that make the loop.
4. You show each tool call in the terminal as one dim line.

Left out: tools that change things (tutorial 5) and asking before a side effect (tutorial 6).

### The problem

```text
> Read the file README.md in this folder and tell me its first heading. Answer
with the heading only.
I can't read files from your local directory.
```

The model can only talk. Everything it knows must arrive in the message list,
and nothing in your harness can put a file there yet.

### What changes

```text
src/harness/
+   tools/read_file.py        one tool that reads a file under the working directory
+   tools/registry.py         the list of tools the model may ask for
~   chat/graph.py             the model node plus the tool node and the loop edges
~   chat/prompts/system.txt   one line naming the read tool
~   tui/render.py             one dim line per tool call
~   tests/                    offline tests for the tool and the loop
```

## In detail

### How it works

1. Your line enters the graph as a message from you.
2. The model node sends the list plus the tool schemas to the model.
3. The reply names `read_file` with a path.
4. The router sees a tool call and goes to the tool node.
5. The tool node resolves the path under the working directory, reads it, and
   appends a tool message tied to the call by its id.
6. The edge leads back to the model node with the grown list.
7. The model answers with text and no tool call.
8. The router goes to the end and the checkpointer saves the five-message list.

This is the whole tool as the model sees it. LangChain builds it from the function's
signature and docstring; the function body never leaves your harness:

```bash
uv run python -c "import json; from pathlib import Path; \
from langchain_core.utils.function_calling import convert_to_openai_tool; \
from harness.tools.read_file import read_file_tool; \
print(json.dumps(convert_to_openai_tool(read_file_tool(Path.cwd())), indent=2))"
```

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a text file under the working directory. Paths are relative to it.",
    "parameters": {
      "properties": {
        "path": {
          "type": "string"
        }
      },
      "required": [
        "path"
      ],
      "type": "object"
    }
  }
}
```

### Design decisions

- **Tool errors are text back to the model, not exceptions.** A wrong path returns
  a not-found message, so it costs you one more turn instead of the chat.
- **Paths stay under the working directory.** The rule lives in code that resolves
  and rejects, not a prompt wish (knowledge base: HowToBuildACustomAgentHarness).
- **The terminal prints every tool call.** You see one dim line per call, so you
  always know what the model did, not only what it said.

### The excerpt that carries the idea

**The loop in `src/harness/chat/graph.py` is these five lines:**

```python
    builder.add_node(MODEL_NODE, call_model)
    builder.add_node(TOOLS_NODE, ToolNode(tools))
    builder.add_edge(START, MODEL_NODE)
    builder.add_conditional_edges(MODEL_NODE, tools_condition, {TOOLS_NODE: TOOLS_NODE, END: END})
    builder.add_edge(TOOLS_NODE, MODEL_NODE)
```

### Run it

```bash
git checkout tut04
just tutorial
```

```text
harness · model muse-spark-1.3-contributor · session 43728859 · /help for
commands
> Read the file README.md and tell me its first heading. Answer with the heading
only.
I'll read README.md to find its first heading.
→ read_file path=README.md
Harness
> /exit
```

### Under the hood

The tool call does not arrive whole. It streams as pieces, name first and arguments
after, and the terminal adds the pieces up before it can print the line.

### Key takeaways

- A tool is a schema the model sees plus a function only you run.
- The model asks with a tool call, and you run it and return the result as a tool message.
- The loop is graph edges: model to tools on a call, tools back to model, end when no call remains.

### What is still missing

The model can read but not change anything. Tutorial 5 adds an edit tool and a
shell tool, and tutorial 6 puts a permission gate in front of them.
