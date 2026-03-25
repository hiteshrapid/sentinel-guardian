# Component Testing Agent

Sub-agent spawned by Sentinel for writing **frontend component tests** using Vitest + React Testing Library + jsdom.

## Skill Reference

**Read `skills/component-tests/SKILL.md` before writing any tests.** The skill contains all patterns, mocking strategies, rules, and verification gates. This agent file covers execution instructions only.

## When to Spawn

- During frontend repo bootstrap (after scaffolding CI + initial tests)
- When component coverage drops below 100%
- When new components are added without tests
- During coverage gap remediation

## Execution Workflow

1. Read `skills/component-tests/SKILL.md` for patterns and rules
2. Load the appropriate stack context (`contexts/nextjs-typescript.md`, etc.)
3. Enumerate all components in `src/components/` — identify untested ones
4. Write tests following the skill patterns (one file per component, mirror source structure)
5. Run `yarn test:coverage` after every batch — verify 100% on all thresholds
6. Run `test-review` skill before committing (dedup, mock target verification, lint)

## Parallelization Strategy

For large repos (100+ components), Sentinel spawns multiple component-testing agents, each handling a slice:

| Agent | Scope |
|-------|-------|
| Agent A | `src/components/auth/` + `src/components/agents/` |
| Agent B | `src/components/users/` + `src/components/organisations/` |
| Agent C | `src/components/campaigns/` + `src/components/credit-monitoring/` |
| Agent D | `src/components/settings/` + `src/components/mcps/` |
| Agent E | `src/shared/` + `src/components/activities/` + remaining |

Each agent writes tests, verifies coverage for their slice, then reports back. Sentinel merges results and runs full coverage verification.

## Critical Rules

- **Lint before committing** — run eslint and tsc --noEmit before every commit
- **100% coverage mandatory** — statements, branches, functions, lines. No exceptions.
- **One component per test file** — never test multiple components in one file
- **Test behavior, not implementation** — what the user sees and does
- **Use accessible queries** — getByRole > getByLabelText > getByText > getByTestId
