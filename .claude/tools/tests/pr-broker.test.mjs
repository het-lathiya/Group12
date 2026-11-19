import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { fixture, who } from './helpers.mjs';

let f;
before(() => { f = fixture(); });
after(() => f.cleanup());

const linkOf = (out) => new URL(out.match(/^LINK (\S+)$/m)[1]);
const prepare = (branch, extra = []) =>
  f.broker(['prepare', '--branch', branch, '--title', `Title for ${branch}`, '--body-file', f.bodyFile, ...extra]);

test("Jeel's branch is prepared for Jeel's account", () => {
  f.setScenario({ prList: [] });
  f.branch('feat/jeel-part', [{ author: who('Jeel') }, { author: who('Jeel') }]);
  const r = prepare('feat/jeel-part', ['--reviewers', 'het-lathiya']);
  assert.equal(r.code, 0, r.err);
  assert.match(r.out, /^OPEN-AS jeelfefar2141 \(Jeel Fefar\)$/m);
  const link = linkOf(r.out);
  assert.equal(link.origin + link.pathname, 'https://github.com/het-lathiya/Group12/compare/main...feat/jeel-part');
  assert.equal(link.searchParams.get('expand'), '1');
  assert.equal(link.searchParams.get('title'), 'Title for feat/jeel-part');
  assert.equal(link.searchParams.get('assignees'), 'jeelfefar2141');
  const body = link.searchParams.get('body');
  assert.ok(body.startsWith('Summary of the change.\n\nTests: listed in the part record.\n\n'));
  assert.ok(body.endsWith('Prepared with the team PR broker (operator: Nidhi9864); opened by the designated owner @jeelfefar2141.\n'));
  assert.match(r.out, /^REVIEWERS het-lathiya /m);
  assert.match(r.out, /^THEN node \.claude\/tools\/pr-broker\.mjs verify --branch feat\/jeel-part --reviewers het-lathiya$/m);
});

test("Krrish's branch is prepared for Krrish's account", () => {
  f.setScenario({ prList: [] });
  f.branch('fix/krrish-part', [{ author: who('Krrish') }]);
  const r = prepare('fix/krrish-part', ['--draft', '--assignees', 'Assassin-byte,kirtan-S111']);
  assert.equal(r.code, 0, r.err);
  assert.match(r.out, /^OPEN-AS Assassin-byte \(Krrish Kamani\)$/m);
  assert.equal(linkOf(r.out).searchParams.get('assignees'), 'Assassin-byte,kirtan-S111');
  assert.match(r.out, /^DRAFT yes/m);
});

test('multi-member branch: refused without --owner, accepted with an author, refused with a non-author', () => {
  f.setScenario({ prList: [] });
  f.branch('feat/batch', [{ author: who('Jeel') }, { author: who('Manya') }]);
  const none = prepare('feat/batch');
  assert.equal(none.code, 1);
  assert.match(none.err, /^ERROR AMBIGUOUS_OWNER: .*jeelfefar2141, manyarana/m);
  const ok = prepare('feat/batch', ['--owner', 'manyarana']);
  assert.equal(ok.code, 0, ok.err);
  assert.match(ok.out, /^OPEN-AS manyarana /m);
  assert.match(ok.out, /verify --branch feat\/batch --owner manyarana$/m);
  const stranger = prepare('feat/batch', ['--owner', 'het-lathiya']);
  assert.equal(stranger.code, 1);
  assert.match(stranger.err, /^ERROR OWNER_NOT_AUTHOR:/m);
});

test('single-author branch with a different --owner is refused', () => {
  f.branch('feat/single', [{ author: who('Junaid') }]);
  const r = prepare('feat/single', ['--owner', 'Malhar1112-v']);
  assert.equal(r.code, 1);
  assert.match(r.err, /^ERROR OWNER_MISMATCH:/m);
});

test('an unmapped email is refused and the sha is listed', () => {
  const sha = f.branch('feat/unmapped', [{ author: { name: 'Someone Else', email: 'someone@example.com' } }]);
  const r = prepare('feat/unmapped');
  assert.equal(r.code, 1);
  assert.match(r.err, /^ERROR UNMAPPED_OR_MISMATCHED_COMMIT:/m);
  assert.ok(r.err.includes(sha.slice(0, 7)));
});

test('author different from committer is refused', () => {
  const sha = f.branch('feat/mixed', [{ author: who('Jeel'), committer: who('Nidhi') }]);
  const r = prepare('feat/mixed');
  assert.equal(r.code, 1);
  assert.match(r.err, /^ERROR UNMAPPED_OR_MISMATCHED_COMMIT:/m);
  assert.ok(r.err.includes(`${sha.slice(0, 7)} author Jeel Fefar`));
});

