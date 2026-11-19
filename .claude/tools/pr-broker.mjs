#!/usr/bin/env node
// Team PR broker (IMD-212). Guide: docs/guides/pr-broker.md.
//
// The designated member opens every pull request from their own GitHub session. The broker never
// holds, reads or asks for anyone's credentials and never writes to GitHub. It:
//   prepare  checks the branch (commit identities, designated owner, pushed, no open pull request)
//            and prints a prefilled GitHub link for the designated member to open;
//   verify   reads the pull request back and confirms that its creator is the designated member.
// Its only GitHub calls are the read-only `gh pr list` and `gh pr view` of the operator's gh login.
// It cannot create, edit, merge, close or approve a pull request, delete a branch or push.
//
// Node 22, standard library only. Child processes take argument arrays, never a shell string.
// Exit codes: 0 success, 1 refused (an ERROR line names the code), 2 usage error.
//
// Changing this file, members.json or the guard hook needs explicit human approval
// (the guard hook asks before any such edit).

import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const MEMBERS_FILE =
  process.env.PR_BROKER_MEMBERS_FILE || fileURLToPath(new URL('./members.json', import.meta.url));
const MAX_LINK_LENGTH = 8000;

const USAGE = `usage:
  node .claude/tools/pr-broker.mjs prepare --branch <name> [--base main] --title <t> --body-file <f>
      [--owner <login>] [--assignees a,b] [--reviewers x,y] [--draft] [--skip-duplicate-check]
  node .claude/tools/pr-broker.mjs verify (--pr <n> | --branch <name>) [--owner <login>] [--reviewers x,y]`;

const COMMANDS = {
  prepare: {
    values: ['branch', 'base', 'title', 'body-file', 'owner', 'assignees', 'reviewers'],
    flags: ['draft', 'skip-duplicate-check'],
  },
  verify: { values: ['pr', 'branch', 'owner', 'reviewers'], flags: [] },
};

class BrokerError extends Error {
  constructor(code, message, exitCode = 1) {
    super(message);
    this.code = code;
    this.exitCode = exitCode;
  }
}

function parseArgs(argv) {
  const [command, ...rest] = argv;
  const spec = COMMANDS[command];
  if (!spec) throw new BrokerError('USAGE', `unknown command ${command ?? '(none)'}\n${USAGE}`, 2);
  const opts = {};
  for (let i = 0; i < rest.length; i += 1) {
    const arg = rest[i];
    if (!arg.startsWith('--')) throw new BrokerError('USAGE', `unexpected argument ${arg}`, 2);
    const eq = arg.indexOf('=');
    const name = eq === -1 ? arg.slice(2) : arg.slice(2, eq);
    if (spec.flags.includes(name)) {
      if (eq !== -1) throw new BrokerError('USAGE', `--${name} takes no value`, 2);
      opts[name] = true;
    } else if (spec.values.includes(name)) {
      const value = eq === -1 ? rest[++i] : arg.slice(eq + 1);
      if (value === undefined || value === '') throw new BrokerError('USAGE', `--${name} needs a value`, 2);
      opts[name] = value;
    } else {
      throw new BrokerError('UNKNOWN_OPTION', `unknown option --${name} for ${command}\n${USAGE}`, 2);
    }
  }
  return { command, opts };
}

function list(value) {
  return value ? value.split(',').map((s) => s.trim()).filter(Boolean) : [];
}

function run(cmd, args, { allowFail = false } = {}) {
  const res = spawnSync(cmd, args, {
    encoding: 'utf8',
    env: { ...process.env, GH_PROMPT_DISABLED: '1', GIT_TERMINAL_PROMPT: '0' },
    maxBuffer: 16 * 1024 * 1024,
  });
  if (res.error) {
    if (allowFail) return { ok: false, stdout: '', stderr: String(res.error.message) };
    throw new BrokerError('TOOL_MISSING', `${cmd} could not be started: ${res.error.message}`);
  }
  const out = { ok: res.status === 0, stdout: res.stdout, stderr: res.stderr };
  if (!out.ok && !allowFail) {
    throw new BrokerError('COMMAND_FAILED', `${cmd} ${args[0]} failed: ${out.stderr.trim()}`);
  }
  return out;
}

