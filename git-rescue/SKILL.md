---
name: git-rescue
description: Diagnose and safely resolve a specific git problem the user is stuck on — "I can't pull because of local changes", "merge conflict I don't understand", "I committed to the wrong branch", "I need to undo my last commit", "detached HEAD", "accidentally committed a secret/large file", "my push was rejected", "I lost my work / need to recover a commit". Use when the user describes a concrete git situation they want fixed, not for general git tutoring. Always inspects the actual repo state first and never discards work without explicit confirmation.
---

# Git Rescue

Get the user unstuck on a **specific** git problem. The user usually describes a symptom ("I can't
pull", "it says merge conflict", "I committed to main by accident") — your job is to read the actual
repository state, identify what's really going on, then apply the smallest safe fix and explain it.

## Prime directive: never lose the user's work

Git rescues go wrong when a command silently throws away commits or uncommitted edits. Before any
command that can discard work (`reset --hard`, `checkout -- .`, `clean`, `git stash drop`, force-push,
`rebase` onto a rewritten history), follow these rules:

- **Inspect before you act.** Run read-only commands first and understand the state. Never run a
  destructive command speculatively.
- **Confirm destructive actions.** State exactly what will be lost (which commits, which files) and
  get the user's explicit go-ahead. Approval for one step is not approval for the next.
- **Prefer reversible moves.** `git stash` over `reset --hard`; a new branch over a force-push;
  `git revert` over `git reset` on shared/pushed history.
- **Create a safety net for risky operations.** Before a rebase or history rewrite, capture the
  current tip: `git branch backup/<short-desc>` so the old state is always recoverable.
- **Untracked changes are work too.** A pull or checkout that "fails because of local changes" may
  involve untracked files — don't `git clean` them away to make the error go away.

## Ask the user at decision points

This skill is interactive. Whenever the fix depends on intent you can't read from the repo — which
changes matter, how a conflict should be resolved, whether history may be rewritten — **stop and ask
with the `AskUserQuestion` tool** rather than guessing. Phrase each option in plain language with its
consequence, and put the safest / recommended option first (label it "(Recommended)").

Gather everything you need for one decision in a single `AskUserQuestion` call (it supports up to 4
questions at once) so the user isn't drip-fed prompts. Ask only what the diagnosis genuinely leaves
open — never ask for state you can gather yourself with a read-only command (Step 1). The decisions
that almost always warrant asking:

- **Which resolution path** to take when more than one is reasonable (e.g. stash vs. rebase vs. discard).
- **How to resolve each non-trivial conflict** — show the user both sides and let them pick ours /
  theirs / a manual blend before you write the resolution.
- **Confirming any destructive action** — name exactly what will be lost and require an explicit yes.
- **Anything that affects teammates** — pushing, force-pushing, rewriting shared history.

When the work is unambiguous and non-destructive (e.g. a clean `git pull --rebase` with no conflicts),
just do it and report — don't manufacture questions.

## Step 1 — Diagnose (always do this first)

Run these read-only commands to build a picture of the state. Don't ask the user for output you can
gather yourself.

```bash
git status                          # working tree + branch vs upstream
git log --oneline -10 --graph --decorate --all   # where the branches/refs sit
git branch -vv                      # local branches and their upstreams
git remote -v                       # remotes
git stash list                      # any stashed work?
```

For specific symptoms, add:
- Pull/push rejected: `git fetch` then `git log --oneline HEAD..@{u}` and `git log --oneline @{u}..HEAD`
  to see what's only-remote vs only-local.
- Conflict in progress: `git status` shows "Unmerged paths"; `git diff --name-only --diff-filter=U`
  lists conflicted files; check `git rev-parse -q --verify MERGE_HEAD || git status` to tell a merge
  from a rebase.
- "Lost" commit: `git reflog -20` — almost nothing is truly gone within the gc window.

Read the output before deciding. State your diagnosis in one or two sentences before acting.

## Step 2 — Resolve

Pick the matching playbook. These cover the common cases; adapt to what the diagnosis actually shows.

### "I can't pull because of local changes" (the headline case)
The colleague's commits are upstream; the user has local edits that conflict (or that git won't
overwrite). First run `git status` / `git diff` so you can summarize *what* the local changes are,
then **ask the user with `AskUserQuestion`** which of these fits — don't assume. Frame the options as
their real consequences:

- "Keep my changes — I'm not done with them" → option 1 (stash, pull, reapply). *Recommended default.*
- "My changes are committed work that should merge with the team's" → option 2 (pull --rebase / merge).
- "Throw my local changes away — the remote version wins" → option 3 (discard; destructive).

Then apply the chosen path:

