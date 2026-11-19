#!/usr/bin/env node
// PreToolUse guard for this repository (IMD-212). Registered in .claude/settings.json.
// Guide: docs/guides/pr-broker.md.
//
// CHANGING THIS FILE, ITS REGISTRATION, THE BROKER (.claude/tools/pr-broker.mjs) OR ITS MEMBER MAP
// NEEDS EXPLICIT HUMAN APPROVAL. The guard itself asks for approval before any edit of those files.
//
// Bash commands that are blocked (exit 2, the reason on stderr):
//   gh pr create|merge|edit|close|review    (the designated member opens the PR from the broker link)
//   gh api writes: -X/--method POST|PATCH|PUT|DELETE, or -f/-F/--field/--raw-field/--input without -X GET
//   gh auth token|switch|login|logout|refresh, gh auth status --show-token
//   gh workflow run of anything but e2e.yml, gh workflow enable|disable
//   security find-generic-password|find-internet-password|dump-keychain
//   reading gh/hosts.yml; printing GH_TOKEN, GITHUB_TOKEN or the whole environment
//   git push to main (main, HEAD:main, any refspec ending in :main, HEAD or no refspec while on main,
//   --all, --mirror); git push --force or +refspec without --force-with-lease
// Everything else passes on to the normal permission rules, including:
//   node .claude/tools/pr-broker.mjs prepare|verify, read-only gh (pr view/list/checks,
//   run view/list/watch, api GET), gh workflow run e2e.yml, git push of a feature branch.
// Edits of the protected files (Edit/Write tools, or a Bash command that writes them) ask a human.

import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';

