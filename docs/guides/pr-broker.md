# Team PR broker (IMD-212)

Status: proposed in IMD-212. It takes effect when the IMD-212 row is in `docs/spec/DECISION_REGISTER.md`; merge the broker's pull request together with that row. Until then, CLAUDE.md §12 and [contributing.md](contributing.md) describe the current flow.

## Purpose

Every pull request is opened by its **designated member** from that member's own GitHub session, so GitHub records the member as the pull request's author (`author.login`). Setting commit authors, assignees or the body text alone does not change this.

The broker does all the preparation and checking. The member's only step is to open one prefilled link while signed in to GitHub and press **Create pull request**.

No member shares a password, token or device login, and no credential is stored on the operator's machine. Nothing needs to be authorized up front or revoked later.

## Design

| | |
| --- | --- |
| Tool | `.claude/tools/pr-broker.mjs` (Node 22, standard library only; child processes take argument arrays, never a shell string) |
| Member map | `.claude/tools/members.json`: member, GitHub login, git name and email (the identities already public in the commit history) |
| GitHub access | Read-only `gh pr list` and `gh pr view` through the operator's own gh login. The broker never creates, edits, merges, closes or approves a pull request, never deletes a branch, never pushes and never reads or stores a credential. |
| Guard | `.claude/hooks/guard.mjs`, registered as a PreToolUse hook in `.claude/settings.json` |

### Designated member

1. Every commit in `origin/main..origin/<branch>` must have an author email and a committer email in the member map, belonging to the same member, with author = committer (CLAUDE.md §12). Otherwise the broker refuses with `UNMAPPED_OR_MISMATCHED_COMMIT` and lists the commits.
2. If every commit belongs to one member, that member is the designated member. A different `--owner` is refused.
3. If several members have commits (a batch), `--owner` is required and must be one of them. This is the PR owner named in the batch prompt.
4. The broker never picks an account by default or at random.

## Commands

Run them from the repository root.

```bash
node .claude/tools/pr-broker.mjs prepare --branch <name> [--base main] --title <t> --body-file <f> \
    [--owner <login>] [--assignees a,b] [--reviewers x,y] [--draft] [--skip-duplicate-check]
```

`prepare` does the following, in order:

1. Fetches `main` and the branch, and checks that the local branch (if any) equals `origin/<branch>`.
2. Checks the commits and picks the designated member.
3. Checks the reviewers and assignees against the member map. Assignees default to the designated member. The designated member can't be a reviewer.
4. Checks the title and body against the same attribution rules CI applies.
5. Checks that no pull request is open for the branch.
6. Appends one line to the body: `Prepared with the team PR broker (operator: Nidhi9864); opened by the designated owner @<login>.` The body is otherwise unchanged.
7. Prints:

```text
OPEN-AS <login> (<name>)
LINK https://github.com/het-lathiya/Group12/compare/main...<branch>?expand=1&title=…&body=…&assignees=…
REVIEWERS <x,y> (choose them in the Reviewers box before creating)
DRAFT yes (…)                         only with --draft
THEN node .claude/tools/pr-broker.mjs verify --branch <branch> …
```

The operator sends the link to the designated member. The member opens it while signed in as themselves, picks the listed reviewers in the sidebar, and presses **Create pull request** (or **Create draft pull request** when `DRAFT yes` is shown).

A body too long for a link is written to a temporary file outside the repository, and the output says to paste it into the description.

`--skip-duplicate-check` is only for when gh can't be reached. The GitHub compare page also shows an existing pull request.

```bash
node .claude/tools/pr-broker.mjs verify (--pr <n> | --branch <name>) [--owner <login>] [--reviewers x,y]
```

`verify` reads the pull request back, works out the designated member from its head branch, and prints `PR #<n> <url> creator=<login>`.

- If someone other than the designated member opened it, it fails with `CREATOR_MISMATCH`. A human closes that pull request, and the member reopens it from a fresh link.
- With `--reviewers`, it also fails with `MISSING_REVIEWERS` until review is requested from each of them.

Exit codes: 0 success, 1 refused, 2 usage error. Errors are one line: `ERROR <CODE>: <message>`.

## Error codes

