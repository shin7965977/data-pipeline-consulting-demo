# Ticket 01: Align `lakehouse-cockpit-core` and `cockpit_core` Submodule

## Description
Ensure `c:\Users\shin7\Downloads\CV\lakehouse-cockpit-core` has no stray uncommitted reverts against commit `1e670ed` so both repositories share the exact same baseline before refactoring.

## Acceptance Criteria
- `lakehouse-cockpit-core` working tree is clean at `1e670ed`.
- `cockpit_core` submodule in `data-pipeline-consulting-demo` is at `1e670ed`.
