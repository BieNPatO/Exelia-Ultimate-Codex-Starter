# Project-local skills registry — Exelia Starter 2.0.1

All external skills are installed as copies into `./.agents/skills/` and checked there. **Existing global skills do not count as an installed project dependency.** The installers use the private `./.exelia-tools/node/node_modules/.bin/skills` binary, not a globally installed skills CLI.

| Skill | Upstream | Local installation |
|---|---|---|
| frontend-design | anthropics/skills | `./scripts/local-tool.sh skills add anthropics/skills --skill frontend-design -a codex -y --copy` |
| vercel-react-best-practices | vercel-labs/agent-skills | `... skills add vercel-labs/agent-skills --skill vercel-react-best-practices -a codex -y --copy` |
| vercel-composition-patterns | vercel-labs/agent-skills | Same repo and appropriate `--skill` |
| web-design-guidelines | vercel-labs/agent-skills | Same repo and appropriate `--skill` |
| shadcn | shadcn/ui | `... skills add shadcn/ui --skill shadcn -a codex -y --copy` |
| fastapi | fastapi/fastapi | `... skills add fastapi/fastapi --skill fastapi -a codex -y --copy` |
| systematic-debugging | obra/superpowers | `... skills add obra/superpowers --skill systematic-debugging -a codex -y --copy` |
| verification-before-completion | obra/superpowers | Same repo and appropriate `--skill` |
| differential-review | trailofbits/skills | `... skills add trailofbits/skills --skill differential-review -a codex -y --copy` |
| playwright-cli | Microsoft | `./scripts/local-tool.sh playwright-cli install --skills=agents` |
| impeccable | pbakaus/impeccable | `./scripts/local-tool.sh impeccable install` (select Codex + Project) |
| ponytail | DietrichGebert/ponytail | `... skills add DietrichGebert/ponytail --skill ponytail -a codex -y --copy` |

Project-owned bundled skills: `premium-motion`, `python-backend-engineering`, `project-delivery`.

Ponytail project-only policy applies during coding through the root `AGENTS.md` when the project-local SKILL.md is present; the starter does not install, trust or require global Ponytail plugin hooks or commands. The separate `.codex/hooks.json` SessionStart hook is an Exelia project-state reminder, not Ponytail. Existing global Ponytail plugins may run independently and should not be blindly trusted. Do not globally install the Ponytail plugin from this starter.

The OpenAI Docs and Context7 MCP definitions live in `.codex/config.toml`. No global `ctx7 setup` commands are executed. Context7 may require login to access the remote server. GitHub, Sentry and database MCP are opt-in per project.

Third-party skill source repositories may change. Review downloaded files, licenses and bundled scripts before trusting them; for reproducible builds, pin tested source revisions.
