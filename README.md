# skills

A personal collection of agent skills I use in my day-to-day work. Each skill lives in its own
directory and packages instructions (and any supporting assets) that teach a coding agent how to do a
specific task well.

Site, with the Graphite UI board: https://taanviir.github.io/skills/

## Skills

| Skill | What it does |
|-------|--------------|
| [`project-presentation`](./skills/project-presentation) | Turns a software repository into a single, self-contained HTML slide deck — an interactive project overview for stakeholders, using the repo's own content and brand colors. |
| [`graphite-ui`](./skills/graphite-ui) | A design system shipped as a skill. Reworks an existing app's UI onto Graphite UI tokens and component recipes, with an audit script that proves nothing hardcoded is left. |
| [`create-info-cards`](./skills/create-info-cards) | Turns a YouTube video, article or PDF into 1080×1350 image cards in an Instagram-style collage page. The content sets the card count, the topic sets the design, and each card exports as a PNG. |

## Usage

Symlink a skill into your agent's skills directory, for example `~/.claude/skills/` for Claude Code
or `~/.agents/skills/` for Codex:

```bash
ln -s "$PWD/skills/project-presentation" ~/.claude/skills/project-presentation
ln -s "$PWD/skills/project-presentation" ~/.agents/skills/project-presentation
```

Then ask for the task in plain language. The agent loads the matching `SKILL.md` and follows its
instructions.

## Testing

Script tests and end-to-end evals are described in [`evals/README.md`](./evals/README.md).

## License

See [LICENSE](./LICENSE).