test('an open pull request for the branch stops the broker', () => {
  f.branch('feat/dup', [{ author: who('Manasvi') }]);
  f.setScenario({ prList: [{ number: 41, url: 'https://github.com/het-lathiya/Group12/pull/41', author: { login: 'Manasvi1704' } }] });
  const r = prepare('feat/dup');
  assert.equal(r.code, 1);
  assert.match(r.out, /^PR #41 https:\/\/github\.com\/het-lathiya\/Group12\/pull\/41 creator=Manasvi1704$/m);
  assert.match(r.err, /^ERROR DUPLICATE_PR:/m);
  assert.doesNotMatch(r.out, /^LINK/m);
});

test('a branch that is not pushed, or not on origin, is refused', () => {
  f.setScenario({ prList: [] });
  f.branch('feat/ahead', [{ author: who('Het') }]);
  f.addLocalCommit('feat/ahead', who('Het'));
  const ahead = prepare('feat/ahead');
  assert.equal(ahead.code, 1);
  assert.match(ahead.err, /^ERROR BRANCH_NOT_PUSHED: local feat\/ahead/m);
  f.branch('feat/local-only', [{ author: who('Het') }], { push: false });
  const missing = prepare('feat/local-only');
  assert.equal(missing.code, 1);
  assert.match(missing.err, /^ERROR BRANCH_NOT_PUSHED: feat\/local-only is not on origin/m);
});

test('the owner cannot be a reviewer; unknown members are refused', () => {
  f.setScenario({ prList: [] });
  f.branch('feat/rev', [{ author: who('Malhar') }]);
  const self = prepare('feat/rev', ['--reviewers', 'het-lathiya,Malhar1112-v']);
  assert.equal(self.code, 1);
  assert.match(self.err, /^ERROR REVIEWER_IS_OWNER:/m);
  const unknown = prepare('feat/rev', ['--reviewers', 'not-a-member']);
  assert.equal(unknown.code, 1);
  assert.match(unknown.err, /^ERROR UNKNOWN_MEMBER: reviewer not-a-member/m);
});

test('a body that would fail the attribution check is refused', () => {
  f.setScenario({ prList: [] });
  f.branch('feat/attr', [{ author: who('Jeel') }]);
  const bad = `${f.root}/bad-body.md`;
  writeFileSync(bad, 'Change.\n\nCo-authored-by: Someone <someone@example.com>\n');
  const r = f.broker(['prepare', '--branch', 'feat/attr', '--title', 'T', '--body-file', bad]);
  assert.equal(r.code, 1);
  assert.match(r.err, /^ERROR BODY_ATTRIBUTION:/m);
});

test('a body too long for a link goes to a temporary file outside the repository', () => {
  f.setScenario({ prList: [] });
  f.branch('feat/long', [{ author: who('Jeel') }]);
  const long = `${f.root}/long-body.md`;
  writeFileSync(long, 'line of text\n'.repeat(1200));
  const r = f.broker(['prepare', '--branch', 'feat/long', '--title', 'T', '--body-file', long]);
  assert.equal(r.code, 0, r.err);
  assert.equal(linkOf(r.out).searchParams.get('body'), null);
  const file = r.out.match(/paste the contents of (\S+) into/)[1];
  assert.ok(!file.startsWith(f.work));
  assert.match(readFileSync(file, 'utf8'), /opened by the designated owner @jeelfefar2141\.\n$/);
});

test('gh failures are reported, and the duplicate check can be skipped explicitly', () => {
  f.branch('feat/nogh', [{ author: who('Jeel') }]);
  f.setScenario({ fail: 'HTTP 401: Bad credentials' });
  const r = prepare('feat/nogh');
  assert.equal(r.code, 1);
  assert.match(r.err, /^ERROR GH_UNAVAILABLE: gh pr list failed: HTTP 401/m);
  const skipped = prepare('feat/nogh', ['--skip-duplicate-check']);
  assert.equal(skipped.code, 0, skipped.err);
  assert.match(skipped.out, /^WARN DUPLICATE_CHECK_SKIPPED/m);
});

test('unknown options such as --verbose and unknown commands are usage errors', () => {
  const v = f.broker(['prepare', '--branch', 'x', '--verbose']);
  assert.equal(v.code, 2);
  assert.match(v.err, /^ERROR UNKNOWN_OPTION: unknown option --verbose/m);
  for (const cmd of ['create', 'merge', 'close', 'approve']) {
    const r = f.broker([cmd, '--pr', '1']);
    assert.equal(r.code, 2);
    assert.match(r.err, /^ERROR USAGE: unknown command/m);
  }
});

test('verify confirms the creator and the requested reviewers', () => {
  f.branch('feat/verify', [{ author: who('Jeel') }]);
  const view = { number: 12, url: 'https://github.com/het-lathiya/Group12/pull/12', author: { login: 'jeelfefar2141' }, headRefName: 'feat/verify', baseRefName: 'main', state: 'OPEN', isDraft: false, reviewRequests: [{ login: 'het-lathiya' }] };
  f.setScenario({ prView: view });
  const ok = f.broker(['verify', '--pr', '12', '--reviewers', 'het-lathiya']);
  assert.equal(ok.code, 0, ok.err);
  assert.equal(ok.out, 'PR #12 https://github.com/het-lathiya/Group12/pull/12 creator=jeelfefar2141\n');
  const missing = f.broker(['verify', '--branch', 'feat/verify', '--reviewers', 'het-lathiya,Manasvi1704']);
  assert.equal(missing.code, 1);
  assert.match(missing.err, /^ERROR MISSING_REVIEWERS: .*Manasvi1704/m);
});

test('verify reports CREATOR_MISMATCH when someone else opened the pull request', () => {
  f.branch('feat/wrong-creator', [{ author: who('Jeel') }]);
  f.setScenario({ prView: { number: 13, url: 'https://github.com/het-lathiya/Group12/pull/13', author: { login: 'Nidhi9864' }, headRefName: 'feat/wrong-creator', baseRefName: 'main', reviewRequests: [] } });
  const r = f.broker(['verify', '--pr', '13']);
  assert.equal(r.code, 1);
  assert.match(r.out, /creator=Nidhi9864$/m);
  assert.match(r.err, /^ERROR CREATOR_MISMATCH: .*not the designated owner jeelfefar2141/m);
});

test('the broker only ever made read-only gh calls and left the working tree clean', () => {
  const calls = f.ghCalls();
  assert.ok(calls.length > 0);
  for (const args of calls) {
    assert.ok(['pr list', 'pr view'].includes(args.slice(0, 2).join(' ')), `unexpected gh call: ${args.join(' ')}`);
  }
  assert.ok(!calls.some((a) => a[0] === 'auth'), 'gh auth was invoked');
  assert.equal(f.status(), '');
});