| Code | Meaning |
| --- | --- |
| `USAGE`, `UNKNOWN_OPTION` | Wrong command, a missing value or an unknown option (for example `--verbose`) |
| `MEMBERS_FILE`, `UNKNOWN_MEMBER` | The member map can't be read, or a login is not in it |
| `GIT_FETCH_FAILED`, `NO_MERGE_BASE` | `origin` can't be fetched, or a shallow clone lacks the common history (`git fetch --depth=200 origin main <branch>`) |
| `BRANCH_NOT_PUSHED` | The branch is not on `origin`, or the local branch differs from `origin/<branch>` |
| `NO_COMMITS` | The branch has no commits on top of the base |
| `UNMAPPED_OR_MISMATCHED_COMMIT` | A commit's author or committer email is not in the map, or author ≠ committer |
| `OWNER_MISMATCH`, `AMBIGUOUS_OWNER`, `OWNER_NOT_AUTHOR` | `--owner` contradicts a single author, is missing for a batch, or has no commit on the branch |
| `REVIEWER_IS_OWNER` | The designated member is in the reviewer list |
| `BODY_ATTRIBUTION` | The title or body would fail the CI attribution check |
| `GH_UNAVAILABLE` | A read-only gh call failed (not signed in, no network) |
| `DUPLICATE_PR` | A pull request is already open for the branch; its number and URL are printed |
| `CREATOR_MISMATCH` | The pull request was opened by someone other than the designated member |
| `MISSING_REVIEWERS` | A listed reviewer has no review request yet |
| `TOOL_MISSING`, `COMMAND_FAILED`, `INTERNAL` | git or gh is not installed, a git command failed, or an unexpected error |

## Guard hook

The guard checks the commands and file edits made in tool sessions that use this repository's `.claude/settings.json`. It does not affect a person's own terminal.

It **blocks**:

- `gh pr create|merge|edit|close|review`;
- `gh api` writes: `-X/--method POST|PATCH|PUT|DELETE`, or fields without `-X GET`;
- `gh auth token|switch|login|logout|refresh` and `gh auth status --show-token`;
- `gh workflow run` of anything but `e2e.yml`, and `gh workflow enable|disable`;
- `security find-generic-password|find-internet-password|dump-keychain`;
- reading `gh/hosts.yml`;
- printing `GH_TOKEN`, `GITHUB_TOKEN` or the whole environment;
- `git push` to `main` (`main`, `HEAD:main`, any refspec ending in `:main`, `HEAD` or no refspec while on `main`, `--all`, `--mirror`);
- `git push --force` or a `+refspec` without `--force-with-lease`.

It **allows**:

- `node .claude/tools/pr-broker.mjs prepare|verify`;
- read-only gh (`pr view/list/checks`, `run view/list/watch`, `api` GET);
- `gh workflow run e2e.yml`;
- `git push` of a feature branch.

Everything it allows still goes through the normal permission rules.

**Changing the guard, its registration in `.claude/settings.json`, the broker or the member map needs explicit human approval.** The guard asks a human before any edit of those files, whether by the edit tools or by a Bash command that writes them.

## Live test

Before the first real use, two members each run one throwaway test.

1. **The member makes a branch.** On their own machine, they create `chore/broker-livetest-<login>` from `origin/main` with one empty commit made under their own git identity, and push it:

```bash
git commit --allow-empty -m "chore: broker live test (<login>)"
```

2. **The operator prepares the link:**

```bash
node .claude/tools/pr-broker.mjs prepare --branch chore/broker-livetest-<login> --title "Broker live test (<login>)" --body-file <file> --draft
```

3. **The member opens the link** and creates the draft pull request.
4. **The operator verifies it.** This must print `creator=<login>`:

```bash
node .claude/tools/pr-broker.mjs verify --branch chore/broker-livetest-<login>
```

5. **Clean up.** The member closes the draft and deletes the branch. The broker can do neither.

## Records

GitHub keeps its own records of who opened each pull request, and the pull-request body says it was prepared with the broker. Nothing about this setup is hidden.

## Tests

```bash
node --test .claude/tools/tests/*.test.mjs
```

The tests run offline. A fake `gh` placed first on `PATH` records every call, and throwaway git repositories with a local `origin` stand in for GitHub. They cover:

- choosing the designated member (single author, batch with and without `--owner`, `--owner` with no commit);
- unmapped emails and author ≠ committer;
- a duplicate pull request and a branch that isn't pushed;
- owner-as-reviewer, attribution in the body and long bodies;
- gh failures;
- `verify` with the right creator, the wrong creator and missing reviewers;
- that only read-only gh calls are made;
- every blocked and allowed guard command, and the ask-a-human edits.
