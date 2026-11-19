import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { guard } from './helpers.mjs';

let repo;
before(() => {
  repo = mkdtempSync(join(tmpdir(), 'guard-test-'));
  spawnSync('git', ['init', '--quiet', '--initial-branch=main', repo]);
});
after(() => rmSync(repo, { recursive: true, force: true }));

const bash = (command, cwd = repo) => guard({ tool_name: 'Bash', tool_input: { command }, cwd });
const checkout = (branch) => spawnSync('git', ['-C', repo, 'checkout', '--quiet', '-B', branch]);

const BLOCKED = [
  'gh pr create --base main --head feat/x --title T --body-file /tmp/b.md',
  'gh pr merge 12 --rebase',
  'gh pr edit 12 --add-reviewer het-lathiya',
  'gh pr close 12',
  'gh pr review 12 --approve',
  'gh -R het-lathiya/Group12 pr create',
  'gh api -X POST repos/het-lathiya/Group12/pulls',
  'gh api --method PATCH repos/het-lathiya/Group12/pulls/1',
  'gh api --method=PUT repos/het-lathiya/Group12/pulls/1/merge',
  'gh api -XDELETE repos/het-lathiya/Group12/git/refs/heads/x',
  'gh api repos/het-lathiya/Group12/issues -f title=x',
  'gh auth token',
  'gh auth token --hostname github.com --user jeelfefar2141',
  'gh auth switch --hostname github.com --user Nidhi9864',
  'gh auth login --web',
  'gh auth logout --user jeelfefar2141',
  'gh auth refresh -s repo',
  'gh auth status --show-token',
  'gh workflow run deploy-production.yml',
  'gh workflow disable ci.yml',
  'security find-generic-password -s group12-pr-broker -a jeelfefar2141 -w',
  'security find-internet-password -s github.com',
  'security dump-keychain',
  'cat ~/.config/gh/hosts.yml',
  'grep oauth_token "$HOME/.config/gh/hosts.yml"',
  'echo $GH_TOKEN',
  'echo "token: ${GITHUB_TOKEN}"',
  'printf "%s" "$GH_TOKEN"',
  'printenv GH_TOKEN',
  'printenv',
  'env | grep TOKEN',
  'env',
  'export -p',
  'set',
  'cat /proc/self/environ',
  'git push origin main',
  'git push origin HEAD:main',
  'git push origin feat/x:main',
  'git push origin feat/x:refs/heads/main',
  'git push origin +feat/x',
  'git push --force origin feat/x',
  'git push -f origin feat/x',
  'git push --all origin',
  'git -C . push origin main',
  'cd apps && git push origin main',
  'npm test; gh pr merge 3',
  'bash -c "gh pr create --title x"',
  'sh -c \'git push origin main\'',
  'eval gh auth token',
  'X=$(gh auth token) && echo ok',
  'echo `security find-generic-password -s x -w`',
  'GH_TOKEN=abc gh pr create --title x',
];

const ALLOWED = [
  'node .claude/tools/pr-broker.mjs prepare --branch feat/x --title T --body-file /tmp/b.md',
  'node .claude/tools/pr-broker.mjs verify --pr 12',
  'gh pr view 12 --json author',
  'gh pr list --state open',
  'gh pr checks 12',
  'gh run view 123 --log-failed',
  'gh run list --branch feat/x',
  'gh run watch 123',
  'gh api repos/het-lathiya/Group12/pulls/12',
  'gh api -X GET repos/het-lathiya/Group12/pulls -f state=open',
  'gh auth status --active',
  'gh workflow run e2e.yml',
  'git push origin feat/x',
  'git push -u origin chore/IMD-212-pr-broker',
  'git push --force-with-lease origin feat/x',
  'git status && git log --oneline -3',
  'echo "$PATH"',
  'node --test .claude/tools/tests',
  'make check',
];

for (const command of BLOCKED) {
  test(`blocks: ${command}`, () => {
    const r = bash(command);
    assert.equal(r.code, 2, `expected a block, got ${r.code} ${r.out}`);
    assert.match(r.err, /^Blocked by \.claude\/hooks\/guard\.mjs: /);
  });
}

for (const command of ALLOWED) {
  test(`allows: ${command}`, () => {
    checkout('feat/x');
    const r = bash(command);
    assert.equal(r.code, 0, r.err);
    assert.equal(r.out, '');
  });
}

test('git push of HEAD or with no refspec depends on the current branch', () => {
  checkout('main');
  assert.equal(bash('git push').code, 2);
  assert.equal(bash('git push origin HEAD').code, 2);
  checkout('feat/y');
  assert.equal(bash('git push').code, 0);
  assert.equal(bash('git push -u origin HEAD').code, 0);
});

test('edits of the guard, settings, broker and member map ask a human', () => {
  for (const file_path of ['/r/.claude/hooks/guard.mjs', '/r/.claude/settings.json', '/r/.claude/tools/pr-broker.mjs', '/r/.claude/tools/members.json']) {
    const r = guard({ tool_name: 'Edit', tool_input: { file_path } });
    assert.equal(r.code, 0);
    assert.equal(JSON.parse(r.out).hookSpecificOutput.permissionDecision, 'ask');
  }
  for (const command of ['sed -i s/x/y/ .claude/hooks/guard.mjs', 'echo {} > .claude/settings.json', 'rm .claude/tools/members.json']) {
    assert.equal(JSON.parse(bash(command).out).hookSpecificOutput.permissionDecision, 'ask', command);
  }
  const other = guard({ tool_name: 'Write', tool_input: { file_path: '/r/docs/guides/pr-broker.md' } });
  assert.equal(other.out, '');
  assert.equal(bash('cat .claude/hooks/guard.mjs').out, '');
});

test('input the guard cannot read is blocked, not waved through', () => {
  assert.equal(bash('echo "unbalanced').code, 2);
});