1. **The local edits should be kept and aren't finished** → stash, pull, reapply:
   ```bash
   git stash push -u -m "wip before pulling teammate's changes"   # -u includes untracked
   git pull --ff-only        # or the team's normal pull strategy
   git stash pop             # reapply; may produce conflicts → resolve as below
   ```
   If `git stash pop` conflicts, resolve the files, `git add` them; the stash stays in the list until
   you confirm it applied cleanly, so the work is recoverable.

2. **The local edits are real, committed work and should merge with the remote** → just integrate:
   ```bash
   git pull --rebase        # replay local commits on top of teammate's (linear history)
   # or: git pull           # if the team prefers merge commits
   ```
   Resolve any conflicts, then `git rebase --continue` (or commit the merge).

3. **The local edits are throwaway and the remote wins** → confirm explicitly, then discard:
   ```bash
   # CONFIRM with the user first — this deletes their local changes:
   git checkout -- <files>   # or: git restore <files>
   git pull
   ```

Default to option 1 or 2 unless the user clearly says the local changes are junk.

### Merge / rebase conflicts
1. `git diff --name-only --diff-filter=U` to list conflicted files.
2. For each conflicted file, show the user both sides of the `<<<<<<< / ======= / >>>>>>>` markers
   ("ours" = current branch, "theirs" = incoming) and **ask with `AskUserQuestion` how to resolve it**:
   keep ours, keep theirs, or a manual blend (describe the blend you'd write). For a file with many
   hunks, ask per hunk if they differ in intent. Only resolve a conflict yourself without asking when
   it's purely mechanical (e.g. both sides added the same import) — and say so when you report.
3. Write the chosen resolution, then `git add <file>` per resolved file.
4. Finish: `git commit` (merge) or `git rebase --continue` (rebase). To bail out entirely:
   `git merge --abort` / `git rebase --abort` returns to the pre-conflict state safely — offer this if
   the user is unsure and wants to start over.

### Committed to the wrong branch
Move the commit(s) to the right branch, remove from the wrong one:
```bash
git branch correct-branch          # or: git switch correct-branch  (if it exists)
git switch correct-branch && git cherry-pick <sha>   # bring the commit over
git switch wrong-branch && git reset --hard HEAD~1   # CONFIRM: drops it from the wrong branch
```
If the wrong branch is `main` and already pushed, prefer `git revert` over reset (see below).

### Undo the last commit
These outcomes are very different, so **ask the user which they want** (keep the edits / replace with a
revert / discard entirely) before running anything — unless they already said.
- Keep the changes staged/working: `git reset --soft HEAD~1` (commit undone, edits kept) — safe.
- Already pushed to a shared branch: **don't rewrite history** — `git revert <sha>` makes a new
  commit that undoes it. Safe for collaborators.
- Throw the commit away entirely: `git reset --hard HEAD~1` — CONFIRM first; this loses the changes.

### Push rejected ("fetch first" / non-fast-forward)
The remote has commits you don't. `git fetch`, then integrate with `git pull --rebase` (or merge),
resolve conflicts, and push again. **Never** suggest `git push --force` to a shared branch; if a force
is genuinely needed (your own feature branch, after a rebase you intended), use
`git push --force-with-lease`, which refuses if someone else pushed in the meantime.

### Detached HEAD
You're on a commit, not a branch. To keep work done here: `git switch -c <new-branch>`. To discard and
go back: `git switch <branch>` (CONFIRM if there are commits only reachable from the detached HEAD —
note their SHAs from `git log` first so reflog can recover them).

### Accidentally committed a secret or huge file
- Not yet pushed, last commit: `git rm --cached <file>`, add to `.gitignore`, `git commit --amend`.
- Deeper in history or already pushed: this is a history rewrite (`git filter-repo` / BFG) plus a
  force-push and **secret rotation**. Tell the user the secret must be treated as compromised and
  rotated regardless — removing it from git does not un-leak it. Walk through it carefully.

### "I lost my work" / need to recover
`git reflog` lists every HEAD position. Find the SHA of the good state and recover with
`git switch -c recovered <sha>` or `git cherry-pick <sha>`. Dropped stashes may still be findable via
`git fsck --no-reflog | grep commit`. Reassure the user — recovery is usually possible within the gc window.

## Step 3 — Verify and explain
- Run `git status` and `git log --oneline -5 --graph` to confirm the repo is in the intended state.
- Tell the user in plain language what you did, what changed, and (briefly) how to avoid the situation
  next time (e.g. "commit or stash before pulling"). Keep it short — they wanted the problem solved.

## Scope and boundaries
- Operate only on the repo in the working directory unless told otherwise.
- Never push, force-push, or delete remote branches without explicit confirmation — these affect
  teammates.
- If the situation is ambiguous or genuinely risky (rewriting shared history, deleting unmerged
  branches), lay out the options and their trade-offs and let the user choose rather than guessing.

