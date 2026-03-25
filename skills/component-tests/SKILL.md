---
name: component-tests
description: >
  Implement frontend React component tests using Vitest + Testing Library + jsdom.
  Use this skill when the user wants to test React components with real DOM rendering,
  user interactions, conditional rendering, form validation states, data tables, modals,
  or any UI behavior in isolation without a full browser. Trigger when the user mentions
  "component tests", "React testing", "Testing Library", "Vitest component", "test my
  components", "component coverage", "render test", or "UI unit tests". This skill
  complements unit tests (pure logic) and E2E tests (full browser). Component tests are
  the fast middle layer for frontend repos. 100% coverage mandatory.
---

# Component Tests Skill

## Stack Adaptation

Before writing any tests, detect the project's frontend stack:

| Signal | Stack | Context |
|--------|-------|---------|
| `package.json` + `next` + `prisma` | Next.js + Prisma | `contexts/nextjs-prisma.md` |
| `package.json` + `next` | Next.js + TypeScript | `contexts/nextjs-typescript.md` |
| `package.json` + `react` (no Next) | React SPA | Analyze and adapt |

Read the context file FIRST. It tells you: package manager, test runner, component library, routing, state management, and stack-specific mocking patterns.

---

You are an expert frontend test engineer. Your mission: implement component tests that verify
every React component renders correctly, handles user interactions, and covers all visual states.

**Component tests answer: "Does this component render and behave correctly for all props, states, and user interactions?"**

---

## Why Component Tests

| Layer | What it tests | Speed | Isolation |
|-------|--------------|-------|-----------|
| Unit | Pure functions, hooks, utilities | ~1ms/test | Full |
| **Component** | **Rendered UI, interactions, conditional states** | **~50-100ms/test** | **Component-level** |
| E2E | Full user journeys in real browser | ~5-30s/test | None |

Component tests run 100-500x faster than E2E. For a repo with 90+ components, that's the difference between 2 seconds and 10 minutes.

---

## Phase 1 — Audit Current State

```bash
# Check testing infrastructure
ls tests/components/ 2>/dev/null && echo "Component test directory exists" || echo "MISSING: tests/components/"
grep -r "testing-library/react" package.json 2>/dev/null && echo "Testing Library installed" || echo "MISSING: @testing-library/react"
grep -r "testing-library/user-event" package.json 2>/dev/null && echo "User Event installed" || echo "MISSING: @testing-library/user-event"
grep -r "jsdom" vitest.config* 2>/dev/null && echo "jsdom configured" || echo "MISSING: jsdom environment"

# Count components vs test files
COMPONENTS=$(find src/components -name "*.tsx" ! -name "*.test.*" 2>/dev/null | wc -l)
TESTS=$(find tests/components -name "*.test.tsx" 2>/dev/null | wc -l)
echo "Components: $COMPONENTS | Tests: $TESTS | Gap: $((COMPONENTS - TESTS))"
```

Determine:
- [ ] Testing Library installed
- [ ] User Event installed
- [ ] jsdom configured in vitest
- [ ] tests/components/ directory exists
- [ ] Current component test coverage

---

## Phase 2 — Install Dependencies (if missing)

```bash
# Core testing deps
yarn add -D @testing-library/react @testing-library/jest-dom @testing-library/user-event
yarn add -D vitest @vitejs/plugin-react jsdom
```

Ensure `vitest.config.ts` includes component tests:

```typescript
export default defineConfig({
  test: {
    include: ['tests/unit/**/*.test.ts', 'tests/components/**/*.test.tsx'],
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
  },
});
```

Ensure `tests/setup.ts` imports Testing Library matchers:

```typescript
import '@testing-library/jest-dom/vitest';
```

---

## Phase 3 — File Placement

```
tests/components/              ← mirrors src/components/ structure
├── auth/
│   ├── LoginForm.test.tsx
│   └── ProtectedRoute.test.tsx
├── agents/
│   ├── AgentCard.test.tsx
│   └── AgentsList.test.tsx
├── shared/
│   ├── DataTable.test.tsx
│   └── Pagination.test.tsx
└── ...
```

**Naming:** `{ComponentName}.test.tsx` — one test file per component, mirrors `src/components/` structure exactly.

---

## Phase 4 — What to Test (Priority Order)

