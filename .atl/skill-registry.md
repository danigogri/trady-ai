# Skill Registry — Trady AI

> Generated: 2026-07-06
> Scope: user-level (`~/.config/opencode/skills/`)
> Project skills: none detected

## Contract

This registry is an **index**, not a summary. Each row points to the canonical `SKILL.md` source of truth. Subagents MUST read the full skill file at the listed path before executing.

## Indexed Skills

| # | Skill | Trigger / Description | Scope | Path |
|---|-------|----------------------|-------|------|
| 1 | branch-pr | Create Gentle AI pull requests with issue-first checks. Trigger: creating, opening, or preparing PRs for review. | user | `~/.config/opencode/skills/branch-pr/SKILL.md` |
| 2 | chained-pr | PRs over 400 lines, stacked PRs, review slices. Split oversized changes into chained PRs that protect review focus. | user | `~/.config/opencode/skills/chained-pr/SKILL.md` |
| 3 | cognitive-doc-design | Design docs that reduce cognitive load. Trigger: writing guides, READMEs, RFCs, onboarding, architecture, or review-facing docs. | user | `~/.config/opencode/skills/cognitive-doc-design/SKILL.md` |
| 4 | comment-writer | Write warm, direct collaboration comments. Trigger: PR feedback, issue replies, reviews, Slack messages, or GitHub comments. | user | `~/.config/opencode/skills/comment-writer/SKILL.md` |
| 5 | go-testing | Trigger: Go tests, go test coverage, Bubbletea teatest, golden files. Apply focused Go testing patterns. | user | `~/.config/opencode/skills/go-testing/SKILL.md` |
| 6 | issue-creation | Create Gentle AI issues with issue-first checks. Trigger: creating GitHub issues, bug reports, or feature requests. | user | `~/.config/opencode/skills/issue-creation/SKILL.md` |
| 7 | judgment-day | Trigger: judgment day, dual review, adversarial review, juzgar. Run blind dual review, fix confirmed issues, then re-judge. | user | `~/.config/opencode/skills/judgment-day/SKILL.md` |
| 8 | skill-creator | Trigger: new skills, agent instructions, documenting AI usage patterns. Create LLM-first skills with valid frontmatter. | user | `~/.config/opencode/skills/skill-creator/SKILL.md` |
| 9 | skill-improver | Trigger: improve skills, audit skills, refactor skills, skill quality. Audit and upgrade existing LLM-first skills. | user | `~/.config/opencode/skills/skill-improver/SKILL.md` |
| 10 | work-unit-commits | Plan commits as reviewable work units. Trigger: implementation, commit splitting, chained PRs, or keeping tests and docs with code. | user | `~/.config/opencode/skills/work-unit-commits/SKILL.md` |

## Skipped (by convention)

| Skill | Reason |
|-------|--------|
| `sdd-*` (init, explore, propose, spec, design, tasks, apply, verify, archive, onboard) | SDD lifecycle skills — resolved via SDD protocol, not registry |
| `_shared` | Shared SDD references — not invokable |
| `skill-registry` | Self-reference — would create circular index |

## Notes

- No project-level skills detected in `/mnt/d/dev/Trady.AI/`
- Registry will be regenerated when skills are installed, removed, or moved
- `go-testing` is indexed but not relevant to this Python project — kept for cross-project portability
