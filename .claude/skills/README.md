# Project skills

Vendored skills, auto-discovered by Claude Code from `.claude/skills/<name>/SKILL.md`.

| Source | Skills | Commit | License |
|---|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | brainstorming, diagnosing-superpowers, dispatching-parallel-agents, executing-plans, finishing-a-development-branch, receiving-code-review, requesting-code-review, subagent-driven-development, systematic-debugging, test-driven-development, using-git-worktrees, using-superpowers, verification-before-completion, writing-plans, writing-skills | `22f0b463e7a5e579904dd6211a520321035526f7` | MIT (`LICENSE-superpowers`) |
| [anthropics/skills](https://github.com/anthropics/skills) | skill-creator | `e4bb5d960d87126ff3b3a8af1a104b7db67560ba` | Apache-2.0 (`skill-creator/LICENSE.txt`) |

Local modification: superpowers cross-references `superpowers:<skill>` were rewritten to bare
`<skill>` names, since project skills are not namespaced like plugin skills.

To update, re-copy `skills/` from each upstream repo and re-apply the rewrite.