const git = (args, o) => run('git', args, o);

function loadMembers() {
  let data;
  try {
    data = JSON.parse(readFileSync(MEMBERS_FILE, 'utf8'));
  } catch (err) {
    throw new BrokerError('MEMBERS_FILE', `cannot read ${MEMBERS_FILE}: ${err.message}`);
  }
  const byEmail = new Map();
  const byLogin = new Map();
  for (const m of data.members) {
    byEmail.set(m.email.toLowerCase(), m);
    byLogin.set(m.login.toLowerCase(), m);
  }
  return { repo: data.repo, operator: data.operator, byEmail, byLogin };
}

function memberByLogin(members, login, role) {
  const m = members.byLogin.get(String(login).toLowerCase());
  if (!m) throw new BrokerError('UNKNOWN_MEMBER', `${role} ${login} is not in members.json`);
  return m;
}

function checkBranchName(name) {
  if (!git(['check-ref-format', '--branch', name], { allowFail: true }).ok) {
    throw new BrokerError('USAGE', `invalid branch name ${name}`, 2);
  }
}

function fetchRefs(base, branch) {
  const baseFetch = git(['fetch', '--quiet', 'origin', `+refs/heads/${base}:refs/remotes/origin/${base}`], {
    allowFail: true,
  });
  if (!baseFetch.ok) throw new BrokerError('GIT_FETCH_FAILED', `cannot fetch origin/${base}`);
  const branchFetch = git(
    ['fetch', '--quiet', 'origin', `+refs/heads/${branch}:refs/remotes/origin/${branch}`],
    { allowFail: true },
  );
  if (!branchFetch.ok) {
    throw new BrokerError('BRANCH_NOT_PUSHED', `${branch} is not on origin; push it first`);
  }
  const remoteHead = git(['rev-parse', `refs/remotes/origin/${branch}`]).stdout.trim();
  const local = git(['rev-parse', '--verify', '--quiet', `refs/heads/${branch}`], { allowFail: true });
  if (local.ok && local.stdout.trim() !== remoteHead) {
    throw new BrokerError(
      'BRANCH_NOT_PUSHED',
      `local ${branch} (${local.stdout.trim().slice(0, 7)}) differs from origin/${branch} (${remoteHead.slice(0, 7)}); push it first`,
    );
  }
  if (!git(['merge-base', `origin/${base}`, `origin/${branch}`], { allowFail: true }).ok) {
    throw new BrokerError(
      'NO_MERGE_BASE',
      `no common history between origin/${base} and origin/${branch} in this clone; run git fetch --depth=200 origin ${base} ${branch}`,
    );
  }
  return remoteHead;
}

// Every commit must be authored and committed by the same mapped member (CLAUDE.md §12).
function branchAuthors(members, base, branch) {
  const fmt = '%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1e';
  const out = git(['log', '--reverse', `--format=${fmt}`, `origin/${base}..origin/${branch}`]).stdout;
  const commits = out
    .split('\x1e')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((rec) => {
      const [sha, an, ae, cn, ce] = rec.split('\x1f');
      return { sha, an, ae, cn, ce };
    });
  if (commits.length === 0) throw new BrokerError('NO_COMMITS', `origin/${base}..origin/${branch} has no commits`);
  const bad = [];
  const authors = new Map();
  for (const c of commits) {
    const author = members.byEmail.get(c.ae.toLowerCase());
    const committer = members.byEmail.get(c.ce.toLowerCase());
    let reason = null;
    if (!author) reason = `author email ${c.ae} is not in members.json`;
    else if (!committer) reason = `committer email ${c.ce} is not in members.json`;
    else if (author !== committer || c.an !== c.cn || c.ae.toLowerCase() !== c.ce.toLowerCase()) {
      reason = `author ${c.an} <${c.ae}> differs from committer ${c.cn} <${c.ce}>`;
    }
    if (reason) bad.push(`${c.sha.slice(0, 7)} ${reason}`);
    else authors.set(author.login.toLowerCase(), author);
  }
  if (bad.length) {
    throw new BrokerError('UNMAPPED_OR_MISMATCHED_COMMIT', `commits that break the attribution rule:\n  ${bad.join('\n  ')}`);
  }
  return [...authors.values()];
}

