# Next.js + TypeScript Context

Stack context for Next.js frontend repos without Prisma (pure TypeScript + Next.js).

For repos that also use Prisma, see `nextjs-prisma.md`.

## Stack Signals

- `package.json` contains `"next"` but NOT `"prisma"`
- `next.config.ts` or `next.config.mjs` present
- `src/app/` (App Router) or `src/pages/` (Pages Router)
- TypeScript: `tsconfig.json` present

## Package Manager

Default: **yarn** (check for `yarn.lock` vs `package-lock.json` vs `pnpm-lock.yaml`)

## Test Runner

- **Vitest** for unit + component tests
- **Playwright** for E2E
- **@testing-library/react** + **@testing-library/user-event** for component tests
- **jsdom** environment in vitest.config.ts

## Key Patterns

### Component Imports
```tsx
import { ComponentName } from '@/components/path/ComponentName';
```

### Mocking Next.js
```tsx
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/dashboard',
  useSearchParams: () => new URLSearchParams(),
}));
```

### API Layer
- API calls typically go through service files (`src/services/` or `src/lib/api/`)
- Mock at the service/hook level, not fetch

### State Management
- Zustand stores (common in Ruh AI repos)
- React Context for auth/theme
- Mock stores in tests, not internal state

## CI Structure

Uses the **frontend CI template** from the `github-pipeline` skill:
- `lint` + `typecheck` (parallel, Stage 1)
- `unit-tests` + `build` (parallel, Stage 2, needs Stage 1)
- `e2e-local` + `lighthouse` + `bundle-size` (Stage 3, needs build)
- `security-audit` + `sast` (parallel, independent)

## Coverage

100% mandatory for both unit and component tests. Vitest enforces via:
```
--coverage.thresholds.lines=100 --coverage.thresholds.functions=100 --coverage.thresholds.branches=100 --coverage.thresholds.statements=100
```

## Browser Strategy

- PR CI: Chromium only
- Nightly regression: Chromium + WebKit (via `NIGHTLY=true` env var)
- Skip Firefox unless analytics show meaningful traffic
