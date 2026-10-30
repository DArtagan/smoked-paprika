# mcp-tools: what Claude can ask

## Opening prompt

> Build the MCP tools over stdio and try them from Claude Code against the real
> export. Read `todos/mcp-tools.md` and the design's *MCP surface* and
> *Freshness* sections.

## Why stdio first

The design allows no unauthenticated network transport, and authentication is
google-auth's job. stdio lets the tools be built and used for real, from Claude
Code on this machine, before any of that exists. The HTTP transport arrives with
google-auth, never before it.

## Scope

- The four tools from the design: search, get a recipe, list categories,
  collection status. All are annotated read-only.
- **Output is written for a model to read.** Plain, compact text: a recipe as
  headed sections with numbered steps, search results as one line per recipe.
  Not raw export JSON. Look at what Claude does with each output in practice,
  then adjust. Over-long outputs cost the conversation; terse ones send Claude
  back for a second call.
- **Search.** Case- and accent-insensitive matching over name, ingredients,
  description and notes, ranked with name matches first, and capped. Names
  include non-Latin text: one recipe was exported as
  `三杯鸡 (Three Cup Chicken)`. Test that such names match.
- **Server instructions**, in FastMCP's `instructions`, telling Claude that the
  collection is a snapshot, and to check its age with the status tool and
  mention it when the age matters to the answer.
- **No collection yet.** Before the first upload, every tool says so plainly
  and explains how to make an export, rather than erroring.

## Done when

- Unit tests over generated fixtures for each tool, including the empty
  collection and a non-Latin name.
- Claude Code, connected over stdio with the real export loaded, answers three
  questions correctly, checked against the app:
  1. find a recipe by an ingredient
  2. list the recipes in one category
  3. give a full recipe with its steps intact

  Record the questions and anything that changed the output format as a
  result.
