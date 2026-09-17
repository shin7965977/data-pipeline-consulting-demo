# Project Agent Guidelines

## Agent skills

### Issue tracker

Issues and specifications are tracked as local markdown files under `.scratch/`. See [`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md).

### Domain docs

This repository uses a single-context domain layout centered on [`CONTEXT.md`](CONTEXT.md) and [`docs/adr/`](docs/adr/). See [`docs/agents/domain.md`](docs/agents/domain.md).

### MBB Management Consultant & FastMCP Intelligence

The repository includes the [MBB Management Consultant Skill](.agents/skills/management-consultant/SKILL.md) (sourced from `DogInfantry/claude-skill-management-consultant-B1`).
When answering questions about business diagnostics, financial metrics, e-commerce KPIs, or using FastMCP tools, activate this skill to enforce:
- **Pyramid Principle & SCQA**: Governing thought / Action Title first.
- **MECE Issue Trees**: Structured causal decomposition (GMV, AOV, cancellation and refund rate leakages).
- **Actionable Commercial Interventions**: Unit economics and 30-60-90 day tactical recommendations.

