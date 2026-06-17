# Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.
- If mid-task the goal turns out wrong (real issue is elsewhere), stop. Restate correct goal and confirm before continuing — don't finish the wrong task just because you started it.
- Prefer type guards over `as SomeType` casts. If a cast is unavoidable after a runtime check, add a comment explaining why.

# Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.
- If a snapshot fails after your change, update only affected snapshots — never bulk-update with `--updateSnapshot` as it silently hides regressions.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

# Use Current Documentation

Don't rely on training data for library/framework/API behavior.

When writing code that uses a library, framework, SDK, or external API:
- Fetch current docs via Context7 before implementing.
- If Context7 unavailable or lacks coverage, fall back to web search.
- Training data is a last resort — API surfaces change.

# Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