1. **All props** — render with each prop variation, defaults, edge values
2. **All visual states** — loading, error, empty, success, disabled
3. **User interactions** — clicks, typing, form submission, toggle, select
4. **Conditional rendering** — role-based UI, feature flags, responsive states
5. **Callbacks** — onSubmit, onChange, onDelete fire with correct arguments
6. **Edge cases** — null/undefined data, empty arrays, long strings, special characters

### What NOT to Component-Test

- Pure utility functions → unit tests
- Full user journeys across pages → E2E
- API integration → E2E or integration tests
- Visual pixel-perfect layout → Lighthouse or visual regression

---

## Phase 5 — Patterns

### Pattern A — Props & Conditional Rendering

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { UserCard } from '@/components/users/UserCard';

describe('UserCard', () => {
  it('renders user name and role', () => {
    render(<UserCard user={{ name: 'Hitesh', role: 'admin' }} />);
    expect(screen.getByText('Hitesh')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
  });

  it('shows delete button only for superadmin', () => {
    const { rerender } = render(<UserCard user={mockUser} isSuperAdmin={false} />);
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    rerender(<UserCard user={mockUser} isSuperAdmin={true} />);
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  it('renders loading skeleton when loading', () => {
    render(<UserCard loading={true} />);
    expect(screen.getByTestId('user-card-skeleton')).toBeInTheDocument();
  });

  it('renders empty state when user is null', () => {
    render(<UserCard user={null} />);
    expect(screen.getByText(/no user/i)).toBeInTheDocument();
  });
});
```

### Pattern B — User Interactions

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '@/components/auth/LoginForm';

describe('LoginForm', () => {
  it('disables submit when fields are empty', () => {
    render(<LoginForm onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: /sign in/i })).toBeDisabled();
  });

  it('calls onSubmit with credentials when form is valid', async () => {
    const onSubmit = vi.fn();
    render(<LoginForm onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/email/i), 'test@ruh.ai');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(onSubmit).toHaveBeenCalledWith({ email: 'test@ruh.ai', password: 'password123' });
  });

  it('shows error message when error prop is set', () => {
    render(<LoginForm onSubmit={vi.fn()} error="Invalid credentials" />);
    expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
  });

  it('toggles password visibility', async () => {
    render(<LoginForm onSubmit={vi.fn()} />);
    const passwordInput = screen.getByLabelText(/password/i);
    expect(passwordInput).toHaveAttribute('type', 'password');
    await userEvent.click(screen.getByTestId('toggle-password'));
    expect(passwordInput).toHaveAttribute('type', 'text');
  });
});
```

### Pattern C — Data Tables

```tsx
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DataTable } from '@/components/common/DataTable';

describe('DataTable', () => {
  it('renders all rows', () => {
    render(<DataTable data={mockData} columns={columns} />);
    expect(screen.getAllByRole('row')).toHaveLength(4); // header + 3 data
  });

  it('sorts by column when header is clicked', async () => {
    render(<DataTable data={mockData} columns={columns} />);
    await userEvent.click(screen.getByText('Name'));
    const rows = screen.getAllByRole('row');
    expect(within(rows[1]).getByText('Alice')).toBeInTheDocument();
  });

  it('filters data when search input changes', async () => {
    render(<DataTable data={mockData} columns={columns} searchable />);
    await userEvent.type(screen.getByPlaceholderText(/search/i), 'Alice');
    expect(screen.getAllByRole('row')).toHaveLength(2);
  });

  it('shows empty state when no data', () => {
    render(<DataTable data={[]} columns={columns} />);
    expect(screen.getByText(/no results/i)).toBeInTheDocument();
  });
});
```

### Pattern D — Modals & Dialogs

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    render(<ConfirmDialog open={false} onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders dialog when open', () => {
    render(<ConfirmDialog open={true} title="Delete user?" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Delete user?')).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button clicked', async () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog open={true} onConfirm={onConfirm} onCancel={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('calls onCancel when cancel button clicked', async () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open={true} onConfirm={vi.fn()} onCancel={onCancel} />);
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
```

---

## Phase 6 — Mocking Patterns

### Next.js Router
```tsx
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/dashboard',
  useSearchParams: () => new URLSearchParams(),
}));
```

### Zustand Stores
```tsx
vi.mock('@/lib/store/appStore', () => ({
  useAppStore: () => ({ user: mockUser, setUser: vi.fn() }),
}));
```

### Service Calls
```tsx
// Don't mock fetch — mock the hook or service
vi.mock('@/services/userService', () => ({
  getUserList: vi.fn().mockResolvedValue({ data: mockUsers, total: 10 }),
  deleteUser: vi.fn().mockResolvedValue({ success: true }),
}));
```

### Context Providers
```tsx
const renderWithAuth = (ui: React.ReactElement, { user = mockUser } = {}) => {
  return render(
    <AuthContext.Provider value={{ user, isAuthenticated: true }}>
      {ui}
    </AuthContext.Provider>
  );
};
```

---

## Phase 7 — Rules

1. **Test behavior, not implementation** — what the user sees and does, not internal state
2. **Use `screen` queries, not container** — `screen.getByText()` not `container.querySelector()`
3. **Prefer accessible queries** — `getByRole` > `getByLabelText` > `getByText` > `getByTestId`
4. **Use `userEvent` over `fireEvent`** — realistic interaction simulation
5. **Mock at boundaries** — mock services/stores/hooks, not internal component methods
6. **One component per file** — `LoginForm.test.tsx` tests ONLY `LoginForm`
7. **Cover all visual states** — loading, error, empty, success, disabled
8. **No `act()` warnings** — missing `await` or `waitFor` if you see them
9. **100% coverage mandatory** — every branch, every function, every line
10. **Import using @/ alias** — `@/components/auth/LoginForm`

---

## Phase 8 — CI Integration

Component tests run in the same `unit-tests` CI job — no separate job needed:

```yaml
  unit-tests:
    name: Unit + Component Tests
    # yarn test:coverage runs both tests/unit/ and tests/components/
```

Vitest config includes both directories:
```typescript
export default defineConfig({
  test: {
    include: ['tests/unit/**/*.test.ts', 'tests/components/**/*.test.tsx'],
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
  },
});
```

---

## Phase 9 — Parallelization for Large Repos

For large repos (100+ components), spawn multiple component-testing agents, each handling a directory slice:

| Agent | Scope |
|-------|-------|
| Agent A | `src/components/auth/` + `src/components/agents/` |
| Agent B | `src/components/users/` + `src/components/organisations/` |
| Agent C | `src/components/campaigns/` + `src/components/credit-monitoring/` |
| Agent D | `src/components/settings/` + `src/components/mcps/` |
| Agent E | `src/shared/` + `src/components/activities/` + remaining |

Each agent writes tests, verifies coverage for their slice, then reports back. Sentinel merges results and runs full coverage verification.

---

## Phase 10 — Verification Gates

### GATE 1 — Coverage at 100%

```bash
yarn test:coverage 2>&1 | tail -20
# All thresholds must show 100%
```

### GATE 2 — All component states covered

```bash
echo "====== GATE 2: Visual State Coverage ======"
for state in "loading" "error" "empty" "disabled"; do
  count=$(grep -r "$state" tests/components/ --include="*.tsx" 2>/dev/null | wc -l)
  [ "$count" -ge 1 ] \
    && echo "  [PASS] '$state' state tested: $count" \
    || echo "  [WARN] Missing tests for '$state' state"
done
```

### GATE 3 — No act() warnings

```bash
yarn test 2>&1 | grep -i "act(" && echo "FAIL: act() warnings found" || echo "PASS: No act() warnings"
```

### GATE 4 — One file per component

```bash
echo "====== GATE 4: File Organization ======"
MULTI=$(grep -r "^describe(" tests/components/ --include="*.tsx" -l 2>/dev/null | while read f; do
  COUNT=$(grep -c "^describe(" "$f")
  [ "$COUNT" -gt 1 ] && echo "$f has $COUNT top-level describes"
done)
[ -z "$MULTI" ] && echo "PASS: One component per file" || echo "FAIL: $MULTI"
```

---

## Mandatory: Post-Write Review Gate

After writing tests, **before committing**, run the `test-review` skill:
- Duplication scan (no copy-pasted test infrastructure)
- Mock target verification (mocked paths match real source)
- Lint + format check
- Combined suite run (unit + component together)

No test changes ship without passing this gate.
