# YouTube Watch History Analysis

## Project Overview

A local-only data analysis application for YouTube watch history, inspired by "Spotify Wrapped". Takes 8 years of watch history (58k+ records in JSON format) and provides analytical insights through a web interface.

**Project Scope**: Similar to a university databases term project - data pipeline, proper storage, backend analysis, frontend visualization. Features will be added iteratively.

**Key Constraint**: Self-hosted only, no internet access required, no authentication needed. Must be easily deployable by others on their own datasets.

## Project Versioning

**V1 Scope**: Core analytics with full data re-ingest, simple UI, no API integration
**V2 Scope**: Channel grouping, YouTube API enrichment, incremental updates, parallel instances

See `docs/requirements/` for detailed requirements by persona (end user, operator, developer).

## Getting Started

**For setup and usage instructions, see `README.md`**.

Quick reference:
```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install -e .

# Run tests
pytest tests/ -v
```

## Technical Stack

- **Platform**: Linux (Arch), local deployment only
- **Database**: SQLite3 (10k-100k records expected, multiple tables for efficient lookups)
- **Backend**: Python 3 (Flask or FastAPI with Jinja templates)
- **Frontend**: Server-rendered HTML + D3.js for interactive visualizations (loaded via CDN, no build step)
- **Testing**: pytest framework with defensive assertion style
- **Version Control**: Git with trunk-based development, short-lived feature branches

## Deployment Model

**Runtime location**: `~/projectDeployments/<instance_name>/` (outside repo)
**Default instance**: "default"
**Per-instance isolation**: Separate DB, logs, config, venv

Repository contains only source, tests, docs, and operator scripts.

## Development Philosophy

### Testing Requirements

**Mandatory Testing**: "If it's not tested, it's not functional"
- Use pytest framework (learning opportunity for me)
- Everything must be tested within reason
- Not strict TDD, but testing and testability are front-of-mind
- Prefer mocking via inheritance for clear interface definitions

**Testing Strategy**:
- Unit tests for data transformation logic
- Integration tests for data pipeline (JSON → SQLite)
- Use fixtures with synthetic/sanitized data (NO real YouTube data in repo)
- Test doubles/mocks following inheritance pattern
- Backend API endpoints must be tested
- Frontend: manual verification acceptable initially

**Testing Infrastructure**:
- Use in-memory SQLite (`:memory:`) for unit tests (fast, isolated)
- Dependency injection for testability: core logic takes parameters, I/O at edges
- Pure functions with clear interfaces preferred over monolithic implementations
- Integration tests use fixtures with file-based SQLite databases

### Error Handling

**Development Mode**: Assert-heavy approach
- Use Python `breakpoint()` statement for debugging
- Emit clear error messages explaining what went wrong
- Fail fast with `sys.exit(1)` style errors (similar to core dumps)
- No recovery attempts - expose problems immediately

**Verbose Mode**:
- `--verbose` or `-v` flag to dump everything (stdout or local file)
- Extensive diagnostic output when debugging

**Production Mode** (when others use this):
- Verbose error messages but no PDB sessions
- Consider `--debug` flag to enable breakpoint() behavior

### Code Standards

**Dependency Management**:
- Minimal dependencies preferred (portability and reusability)
- Python virtual environments welcome
- Avoid Node.js dependency hell - use CDN for D3.js
- Must be simple to set up on a different person's system

**KISS Principle**: Keep it simple, don't overcomplicate
- Only add complexity when needed
- Defer optimization until necessary
- Clear, straightforward solutions over clever code

**Documentation**:
- Brief inline comments for non-obvious logic
- Short explanations after implementation (see Interaction Protocol)
- Code should be self-documenting where possible

**Code Formatting**:
- Black for automatic formatting (default configuration)
- Developers run Black manually before commits in V1

**Python Error Handling Patterns**:
- Use `Optional[T]` for expected non-matches (e.g., filtering posts from video records)
- Raise exceptions for actual data errors (malformed data, missing required fields)
- Pattern: "None for not applicable, exception for data corruption"
- Aligns with systems philosophy: exceptions for exceptional circumstances

### Git Workflow

**Trunk-Based Development**:
- Main branch must always build and pass all tests
- Short-lived feature branches (1-5 small commits)
- GitHub PR process for each feature
- Branch → Implement → Review → Merge → Next feature

