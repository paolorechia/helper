---
name: entire-trail
description: Run a piece of work as an Entire trail — capture the intent, attach a branch to it as a change, let commits capture checkpoints, and post structured findings. Use this whenever the user wants to start, track, or continue work in Entire; references an entire.com trail URL; asks to open, update, or close a trail; wants a branch attached to a trail; or asks to post findings or review a trail's changes. Also use it when the user describes a task and mentions Entire, trails, changes, or checkpoints, even without using those words.
---

# Entire Trail

An Entire **trail** is a project-level work item holding the intent — the
*why* of some work. A **change** is one branch in one repo working on that
intent. A **checkpoint** is the AI session captured automatically at each
commit. A **finding** is structured review feedback attached to a change.

This skill takes a task from intent through to a reported trail.

## Read the flags, don't guess them

The CLI is the source of truth for its own usage and its flags change between
versions. Before running an unfamiliar subcommand, read its flags:

```sh
entire agent-help              # overview, and which command applies when
entire agent-help trail        # trail subcommands and shared flags
entire agent-help trail <sub>  # exact flags for one subcommand
```

Add `--json` for structured output — it parses more reliably than the table
format, and `trail show --json` is how you see a trail's `changes[]`.

## Selector discipline

Users paste URLs; commands take selectors. Map the path after the host:

| URL path | Selector |
| --- | --- |
| `<forge>/<project>/-/trails/<P>` | project trail `<P>` |
| `<forge>/<project>/-/trails/<P>/changes/<repo>/<n>` | change `<repo>/<n>` |
| `<forge>/<project>/<repo>/-/trails/<P>/changes/<n>` | change `<repo>/<n>` |
| `<forge>/<project>/<repo>/trails/<n>` | change `<repo>/<n>` |

Never pass a URL to a command. Project trails and changes are numbered
separately, so passing `<P>` where a change is expected — or the reverse —
targets the wrong thing. When you resolve a pasted URL, say what you resolved
it to before acting on it.

`--project <forge>/<project>` is required for `list`; elsewhere it defaults
to the repo's namespace. The repo itself is auto-detected from the git
remote, so never ask the user which repo they are in — pass `--repo` only to
target a *different* one.

## Workflow

### 1. Find where the work belongs

If the user pasted a trail URL, resolve it to a selector and confirm the
traal's title and status before acting.

Otherwise list what already exists:

```sh
entire trail list --project <forge>/<project>
```

- One obvious open trail matching the task → use it, and say which you chose.
- Several plausible trails → ask which one, rather than guessing.
- Nothing matching → this is new work; create a trail.

### 2. Capture the intent

The trail's title and body are the durable record of *why* this work exists,
so write them for someone who wasn't in the conversation.

- **Title** — the outcome, short: `Fix aggregation dropping transcripts`.
- **Body** — why it matters and what "done" looks like.
- **Type** — `--type feature|bug|task`.

```sh
entire trail update <P> --title "..." --body "..." --type feature
```

A trail's description should stay current: when the goal shifts mid-work,
update it rather than letting it drift from reality.

### 3. Attach a change

A change is a branch. The base branch (`main`) is not itself a meaningful
change — new work needs a branch off it.

New work — creates the branch and attaches it in one step:

```sh
entire trail create --project <forge>/<project> \
  --title "..." --body "..." --type feature \
  --branch-action=create --base main
```

Existing branch — `--branch-action` defaults to `link`, which attaches
work that already exists:

```sh
entire trail link <P> --branch <branch> --base main
```

A branch can only belong to one trail; linking a branch that is already
claimed is rejected. When that happens, find its current trail with
`entire trail show --branch <branch>` rather than guessing.

To get back onto a change later, `entire trail checkout --trail <selector>`
switches the checkout, and `--worktree` puts it under `.entire/worktrees`
instead — useful when the main checkout is already on the base branch.

### 4. Do the work

Work on the branch and commit normally. **Checkpoints capture the AI session
automatically** — don't create checkpoints by hand unless the user asks.

`entire status` shows sync state; a checkpoint reaches origin with the next
`git push origin`. `entire checkpoint list` shows what has been captured.

### 5. Post findings

Findings are how review feedback reaches the work. Post them against the
change, with the file and line that the finding is about:

```sh
entire trail finding add --trail <selector> \
  --file lib/event_aggregation_pipeline.py --line 50 \
  --severity medium -m "What is wrong and why it matters"
```

`--confidence` takes 0.0–1.0, and `--patch` / `--patch-file` attach a
suggested diff (it must modify a single existing file in the worktree).

Findings are for feedback. Comments (`entire trail comment`) are for people —
post review feedback as a finding, not a comment.

### 6. Report

Give the user the full URLs of the trail and the change, what was done, and
what is still outstanding. Include the URL whenever you reference a trail or
change so they can click through.

## Guardrails

- `entire trail` commands need network access and the OS keychain. If you hit
  "Keychain is not accessible" or a network error, that is the sandbox, not a
  logged-out state: ask to re-run it unsandboxed. Do not run `entire login`.
- `enable`, `disable`, `clean`, `auth`, `login`, and `logout` are the user's
  to run — suggest them, don't run them.
- Writing intent onto a shared trail is outward-facing. Confirm the title and
  body with the user before writing, and confirm before creating a trail.
- If it's unclear whether work belongs on an existing trail or a new one, ask
  rather than picking for them.

## Quick reference

| Task | Command |
| --- | --- |
| List trails | `entire trail list --project <forge>/<project>` |
| Inspect a trail | `entire trail show <P> --project <forge>/<project> --json` |
| Set intent | `entire trail update <P> --title "..." --body "..."` |
| New trail + branch | `entire trail create ... --branch-action=create --base main` |
| Attach existing branch | `entire trail link <P> --branch <branch> --base main` |
| Get onto a change | `entire trail checkout --trail <selector> [--worktree]` |
| Post a finding | `entire trail finding add --trail <selector> --file <f> -m "..."` |
| Checkpoints | `entire checkpoint list` / `entire status` |
