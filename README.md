# skills

A personal collection of [Claude](https://claude.com/claude-code) skills I use in my day-to-day work.
Each skill lives in its own directory and packages instructions (and any supporting assets) that teach
the agent how to perform a specific task well.

## Skills

| Skill | What it does |
|-------|--------------|
| [`project-presentation`](./project-presentation) | Turns a software repository into a single, self-contained HTML slide deck — an interactive project overview for stakeholders, using the repo's own content and brand colors. |
| [`create-info-cards`](./create-info-cards) | Turns a YouTube video, article or PDF into 1080×1350 image cards in an Instagram-style collage page. The content sets the card count, the topic sets the design, and each card exports as a PNG. |

## Layout

Each skill is a directory containing a `SKILL.md` with YAML frontmatter (`name`, `description`) and the
agent instructions, plus optional `assets/` and a `README.md`:

```
skills/
├── README.md
└── <skill-name>/
    ├── SKILL.md      # frontmatter + instructions (required)
    ├── README.md     # human-facing overview (optional)
    └── assets/       # templates, scripts, references (optional)
```

The `description` in each `SKILL.md` frontmatter is what Claude uses to decide when a skill applies, so
it's written to describe the triggering situations.

## Usage

Point Claude Code at this directory as a skills source — e.g. symlink a skill into `~/.claude/skills/`:

```bash
ln -s "$PWD/project-presentation" ~/.claude/skills/project-presentation
```

Then invoke it by asking for the task in natural language (or `/project-presentation`). Claude loads
the matching `SKILL.md` and follows its instructions.

## Adding a skill

1. Create a new directory named after the skill.
2. Add a `SKILL.md` with `name` + `description` frontmatter and clear, step-by-step instructions.
3. Drop any templates or scripts the skill needs into `assets/`.
4. Add a row to the table above.

## License

See [LICENSE](./LICENSE).
