# Planning Guidelines: Analysis and Plan Phases

**Purpose**: Keep planning documents at the right abstraction level. Answer WHAT/WHY/WHEN, defer HOW/WHICH/WHERE to execution phase.

**Problem**: Planning documents with excessive implementation detail (code snippets, exact SQL, full templates) create noise and rigidity. Implementation details should emerge during execution, not be pre-determined.

---

## Analysis Phase: Focus on WHAT and WHY

### Purpose
Understand the problem space, make design decisions, identify risks. Set direction without prescribing implementation.

### Should Include ✅

**Problem Understanding**:
- Requirements breakdown (what features are in scope)
- User workflows and use cases
- Success criteria (how do we know we're done?)

**Design Decisions**:
- Technology choices (Flask vs FastAPI, SQLite vs Postgres) with rationale
- Architecture patterns (where do concerns separate?)
- Data modeling decisions (denormalization choices, why?)
- Trade-offs considered and chosen direction

**Scope Management**:
- What's included in this iteration
- What's deferred to later iterations
- Why these boundaries were chosen

**Risk Identification**:
- Potential problems (performance, complexity, knowledge gaps)
- Mitigation strategies (high-level)

**Testing Strategy** (high-level):
- What types of tests are needed (unit, integration, manual)
- What needs to be tested (query correctness, endpoint behavior)
- Test data requirements (need fixture with X characteristics)

### Should NOT Include ❌

- Exact code snippets or function implementations
- Full SQL queries with specific syntax
- Complete file contents or detailed templates
- Line-by-line implementation instructions
- Exact function signatures with full type hints
- Detailed directory structures with every file listed
- Specific CSS styles or HTML structure

### Depth Check Questions

Before finalizing analysis, ask:
1. Could a different developer implement this in multiple valid ways? (should be YES)
2. Am I prescribing HOW instead of describing WHAT? (should be NO)
3. Would I need to rewrite this if implementation details change? (should be NO)
4. Is this more than 30-50 lines per major decision? (should be NO)

### Example: Right vs Wrong Level

**❌ Too Detailed**:
```
Query Design Pattern for Top Channels:

```sql
SELECT
    c.channel_name,
    COUNT(*) as total_views,
    COUNT(DISTINCT v.video_id) as unique_videos,
    MIN(v.timestamp) as first_view,
    MAX(v.timestamp) as last_view
FROM views v
JOIN channels c ON v.channel_id = c.channel_id
WHERE c.channel_id != ? -- Exclude sentinel channel
GROUP BY c.channel_id, c.channel_name
ORDER BY total_views DESC
LIMIT ?
```

Design notes:
- Denormalized channel_id in views table enables efficient grouping
- Indexes on (channel_id, timestamp) support both GROUP BY and MIN/MAX
```

**✅ Right Level**:
```
Top Channels Query Requirements:
- Return N channels ranked by total view count
- For each channel: view count, unique videos, date range (first/last view)
- Exclude sentinel channel (deleted videos) by default, with toggle option
- Must perform well on 53k dataset (target <500ms)

Design decision: Leverage denormalized channel_id in views table for grouping efficiency. Existing indexes should support this query pattern.
```

---

## Plan Phase: Focus on Task Breakdown and Ordering

### Purpose
Define what needs to be built and in what order. Provide enough direction for execution without prescribing exact implementation.

### Should Include ✅

**Task Breakdown**:
- List of discrete tasks (create X, implement Y, test Z)
- What each task accomplishes (1-3 sentences)
- Key constraints or requirements per task
- Expected outputs (files created, tests passing)

**Dependencies and Ordering**:
- Which tasks must happen before others
- Why this ordering makes sense
- Phase groupings (test infra → analytics → API → frontend)

**Testing Expectations**:
- What test coverage is expected per component
- Key test cases to cover (normal case, edge cases, error paths)
- How to verify success (test count, manual checks)

**Commit Strategy**:
- Logical commit boundaries
- What goes in each commit (high-level grouping)
- PR description outline

**Success Criteria**:
- Concrete deliverables (all tests pass, server runs, UI functional)
- Performance targets (page loads in <1s)
- Code quality expectations (Black formatting, docstrings, etc.)

### Should NOT Include ❌

- Complete code implementations
- Full function bodies or class definitions
- Exact HTML templates or CSS
- Detailed SQL queries (unless critical to understand approach)
- Line-by-line "what to write"
- Exact file contents from start to finish

### Depth Check Questions

Before finalizing plan, ask:
1. Does this describe WHAT to build or HOW to build it? (should be WHAT)
2. Could implementation vary while still satisfying this plan? (should be YES)
3. Am I writing code in the plan instead of during execution? (should be NO)
4. Is each task description under 5-10 lines? (should be YES for most tasks)

### Example: Right vs Wrong Level

**❌ Too Detailed**:
```
Task 4: Top Channels Query
File: src/analytics/queries.py

```python
def get_top_channels(db_conn: sqlite3.Connection,
                     limit: int,
                     include_deleted: bool = False) -> list[dict]:
    """
    Get top N channels ranked by total view count.

    Args:
        db_conn: SQLite database connection
        limit: Maximum number of channels to return
        include_deleted: If True, include sentinel channel

    Returns:
        List of dicts with keys: channel_name, total_views,
        unique_videos, first_view, last_view
    """
    cursor = db_conn.cursor()
    query = """
        SELECT c.channel_name, COUNT(*) as total_views, ...
    """
    # ... full implementation
```

Implementation notes:
- Format dates as YYYY-MM using strftime
- Handle empty results by returning empty list
- Add DEBUG logging for parameters and result count
```

**✅ Right Level**:
```
Task 4: Top Channels Query
File: src/analytics/queries.py

Implement function that returns top N channels ranked by view count.

Requirements:
- Parameters: database connection, limit (int), include_deleted flag
- Returns: List of channel stats (name, views, unique videos, date range)
- Exclude sentinel channel by default, include when flagged
- Date formatting: YYYY-MM for channel date ranges
- Add DEBUG-level logging for parameters and result counts
- Return empty list if no results (don't error)

Testing: Will be covered in Task 7 (unit tests for query functions)
```

---

## General Guidelines

### When Detailed Examples ARE Appropriate

- **New patterns being introduced**: If this is the first time using a technology/pattern in the project, a small example can help (but keep it minimal, 5-10 lines max)
- **Ambiguous requirements**: If something could be interpreted multiple ways and you need to clarify which interpretation
- **Critical constraints**: If there's a specific technical requirement that must be satisfied (e.g., "must use prepared statements for SQL injection prevention")

### Document Length Guidelines

**Analysis Phase**:
- Typical length: 300-500 lines
- If over 600 lines, probably too detailed
- Should be readable in 5-10 minutes

**Plan Phase**:
- Typical length: 400-600 lines
- If over 800 lines, probably too detailed
- Focus should be on task list and key requirements

### Red Flags (You're Too Detailed If...)

1. You're writing multi-line code blocks for every component
2. You're specifying exact HTML structure element by element
3. You're including full SQL queries with all clauses
4. You're defining complete function signatures with full docstrings
5. You're writing more about HOW than WHAT
6. Implementation phase will just be "copying from plan document"

### Self-Check Before Finalizing

Ask yourself:
- **Can execution make reasonable choices?** If no flexibility remains, too detailed.
- **Could this be implemented differently?** If only one way forward, too detailed.
- **Am I answering questions that belong in code review?** If yes, too detailed.

---

## Templates

### Analysis Phase Template

```markdown
# Analysis: [Feature Name]

## Context Review
- Current state: What exists now?
- Requirements: What are we building?
- Environment: Relevant tech stack, constraints

## Problem Analysis
- Core challenge being solved
- Why this is needed
- Scope boundaries (in/out)

## Design Decisions
### Decision 1: [Name]
- Options considered
- Choice made and rationale
- Trade-offs accepted

### Decision 2: [Name]
...

## Testing Strategy
- What types of tests needed
- Key scenarios to cover
- Test data requirements

## Key Risks
- Risk description
- Likelihood and impact
- Mitigation approach

## Success Criteria
- Deliverable 1
- Deliverable 2
- Performance/quality targets

## Open Questions
- Question → Resolution
```

### Plan Phase Template

```markdown
# Implementation Plan: [Feature Name]

## Overview
- What we're building (2-3 sentences)
- Approach (architecture pattern)
- Key validation goals

## Task Breakdown

### Phase 1: [Component Name]
**Task 1: [Name]**
- What it does (1-3 sentences)
- Key requirements
- Expected output

**Task 2: [Name]**
...

### Phase 2: [Component Name]
...

## Testing Expectations
- Test coverage per component
- Key test cases (bullet list)
- How to verify success

## Commit Strategy
- Commit 1: What's included
- Commit 2: What's included
- PR description outline

## Success Criteria
- Concrete deliverables checklist
- Performance targets
- Quality expectations

## Dependencies
- New dependencies being added
- Version constraints if any

## Verification Plan
- How to test end-to-end
- Manual test checklist
- Performance validation approach
```

---

## Usage Instructions

### For Claude Code Sessions

At the start of analysis/planning sessions, reference this document:

```
"I'm starting the analysis phase. Per docs/planning-guidelines.md,
I should focus on WHAT/WHY and avoid implementation details."
```

Before finalizing documents, self-check:

```
"Let me verify against docs/planning-guidelines.md depth check questions
before presenting this plan."
```

### For Human Review

When reviewing analysis/plan documents, check:
1. Are there full code blocks? → Too detailed
2. Are there complete SQL queries? → Too detailed
3. Is the document over 600 lines? → Probably too detailed
4. Can implementation vary while satisfying this? → Good level

Provide feedback: "This is too detailed per docs/planning-guidelines.md section X"

---

## Evolution

This document should evolve as the project learns what planning depth works best. Update based on:
- Iterations that went smoothly (what level of planning helped?)
- Iterations that struggled (what was missing? what was excess?)
- Patterns that emerge (what decisions keep coming up?)

**Version**: 1.0 (2025-11-11)
**Next Review**: After Iteration 2 completion
