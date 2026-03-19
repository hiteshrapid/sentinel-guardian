# Next.js + Prisma/TypeScript Context

> Stack-specific patterns for testing Next.js applications using Prisma ORM.
> Load this context when the target repo has `package.json` with `next` + `prisma`.

## Stack Summary

- **Framework:** Next.js (App Router or Pages Router)
- **ORM:** Prisma
- **Database:** PostgreSQL
- **Package Manager:** npm / pnpm / yarn
- **Test Runner:** Jest (unit) + Playwright (E2E)
- **Auth Pattern:** NextAuth.js / JWT / Session cookies
- **Language:** TypeScript

## Install Dependencies

```bash
npm install --save-dev \
  jest @jest/globals ts-jest @types/jest \
  @testing-library/react @testing-library/jest-dom \
  supertest @types/supertest \
  testcontainers @testcontainers/postgresql \
  playwright @playwright/test \
  jest-mock-extended
```

## Jest Configuration

```typescript
// jest.config.ts
import type { Config } from "jest";

const config: Config = {
  projects: [
    {
      displayName: "unit",
      testMatch: ["<rootDir>/tests/unit/**/*.test.ts"],
      transform: { "^.+\\.tsx?$": "ts-jest" },
      testEnvironment: "node",
    },
    {
      displayName: "integration",
      testMatch: ["<rootDir>/tests/integration/**/*.test.ts"],
      transform: { "^.+\\.tsx?$": "ts-jest" },
      testEnvironment: "node",
      globalSetup: "<rootDir>/tests/integration/globalSetup.ts",
      globalTeardown: "<rootDir>/tests/integration/globalTeardown.ts",
    },
  ],
  coverageThreshold: {
    global: { branches: 100, functions: 100, lines: 100, statements: 100 },
  },
};

export default config;
```

## DB Setup — Integration Tests (Testcontainers)

```typescript
// tests/integration/globalSetup.ts
import { PostgreSqlContainer } from "@testcontainers/postgresql";

export default async function globalSetup() {
  const container = await new PostgreSqlContainer("postgres:16-alpine").start();
  process.env.DATABASE_URL = container.getConnectionUri();

  const { execSync } = require("child_process");
  execSync("npx prisma migrate deploy", {
    env: { ...process.env, DATABASE_URL: container.getConnectionUri() },
  });

  (globalThis as any).__POSTGRES_CONTAINER__ = container;
}

// tests/integration/globalTeardown.ts
export default async function globalTeardown() {
  const container = (globalThis as any).__POSTGRES_CONTAINER__;
  if (container) await container.stop();
}
```

## Prisma Mock Setup

```typescript
// tests/mocks/prisma.ts
import { PrismaClient } from "@prisma/client";
import { mockDeep, DeepMockProxy } from "jest-mock-extended";

export const prismaMock = mockDeep<PrismaClient>() as DeepMockProxy<PrismaClient>;
```

## Unit Test Patterns

```typescript
// tests/unit/userService.test.ts
import { UserService } from "@/services/userService";
import { prismaMock } from "../mocks/prisma";

describe("UserService", () => {
  const service = new UserService(prismaMock);

  it("creates a user and returns without password", async () => {
    prismaMock.user.create.mockResolvedValue({
      id: "1", email: "alice@test.com", name: "Alice", createdAt: new Date(),
    });
    const result = await service.createUser({ email: "alice@test.com", password: "Secure123!" });
    expect(result.email).toBe("alice@test.com");
    expect(result).not.toHaveProperty("password");
  });

  it("throws on duplicate email", async () => {
    prismaMock.user.create.mockRejectedValue({ code: "P2002" });
    await expect(
      service.createUser({ email: "dup@test.com", password: "x" })
    ).rejects.toThrow("already exists");
  });
});
```

## Integration Test Patterns

```typescript
// tests/integration/users.test.ts
import request from "supertest";
import { app } from "@/app";

describe("POST /api/users", () => {
  it("201 creates user", async () => {
    const res = await request(app)
      .post("/api/users")
      .send({ email: "test@test.com", password: "Secure123!" })
      .set("Authorization", "Bearer " + testToken);
    expect(res.status).toBe(201);
    expect(res.body.email).toBe("test@test.com");
  });

  it("401 without auth", async () => {
    const res = await request(app).post("/api/users").send({});
    expect(res.status).toBe(401);
  });
});
```

## Security: audit-ci for Dependency Security

```bash
npx audit-ci --config audit-ci.jsonc
```

## CI Pipeline Pattern

```
lint-typecheck → unit + integration + security (parallel) → contract
Post-deploy: smoke → e2e
Nightly: all layers + Slack alert
```
