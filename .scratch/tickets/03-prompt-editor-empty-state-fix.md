# Ticket 03: Fix Prompt Editor Empty-State Fallback Bug

- **blocked_by**: `01-align-cockpit-core-and-schema-designer.md`

## Description
In `fastmcp_diagnostic.py` (`data-pipeline-consulting-demo`) and `components/ai_drawer.py` (`lakehouse-cockpit-core`):
- Currently, clearing the Prompt Editor (`""`) causes `if active_custom and active_custom.strip():` to evaluate to `False`, silently falling back to the verbose MBB system prompt.
- Fix by distinguishing `None` (not customized -> use default MBB prompt) from `""` (explicitly cleared -> use minimal concise Q&A instruction).

## Acceptance Criteria
- Clearing Prompt Editor and clicking Apply produces concise direct answers without forcing MBB/30-60-90 templates.
- Clicking Reset restores `DEFAULT_SYSTEM_PROMPT_ZH` / `DEFAULT_SYSTEM_PROMPT_EN`.
- All existing and new `pytest` tests pass.