**CRITICAL: Make small, focused commits**:
- Each commit should be reviewable in 5-10 minutes
- Small commits enable easier review and better feedback
- Break large features into multiple small commits
- Each commit should build and pass tests
- Commit frequently during implementation

**PR Reviews as Education**:
- PRs serve dual purpose: quality control + knowledge transfer
- Reviews will be thorough, expect detailed feedback
- Code review demonstrates proper software engineering process for spectators
- Small commits make reviews more effective

**Manual Edits Expected**:
- I may manually edit code between commits
- After manual changes, I'll explain what I changed and why
- Claude should `git diff` to see my changes and learn preferences

## Claude Code Interaction Protocol

### When to Interject

**Always flag proactively**:
- Potential mistakes or bugs
- Better alternatives exist (explain trade-offs)
- Security concerns (though low-stakes environment)
- Performance implications
- Design smells or anti-patterns

### Implementation Process

**For each feature, follow this cycle**:

1. **Analyze**: Understand requirements, identify potential issues
2. **Plan**: Propose approach, flag alternatives, wait for approval if ambiguous
3. **Execute**: Implement with brief inline comments
4. **Explain**: Short summary after implementation (2-4 sentences covering "why" not "what")

**Use AskUserQuestion tool** when:
- Multiple valid approaches exist
- Unclear requirements
- Trade-offs need user preference
- Assumptions could affect design

### Planning Depth Guidelines

**CRITICAL: Do NOT implement code during analysis or planning phases**

Analysis and planning are for understanding and direction, NOT implementation.

**Document Length**: Keep analysis and planning documents concise (aim for <100 lines each)
- Too much text leads the tool astray
- Focus on essential decisions and high-level approach
- Details belong in execution phase

See `docs/planning-guidelines.md` for complete guidelines. Quick summary:

**Analysis Phase** - Focus on WHAT and WHY:
- Requirements, design decisions, trade-offs
- Architecture boundaries, testing strategy
- **NEVER**: Code snippets, exact SQL, full function signatures, implementation details

**Plan Phase** - Focus on task breakdown and ordering:
- What needs to be built (high-level), dependencies, testing expectations
- Task descriptions: 1-3 sentences per task
- **NEVER**: Full implementations, complete templates, line-by-line instructions, code examples

**Execution Phase** - Where implementation details belong:
- Actual code, exact APIs, specific queries
- Planning provides direction, execution fills in details

**Self-check**: If implementation phase is just "copying from plan", the plan is too detailed.

### Explanation Depth

**Default Style**: Brief inline documentation + short explanation after implementation
- Focus on "why" rather than "what"
- Explain trade-offs made

**Defer Details**: Deeper explanations can be requested during PR review

### PR-Style Presentation

After implementing a feature:
1. Summarize what changed
2. Explain key decisions
3. Note any deviations from plan
4. Highlight areas that need review attention
5. List tests added

## Data Constraints

**Privacy Protection**:
- NO real YouTube watch history data in repository
- Use synthetic/anonymized data for examples and tests
- Sanitized test fixtures only

**Test Data**:
- Use curated real records safe for public display (committed to repo)
- Keep some non-sensitive examples in repo for testing
- Real data stays local, never committed


## Project-Specific Notes

**Expected Data Scale**:
- 58,000 records in source JSON
- Multiple tables for efficient lookups
- Simple caching acceptable (JSON file + periodic eviction)

**Iterative Feature Development**:
- Start with basic pipeline (JSON → SQLite)
- Add simple queries and summaries
- Build web interface incrementally
- Add sophisticated analysis features over time

**No Authentication Required**: Local-only deployment, single-user assumption

**Spectator Mode**: Assume an inexperienced observer may be watching the development process. Demonstrate proper software engineering practices throughout.

---

## Quick Reference

**Testing**: pytest, assert-heavy, test doubles via inheritance
**Errors**: breakpoint() in dev, verbose messages, fail fast
**Dependencies**: Minimal, Python venv, D3.js via CDN
**Git**: Trunk-based, small commits (5-10 min review), main always passes tests
**Explanation**: Brief, focus on "why" over "what"
**Interject**: Always flag issues/alternatives proactively
**Planning**: NO CODE in analysis/plan, keep docs <100 lines, focus WHAT/WHY/WHEN not HOW
