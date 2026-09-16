# 06: Automated Quality Gates and CI/CD via GitHub Actions

**What to build:** Enterprise-grade Continuous Integration workflows enforcing strict code and data transformation standards on every pull request. The pipeline runs Ruff for Python linting and formatting, SQLFluff for dbt SQL compliance, and Pytest for simulator domain logic and canonical schema compliance tests.

**Blocked by:** 04: Docker Packaging and Serverless Orchestration

**Status:** closed

- [x] GitHub Actions workflow file `.github/workflows/ci.yml` configured to trigger on pull requests and pushes to `main`.
- [x] Ruff configuration and CI step enforcing Python formatting and lint rules.
- [x] SQLFluff configuration (`.sqlfluff`) and CI step validating dbt SQL models against best practices.
- [x] Pytest suite and CI step verifying simulator state machine logic, discount calculations, and Canonical Schema contracts.
- [x] README badges and workflow status reporting configured.
- [x] Entire test suite passes in a clean GitHub Actions runner environment.