const PROTECTED = [/(^|\/)\.claude\/hooks\//, /(^|\/)\.claude\/settings(\.local)?\.json$/, /(^|\/)\.claude\/tools\/pr-broker\.mjs$/, /(^|\/)\.claude\/tools\/members\.json$/];
const TOKEN_VARS = /\$\{?(GH_TOKEN|GITHUB_TOKEN|GH_ENTERPRISE_TOKEN|GITHUB_ENTERPRISE_TOKEN)\b/;
const TOKEN_NAMES = /^(GH_TOKEN|GITHUB_TOKEN|GH_ENTERPRISE_TOKEN|GITHUB_ENTERPRISE_TOKEN)$/;
const WRAPPERS = new Set(['sudo', 'command', 'exec', 'nohup', 'time', 'nice', 'xargs', 'builtin']);
const SHELLS = new Set(['bash', 'sh', 'zsh', 'dash', 'ksh']);

// Pulls $(...) and `...` bodies out (they run too) and replaces them with a placeholder.
function extractSubstitutions(cmd, found) {
  let out = '';
  let quote = null;
  for (let i = 0; i < cmd.length; i += 1) {
    const ch = cmd[i];
    if (ch === '\\' && quote !== "'") { out += ch + (cmd[i + 1] ?? ''); i += 1; continue; }
    if (quote === "'") { if (ch === "'") quote = null; out += ch; continue; }
    if (ch === "'" && !quote) { quote = "'"; out += ch; continue; }
    if (ch === '"') { quote = quote === '"' ? null : '"'; out += ch; continue; }
    if (ch === '$' && cmd[i + 1] === '(') {
      let depth = 1;
      let j = i + 2;
      for (; j < cmd.length && depth; j += 1) {
        if (cmd[j] === '(') depth += 1;
        else if (cmd[j] === ')') depth -= 1;
      }
      found.push(cmd.slice(i + 2, j - 1));
      out += 'SUBST';
      i = j - 1;
      continue;
    }
    if (ch === '`') {
      const j = cmd.indexOf('`', i + 1);
      const end = j === -1 ? cmd.length : j;
      found.push(cmd.slice(i + 1, end));
      out += 'SUBST';
      i = end;
      continue;
    }
    out += ch;
  }
  return out;
}

// Splits into simple commands (on ; & | newline and parentheses) and words, honouring quotes.
function segments(cmd) {
  const segs = [];
  let words = [];
  let word = null;
  let quote = null;
  const endWord = () => { if (word !== null) { words.push(word); word = null; } };
  const endSeg = () => { endWord(); if (words.length) segs.push(words); words = []; };
  for (let i = 0; i < cmd.length; i += 1) {
    const ch = cmd[i];
    if (quote) {
      if (ch === quote) quote = null;
      else if (ch === '\\' && quote === '"' && i + 1 < cmd.length) { word += cmd[i + 1]; i += 1; }
      else word += ch;
      continue;
    }
    if (ch === "'" || ch === '"') { quote = ch; word ??= ''; continue; }
    if (ch === '\\') { word = (word ?? '') + (cmd[i + 1] ?? ''); i += 1; continue; }
    if (';&|\n()'.includes(ch)) {
      if (ch === '&' && (cmd[i - 1] === '>' || cmd[i + 1] === '>')) { word = (word ?? '') + ch; continue; }
      endSeg();
      continue;
    }
    if (ch === ' ' || ch === '\t') { endWord(); continue; }
    if (ch === '>' || ch === '<') {
      endWord();
      let op = ch;
      while (cmd[i + 1] === '>' || cmd[i + 1] === '&') { op += cmd[i + 1]; i += 1; }
      words.push(op);
      continue;
    }
    word = (word ?? '') + ch;
  }
  if (quote) throw new Error('unbalanced quote');
  endSeg();
  return segs;
}

// Drops leading VAR=value words and wrapper commands; returns the words of the real command.
function unwrap(words) {
  let w = words.slice();
  let envDump = false;
  for (;;) {
    while (w.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(w[0])) w = w.slice(1);
    if (!w.length) break;
    const name = basename(w[0]);
    if (name === 'env') {
      w = w.slice(1);
      while (w.length && (w[0].startsWith('-') || /^[A-Za-z_][A-Za-z0-9_]*=/.test(w[0]))) {
        w = w.slice(w[0] === '-u' || w[0] === '-C' ? 2 : 1);
      }
      if (!w.length) envDump = true;
      continue;
    }
    if (WRAPPERS.has(name)) {
      w = w.slice(1);
      while (w.length && w[0].startsWith('-')) w = w.slice(1);
      continue;
    }
    break;
  }
  return { words: w, envDump };
}

function positionals(args, valueFlags = []) {
  const pos = [];
  for (let i = 0; i < args.length; i += 1) {
    const a = args[i];
    if (a === '--') { pos.push(...args.slice(i + 1)); break; }
    if (a.startsWith('-')) {
      if (valueFlags.includes(a)) i += 1;
      continue;
    }
    pos.push(a);
  }
  return pos;
}

function checkGh(args) {
  const [group, sub] = positionals(args, ['-R', '--repo', '--hostname', '-H', '--header']);
  if (group === 'pr' && ['create', 'merge', 'edit', 'close', 'review'].includes(sub)) {
    return `gh pr ${sub} is blocked: the designated member opens pull requests from the link printed by node .claude/tools/pr-broker.mjs prepare, and merging stays with the operator`;
  }
  if (group === 'auth') {
    if (['token', 'switch', 'login', 'logout', 'refresh'].includes(sub)) return `gh auth ${sub} is blocked: credentials and the active account are handled only by people`;
    if (sub === 'status' && args.some((a) => a === '--show-token' || a === '-t')) return 'gh auth status --show-token is blocked: tokens are never printed';
  }
  if (group === 'workflow') {
    if (sub === 'run') {
      const target = positionals(args, ['-R', '--repo', '-r', '--ref', '-f', '-F', '--field', '--raw-field'])[2];
      if (target !== 'e2e.yml') return `gh workflow run ${target ?? ''} is blocked: only gh workflow run e2e.yml is allowed`;
    }
    if (sub === 'enable' || sub === 'disable') return `gh workflow ${sub} is blocked: workflow changes need a human`;
  }
  if (group === 'api') {
    let method = null;
    let fields = false;
    for (let i = 0; i < args.length; i += 1) {
      const a = args[i];
      if (a === '-X' || a === '--method') method = (args[i + 1] || '').toUpperCase();
      else if (a.startsWith('--method=')) method = a.slice(9).toUpperCase();
      else if (/^-X./.test(a)) method = a.slice(2).toUpperCase();
      else if (['-f', '-F', '--field', '--raw-field', '--input'].includes(a) || /^(--field|--raw-field|--input)=/.test(a) || /^-[fF]./.test(a)) fields = true;
    }
    if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(method)) return `gh api -X ${method} is blocked: only read-only GET calls are allowed`;
    if (fields && method !== 'GET') return 'gh api with fields defaults to POST and is blocked: add -X GET for a read-only call';
  }
  return null;
}

function currentBranch(dir) {
  const res = spawnSync('git', ['symbolic-ref', '--quiet', '--short', 'HEAD'], { cwd: dir, encoding: 'utf8' });
  return res.status === 0 ? res.stdout.trim() : null;
}

function checkGit(args, cwd) {
  let dir = cwd;
  let i = 0;
  for (; i < args.length && args[i].startsWith('-'); i += 1) {
    if (args[i] === '-C') { dir = args[i + 1]?.startsWith('/') ? args[i + 1] : `${dir}/${args[i + 1]}`; i += 1; }
    else if (args[i] === '-c') i += 1;
  }
  if (args[i] !== 'push') return null;
  const rest = args.slice(i + 1);
  let force = false;
  let lease = false;
  let del = false;
  for (const a of rest) {
    if (a === '--force' || a === '-f' || (/^-[a-zA-Z]+$/.test(a) && a.includes('f'))) force = true;
    if (a.startsWith('--force-with-lease')) lease = true;
    if (a === '--delete' || a === '-d') del = true;
    if (a === '--all' || a === '--mirror' || a === '--branches') return `git push ${a} is blocked: it would push main`;
  }
  const pos = positionals(rest, ['--repo', '-o', '--push-option', '--receive-pack', '--exec']);
  const specs = pos.slice(1);
  if (specs.some((s) => s.startsWith('+'))) force = true;
  if (force && !lease) return 'git push --force is blocked: use --force-with-lease on your own feature branch';
  const isMain = (ref) => ref.replace(/^refs\/heads\//, '') === 'main';
  for (const raw of specs) {
    const spec = raw.replace(/^\+/, '');
    const colon = spec.lastIndexOf(':');
    const dst = colon === -1 ? spec : spec.slice(colon + 1);
    const src = colon === -1 ? spec : spec.slice(0, colon);
    if (isMain(dst) || (colon === -1 && isMain(src))) return `git push to main is blocked (${raw}): main moves only by the operator's fast-forward merge`;
    if (!del && colon === -1 && (spec === 'HEAD' || spec === '@')) {
      const branch = currentBranch(dir);
      if (branch === null || branch === 'main') return 'git push HEAD is blocked: it would push main or the current branch is unknown; name the feature branch';
    }
  }
  if (!specs.length) {
    const branch = currentBranch(dir);
    if (branch === null || branch === 'main') return 'git push without a branch is blocked here: it would push main or the current branch is unknown; name the feature branch';
  }
  return null;
}

const isProtected = (p) => PROTECTED.some((re) => re.test(String(p).replace(/\\/g, '/')));
const WRITERS = new Set(['tee', 'mv', 'cp', 'rm', 'truncate', 'ln', 'chmod', 'install', 'dd', 'touch']);

function writesProtected(words) {
  const name = basename(words[0]);
  const args = words.slice(1);
  for (let i = 0; i < words.length - 1; i += 1) {
    if (/^\d*>{1,2}$|^&>$/.test(words[i]) && isProtected(words[i + 1])) return true;
  }
  if (!args.some(isProtected)) return false;
  if (WRITERS.has(name)) return true;
  if ((name === 'sed' || name === 'perl') && args.some((a) => /^-[a-zA-Z]*i/.test(a) || a.startsWith('--in-place'))) return true;
  if (name === 'git' && args.some((a) => ['checkout', 'restore', 'rm', 'mv', 'apply'].includes(a))) return true;
  return false;
}

function analyse(command, cwd, depth = 0) {
  if (depth > 5) return { deny: 'command nesting is too deep to check' };
  if (/gh\/hosts\.ya?ml/.test(command)) return { deny: 'reading the gh credential file hosts.yml is blocked' };
  if (/\/proc\/[^/\s]+\/environ/.test(command)) return { deny: 'reading a process environment is blocked: it can hold tokens' };
  const subs = [];
  const flat = extractSubstitutions(command, subs);
  for (const s of subs) {
    const r = analyse(s, cwd, depth + 1);
    if (r.deny || r.ask) return r;
  }
  let ask = null;
  for (const seg of segments(flat)) {
    const { words, envDump } = unwrap(seg);
    if (envDump) return { deny: 'printing the whole environment is blocked: it can hold GH_TOKEN or GITHUB_TOKEN' };
    if (!words.length) continue;
    const name = basename(words[0]);
    const args = words.slice(1);
    if (SHELLS.has(name)) {
      const c = args.indexOf('-c');
      if (c !== -1 && args[c + 1] !== undefined) {
        const r = analyse(args[c + 1], cwd, depth + 1);
        if (r.deny) return r;
        ask ??= r.ask;
      }
      continue;
    }
    if (name === 'eval') {
      const r = analyse(args.join(' '), cwd, depth + 1);
      if (r.deny) return r;
      ask ??= r.ask;
      continue;
    }
    if (['echo', 'printf', 'print'].includes(name) && args.some((a) => TOKEN_VARS.test(a))) return { deny: `${name} of a GitHub token variable is blocked` };
    if (name === 'printenv' && (!positionals(args).length || args.some((a) => TOKEN_NAMES.test(a)))) return { deny: 'printenv of a GitHub token or the whole environment is blocked' };
    if (name === 'set' && !args.length) return { deny: 'set without arguments prints the environment and is blocked' };
    if ((name === 'export' || name === 'declare' || name === 'typeset') && (args.some((a) => TOKEN_NAMES.test(a)) || (args.some((a) => /^-[a-zA-Z]*[px]/.test(a)) && !positionals(args).length) || !args.length)) {
      return { deny: `${name} that lists variables is blocked: it can print GH_TOKEN or GITHUB_TOKEN` };
    }
    if (args.some((a) => TOKEN_VARS.test(a)) && ['cat', 'tee', 'logger'].includes(name)) return { deny: 'writing a GitHub token variable is blocked' };
    if (name === 'security' && ['find-generic-password', 'find-internet-password', 'dump-keychain'].includes(positionals(args)[0])) {
      return { deny: `security ${positionals(args)[0]} is blocked: Keychain secrets are never read here` };
    }
    const reason = name === 'gh' ? checkGh(args) : name === 'git' ? checkGit(args, cwd) : null;
    if (reason) return { deny: reason };
    if (writesProtected(words)) ask ??= 'this command changes the guard hook, the settings, the PR broker or its member map; that needs explicit human approval';
  }
  return ask ? { ask } : {};
}

function decide(input) {
  const tool = input.tool_name;
  const ti = input.tool_input || {};
  if (tool === 'Bash') return analyse(String(ti.command ?? ''), input.cwd || process.cwd());
  if (['Edit', 'Write', 'MultiEdit', 'NotebookEdit'].includes(tool) && isProtected(ti.file_path ?? ti.notebook_path ?? '')) {
    return { ask: 'this edit changes the guard hook, the settings, the PR broker or its member map; that needs explicit human approval' };
  }
  return {};
}

let result;
try {
  result = decide(JSON.parse(readFileSync(0, 'utf8') || '{}'));
} catch (err) {
  result = { deny: `guard could not check this command (${err.message}); rewrite it more simply` };
}
if (result.deny) {
  process.stderr.write(`Blocked by .claude/hooks/guard.mjs: ${result.deny}\n`);
  process.exit(2);
}
if (result.ask) {
  process.stdout.write(`${JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'ask', permissionDecisionReason: result.ask } })}\n`);
}
process.exit(0);
