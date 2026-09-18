# Agent-ready GitHub issue specimen

Apply the `agent-ready` label only after this issue contains enough information for an agent to complete the work without a material product, design, or access decision.

## Title

`<Imperative verb> <specific, independently mergeable outcome>` (12 words or fewer)

Example: `Add a pgvector health-check endpoint`

## Goal

State the one user-visible or operational outcome in plain language (one or two sentences; 50 words or fewer).

## Context

Include only the relevant items below (at most five bullets; 40 words or fewer each).

- **Why:** Why this work is needed.
- **Current behavior:** What happens now, including a reproduction when relevant.
- **Desired behavior:** What should happen instead.
- **Relevant code:** Paths, components, services, or configuration keys to inspect.
- **Reference pattern:** An existing module, PR, design, or documentation to follow.

## Scope

Use up to three concise bullets for each applicable category (30 words or fewer each).

- **In scope:** The required changes.
- **Out of scope:** Explicit non-goals.
- **Constraints:** Compatibility, security, performance, migration, dependency, or rollout constraints.

## Acceptance criteria

List three to six observable, independently testable outcomes (35 words or fewer each). Include important failure paths, tests or documentation changes, and exact verification commands where known.

## Implementation notes

Optional. Record only decisions or evidence needed to implement safely (up to five bullets; 40 words or fewer each). Link to logs, designs, screenshots, or documentation instead of copying them.

## Definition of done

- [ ] The scoped implementation is complete.
- [ ] Relevant tests, linting, and type checks have run; results are reported in the PR.
- [ ] Documentation and configuration are updated where needed.
- [ ] The PR summarizes changed files, verification, and remaining risks.

## Labels

- `agent-ready` once all material decisions and access needs are resolved.
- One type label: `type:bug`, `type:feature`, or `type:chore`.
- One priority label: `priority:p0` through `priority:p3`.
- Use `needs-work` instead of `agent-ready` when an unresolved decision prevents implementation.

## Writing conventions

- Keep one issue to one independently mergeable outcome.
- Prefer precise paths and nearby examples over abstract instructions.
- Prefer links, paths, and exact commands over explanatory prose.
- Apply the stated word limits to bullets; use a linked document when supporting detail does not fit.
- Separate discovery/design work from implementation when its outcome could change the scope.
- Use testable language; avoid terms such as “improve,” “better,” or “clean up” unless the intended result is defined.
- If the issue exceeds roughly 700 words, excluding links and the definition of done, split it or move supporting detail to a linked document.