// Never picks an account by default: one author, or an explicit --owner who is one of the authors.
function designatedOwner(members, authors, ownerOpt) {
  if (ownerOpt) memberByLogin(members, ownerOpt, 'owner');
  const owner = ownerOpt?.toLowerCase();
  if (authors.length === 1) {
    if (owner && owner !== authors[0].login.toLowerCase()) {
      throw new BrokerError('OWNER_MISMATCH', `--owner ${ownerOpt} is not the branch's only author ${authors[0].login}`);
    }
    return authors[0];
  }
  const logins = authors.map((a) => a.login).join(', ');
  if (!owner) throw new BrokerError('AMBIGUOUS_OWNER', `the branch has several authors (${logins}); name one with --owner`);
  const found = authors.find((a) => a.login.toLowerCase() === owner);
  if (!found) throw new BrokerError('OWNER_NOT_AUTHOR', `--owner ${ownerOpt} has no commit on the branch (authors: ${logins})`);
  return found;
}

// Mirrors .githooks/commit-msg, which CI also runs on the pull-request body.
function attributionProblem(text) {
  const cleaned = text.replace(/claude\.md/gi, '').replace(/\.claude\//gi, '');
  if (/^[ \t]*co-authored-by:/im.test(cleaned)) return 'a line starts with Co-authored-by:';
  if (/(^|[^A-Za-z0-9_])(anthropic|claude)([^A-Za-z0-9_]|$)/i.test(cleaned)) return 'it names a tool word that CI rejects';
  return null;
}

function gh(args) {
  const res = run('gh', args, { allowFail: true });
  if (!res.ok) {
    const first = (res.stderr || '').trim().split('\n')[0] || 'no output';
    throw new BrokerError('GH_UNAVAILABLE', `gh ${args.slice(0, 2).join(' ')} failed: ${first}`);
  }
  try {
    return JSON.parse(res.stdout);
  } catch {
    throw new BrokerError('GH_UNAVAILABLE', `gh ${args.slice(0, 2).join(' ')} returned unreadable output`);
  }
}

function pathPart(ref) {
  return ref.split('/').map(encodeURIComponent).join('/');
}

function prepare(opts) {
  for (const key of ['branch', 'title', 'body-file']) {
    if (!opts[key]) throw new BrokerError('USAGE', `prepare needs --${key}\n${USAGE}`, 2);
  }
  const base = opts.base || 'main';
  const branch = opts.branch;
  checkBranchName(base);
  checkBranchName(branch);
  if (branch === base) throw new BrokerError('USAGE', 'the branch and the base are the same', 2);

  const members = loadMembers();
  let body;
  try {
    body = readFileSync(opts['body-file'], 'utf8');
  } catch (err) {
    throw new BrokerError('USAGE', `cannot read the body file: ${err.message}`, 2);
  }
  for (const [what, text] of [['title', opts.title], ['body', body]]) {
    const problem = attributionProblem(text);
    if (problem) throw new BrokerError('BODY_ATTRIBUTION', `the ${what} would fail the attribution check: ${problem}`);
  }

  fetchRefs(base, branch);
  const authors = branchAuthors(members, base, branch);
  const owner = designatedOwner(members, authors, opts.owner);

  const reviewers = list(opts.reviewers).map((r) => memberByLogin(members, r, 'reviewer').login);
  const nonOwner = reviewers.filter((r) => r.toLowerCase() !== owner.login.toLowerCase());
  if (nonOwner.length < reviewers.length) {
    throw new BrokerError('REVIEWER_IS_OWNER', `${owner.login} opens the pull request and cannot also review it; name another reviewer`);
  }
  const assignees = (opts.assignees ? list(opts.assignees) : [owner.login]).map(
    (a) => memberByLogin(members, a, 'assignee').login,
  );

  if (opts['skip-duplicate-check']) {
    console.log('WARN DUPLICATE_CHECK_SKIPPED: the GitHub compare page also shows an open pull request for this branch');
  } else {
    const open = gh(['pr', 'list', '--repo', members.repo, '--head', branch, '--state', 'open', '--json', 'number,url,author']);
    if (open.length) {
      const pr = open[0];
      console.log(`PR #${pr.number} ${pr.url} creator=${pr.author?.login ?? 'unknown'}`);
      throw new BrokerError('DUPLICATE_PR', `an open pull request already exists for ${branch}; nothing to do`);
    }
  }

  const fullBody = `${body.replace(/\s+$/, '')}\n\nPrepared with the team PR broker (operator: ${members.operator}); opened by the designated owner @${owner.login}.\n`;
  const params = (withBody) =>
    [
      ['expand', '1'],
      ['title', opts.title],
      ...(withBody ? [['body', fullBody]] : []),
      ['assignees', assignees.join(',')],
    ]
      .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
      .join('&');
  const prefix = `https://github.com/${members.repo}/compare/${pathPart(base)}...${pathPart(branch)}?`;
  let link = prefix + params(true);
  let bodyFile = null;
  if (link.length > MAX_LINK_LENGTH) {
    link = prefix + params(false);
    bodyFile = join(mkdtempSync(join(tmpdir(), 'pr-broker-')), 'body.md');
    writeFileSync(bodyFile, fullBody);
  }

  console.log(`OPEN-AS ${owner.login} (${owner.name})`);
  console.log(`LINK ${link}`);
  if (bodyFile) console.log(`BODY too long for a link: paste the contents of ${bodyFile} into the description`);
  console.log(`REVIEWERS ${reviewers.length ? reviewers.join(',') : 'none'} (choose them in the Reviewers box before creating)`);
  if (opts.draft) console.log('DRAFT yes (use the arrow on the green button: Create draft pull request)');
  const reviewArg = reviewers.length ? ` --reviewers ${reviewers.join(',')}` : '';
  const ownerArg = authors.length > 1 ? ` --owner ${owner.login}` : '';
  console.log(`THEN node .claude/tools/pr-broker.mjs verify --branch ${branch}${ownerArg}${reviewArg}`);
}

function verify(opts) {
  if (!opts.pr === !opts.branch) throw new BrokerError('USAGE', `verify needs exactly one of --pr or --branch\n${USAGE}`, 2);
  if (opts.pr && !/^[1-9][0-9]*$/.test(opts.pr)) throw new BrokerError('USAGE', '--pr must be a number', 2);
  if (opts.branch) checkBranchName(opts.branch);
  const members = loadMembers();
  const pr = gh([
    'pr', 'view', opts.pr || opts.branch, '--repo', members.repo,
    '--json', 'number,url,author,headRefName,baseRefName,state,isDraft,reviewRequests',
  ]);
  fetchRefs(pr.baseRefName, pr.headRefName);
  const authors = branchAuthors(members, pr.baseRefName, pr.headRefName);
  const owner = designatedOwner(members, authors, opts.owner);
  const creator = pr.author?.login ?? 'unknown';
  console.log(`PR #${pr.number} ${pr.url} creator=${creator}`);
  if (creator.toLowerCase() !== owner.login.toLowerCase()) {
    throw new BrokerError('CREATOR_MISMATCH', `the pull request was opened by ${creator}, not the designated owner ${owner.login}; a human should close it and the owner should reopen it from the link`);
  }
  const requested = new Set((pr.reviewRequests || []).map((r) => String(r.login || '').toLowerCase()));
  const missing = list(opts.reviewers).filter((r) => !requested.has(r.toLowerCase()));
  if (missing.length) {
    throw new BrokerError('MISSING_REVIEWERS', `review not yet requested from ${missing.join(', ')}; the owner adds them on the pull request page`);
  }
}

function main() {
  try {
    const { command, opts } = parseArgs(process.argv.slice(2));
    if (command === 'prepare') prepare(opts);
    else verify(opts);
    return 0;
  } catch (err) {
    if (err instanceof BrokerError) {
      console.error(`ERROR ${err.code}: ${err.message}`);
      return err.exitCode;
    }
    console.error(`ERROR INTERNAL: ${err.message}`);
    return 1;
  }
}

process.exitCode = main();
