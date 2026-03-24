# Component Testing Agent

Sub-agent spawned by Sentinel for writing **frontend component tests** using Vitest + React Testing Library + jsdom.

## When to Spawn

- During frontend repo bootstrap (after scaffolding CI + initial tests)
- When component coverage drops below 100%
- When new components are added without tests
- During coverage gap remediation

## Stack

- **Vitest** — test runner
- **@testing-library/react** — render, screen, within, waitFor
- **@testing-library/user-event** — realistic user interaction simulation
- **jsdom** — DOM environment (configured in vitest.config.ts)

## File Placement

```
tests/components/
├── auth/               ← mirrors src/components/auth/
│   ├── LoginForm.test.tsx
│   └── ProtectedRoute.test.tsx
├── agents/
│   ├── AgentCard.test.tsx
│   └── AgentsList.test.tsx
├── shared/
│   ├── DataTable.test.tsx
│   └── Pagination.test.tsx
└── ...                 ← mirror source structure exactly
```

**Naming:** `{ComponentName}.test.tsx` — one test file per component, mirrors `src/components/` structure.

## What to Test (Priority Order)

1. **All props** — render with each prop variation, defaults, edge values
2. **All visual states** — loading, error, empty, success, disabled
3. **User interactions** — clicks, typing, form submission, toggle, select
4. **Conditional rendering** — role-based UI, feature flags, responsive states
5. **Callbacks** — onSubmit, onChange, onDelete fire with correct arguments
6. **Edge cases** — null/undefined data, empty arrays, long strings, special characters

## Patterns

### Props & Conditional Rendering
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ComponentName } from '@/components/path/ComponentName';

describe('ComponentName', () => {
  it('renders with required props', () => {
    render(<ComponentName data={mockData} />);
    expect(screen.getByText('expected text')).toBeInTheDocument();
  });

  it('shows loading skeleton when loading=true', () => {
    render(<ComponentName loading={true} />);
    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
  });

  it('shows empty state when data is empty', () => {
    render(<ComponentName data={[]} />);
    expect(screen.getByText(/no results/i)).toBeInTheDocument();
  });
});
```

### User Interactions
```tsx
import userEvent from '@testing-library/user-event';

it('calls onSubmit with form data', async () => {
  const onSubmit = vi.fn();
  render(<Form onSubmit={onSubmit} />);
  
  await userEvent.type(screen.getByLabelText(/email/i), 'test@ruh.ai');
  await userEvent.click(screen.getByRole('button', { name: /submit/i }));
  
  expect(onSubmit).toHaveBeenCalledWith({ email: 'test@ruh.ai' });
});
```

### Data Tables
```tsx
it('sorts by column on header click', async () => {
  render(<DataTable data={mockData} columns={columns} />);
  await userEvent.click(screen.getByText('Name'));
  const rows = screen.getAllByRole('row');
  expect(within(rows[1]).getByText('Alice')).toBeInTheDocument();
});

it('paginates correctly', async () => {
  render(<DataTable data={largeDataset} pageSize={10} />);
  expect(screen.getAllByRole('row')).toHaveLength(11); // header + 10
  await userEvent.click(screen.getByRole('button', { name: /next/i }));
  expect(screen.getByText('Page 2')).toBeInTheDocument();
});
```

### Modals & Dialogs
```tsx
it('renders nothing when closed', () => {
  render(<Modal open={false} />);
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

it('calls onConfirm when confirmed', async () => {
  const onConfirm = vi.fn();
  render(<Modal open={true} onConfirm={onConfirm} />);
  await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
  expect(onConfirm).toHaveBeenCalledOnce();
});
```

## Mocking

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
vi.mock('@/services/userService', () => ({
  getUserList: vi.fn().mockResolvedValue({ data: mockUsers, total: 10 }),
  deleteUser: vi.fn().mockResolvedValue({ success: true }),
}));
```

## Rules

1. **Test behavior, not implementation** — what the user sees and does
2. **Use `screen` queries** — `screen.getByRole()`, never `container.querySelector()`
3. **Prefer accessible queries** — `getByRole` > `getByLabelText` > `getByText` > `getByTestId`
4. **Use `userEvent` over `fireEvent`** — realistic interaction simulation
5. **Mock at boundaries** — mock services/stores, not internal methods
6. **One component per file** — `LoginForm.test.tsx` tests ONLY `LoginForm`
7. **Cover all states** — loading, error, empty, success, disabled
8. **No `act()` warnings** — missing `await` or `waitFor` if you see them
9. **100% coverage mandatory** — every branch, every function, every line
10. **Import using @/ alias** — `@/components/auth/LoginForm`

## Coverage

Agent MUST run `yarn test:coverage` after writing tests and verify:
- Statements: 100%
- Branches: 100%  
- Functions: 100%
- Lines: 100%

If any file is below 100%, write additional tests to cover the gap. Check the coverage report for uncovered lines.

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
