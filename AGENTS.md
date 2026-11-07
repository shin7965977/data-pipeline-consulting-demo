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

### Lakehouse Conversational Onboarding Skill

The repository includes the [Lakehouse Onboarding Skill](.agents/skills/lakehouse-onboarding/SKILL.md) for conversational platform setup.
When the user says "開始安裝", "/install", "setup", or asks to configure the lakehouse platform:
- **Dynamic Codebase Introspection**: Run `python onboarding_wizard.py --introspect` before posing questions to detect available sources, gold marts, storage engines, and environment status.
- **Zero Hardcoding & Data-Driven Charts**: Dynamically assemble menus and recommendations based on current repository capabilities. Never hardcode chart lists; dynamically profile user measures/dimensions/time and default to **Google Looker Studio embedded inside Streamlit**.
- **7-Stage Onboarding Flow**: Guide through Ingestion -> Storage & FinOps 100MB Guardrail -> AI Intelligence -> ELT Pipeline Run -> Data-Driven C-T-D-S-A Chart Ideation (Looker on Streamlit) -> Streamlit Cockpit Launch.


