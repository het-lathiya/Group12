// Offline fixtures for the PR broker tests: a bare "origin" repository, a working clone, member
// identities from members.json and a fake gh placed first on PATH that records every call.
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, existsSync, chmodSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const BROKER = fileURLToPath(new URL('../pr-broker.mjs', import.meta.url));
export const GUARD = fileURLToPath(new URL('../../hooks/guard.mjs', import.meta.url));
export const MEMBERS = JSON.parse(readFileSync(new URL('../members.json', import.meta.url), 'utf8')).members;
export const who = (member) => MEMBERS.find((m) => m.member === member);

const FAKE_GH = `#!/usr/bin/env node
const fs = require('node:fs');
const args = process.argv.slice(2);
fs.appendFileSync(process.env.FAKE_GH_LOG, JSON.stringify({ args }) + '\\n');
const sc = JSON.parse(fs.readFileSync(process.env.FAKE_GH_SCENARIO, 'utf8'));
if (sc.fail) { process.stderr.write(sc.fail + '\\n'); process.exit(1); }
const key = args.slice(0, 2).join(' ');
if (key === 'pr list') { process.stdout.write(JSON.stringify(sc.prList ?? [])); process.exit(0); }
if (key === 'pr view') { process.stdout.write(JSON.stringify(sc.prView)); process.exit(0); }
process.stderr.write('fake gh: unexpected call ' + key + '\\n');
process.exit(3);
`;

function sh(cwd, args, env = {}) {
  const res = spawnSync('git', args, { cwd, encoding: 'utf8', env: { ...process.env, ...env } });
  if (res.status !== 0) throw new Error(`git ${args.join(' ')} failed: ${res.stderr}`);
  return res.stdout.trim();
}

const idEnv = (author, committer = author) => ({
  GIT_AUTHOR_NAME: author.name,
  GIT_AUTHOR_EMAIL: author.email,
  GIT_COMMITTER_NAME: committer.name,
  GIT_COMMITTER_EMAIL: committer.email,
});

export function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'broker-test-'));
  const origin = join(root, 'origin.git');
  const work = join(root, 'work');
  const bin = join(root, 'bin');
  mkdirSync(bin);
  writeFileSync(join(bin, 'gh'), FAKE_GH);
  chmodSync(join(bin, 'gh'), 0o755);
  const log = join(root, 'gh-calls.jsonl');
  const scenario = join(root, 'scenario.json');
  writeFileSync(scenario, '{}');
  sh(root, ['init', '--quiet', '--bare', '--initial-branch=main', origin]);
  sh(root, ['clone', '--quiet', origin, work]);
  sh(work, ['checkout', '--quiet', '-B', 'main']);
  sh(work, ['commit', '--quiet', '--allow-empty', '-m', 'chore: base'], idEnv(who('Kirtan')));
  sh(work, ['push', '--quiet', 'origin', 'main']);

  const f = {
    root,
    work,
    bodyFile: join(root, 'body.md'),
    setScenario: (obj) => writeFileSync(scenario, JSON.stringify(obj)),
    ghCalls: () => (existsSync(log) ? readFileSync(log, 'utf8').trim().split('\n').filter(Boolean).map((l) => JSON.parse(l).args) : []),
    // commits: [{ author: member, committer?: member-like {name,email} }]
    branch(name, commits, { push = true } = {}) {
      sh(work, ['checkout', '--quiet', '-B', name, 'origin/main']);
      commits.forEach((c, i) => sh(work, ['commit', '--quiet', '--allow-empty', '-m', `chore: ${name} ${i}`], idEnv(c.author, c.committer)));
      if (push) sh(work, ['push', '--quiet', '--force', 'origin', name]);
      sh(work, ['checkout', '--quiet', 'main']);
      return sh(work, ['rev-parse', name]);
    },
    addLocalCommit(name, member) {
      sh(work, ['checkout', '--quiet', name]);
      sh(work, ['commit', '--quiet', '--allow-empty', '-m', 'chore: local only'], idEnv(member));
      sh(work, ['checkout', '--quiet', 'main']);
    },
    status: () => sh(work, ['status', '--porcelain']),
    broker(args) {
      const res = spawnSync(process.execPath, [BROKER, ...args], {
        cwd: work,
        encoding: 'utf8',
        env: { ...process.env, PATH: `${bin}:${process.env.PATH}`, FAKE_GH_LOG: log, FAKE_GH_SCENARIO: scenario },
      });
      return { code: res.status, out: res.stdout, err: res.stderr };
    },
    cleanup: () => rmSync(root, { recursive: true, force: true }),
  };
  writeFileSync(f.bodyFile, 'Summary of the change.\n\nTests: listed in the part record.\n');
  return f;
}

export function guard(input) {
  const res = spawnSync(process.execPath, [GUARD], { input: JSON.stringify(input), encoding: 'utf8' });
  return { code: res.status, out: res.stdout, err: res.stderr };
}
