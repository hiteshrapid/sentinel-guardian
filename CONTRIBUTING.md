# Contributing to Sentinel Guardian

## Adding a New Skill

1. Create a directory under `skills/` with a `SKILL.md` file
2. Follow the existing pattern: frontmatter → Stack Adaptation → Phases → Verification Gates
3. The skill must be stack-agnostic — use the Stack Adaptation table to point to contexts
4. Include at least 3 verification gates

## Adding a New Context

1. Create a `.md` file in `skills/contexts/`
2. Follow the structure of existing contexts: Stack Summary → Key Differences → Install → Auth → DB Setup → Test Patterns
3. Update the Stack Adaptation table in all skills to reference it

## Adding a New Agent

1. Create a `.md` file in `agents/`
2. Include frontmatter: name, description, tools, model
3. Define: workflow, critical rules, verification gate

## Adding a New Command

1. Create a `.md` file in `commands/`
2. Include: description, usage, example output

## Updating LEARNINGS.md

After any deployment or significant fix, append a dated entry:
```markdown
## YYYY-MM-DD — {repo-name} — {action summary}

**What happened:** {1-2 sentences}
**Root cause:** {classification}
**Fix applied:** {what you did}
**Learning:** {what to remember next time}
```

## Code Quality

- No SDR-specific or company-specific content in generic skills
- Stack-specific content belongs in `skills/contexts/`
- All skills must have verification gates
- Test the skill by running Sentinel against a real repo before submitting
