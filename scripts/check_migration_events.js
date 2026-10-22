const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const js = name => fs.readFileSync(path.join(__dirname, '../assets/js', name), 'utf8');
for (const [pathname, referrer] of [
  ['/event/123/456/old-show', 'https://example.com/private?email=secret'],
  ['/blogs/diary-of-a-rock-n-roll-doctor/posts/123/old-post', 'not a URL'],
  ['/random-page', '']
]) {
  const message = {textContent: 'Default message'};
  const calls = [];
  vm.runInNewContext(js('not-found.js'), {
    window: {location: {pathname}, gtag: (...args) => calls.push(args)},
    document: {referrer, getElementById: () => message}, URL
  });
  assert.equal(calls.length, 1);
  assert.equal(calls[0][1], 'page_not_found');
  assert.equal(calls[0][2].missing_path, pathname);
  assert.ok(!JSON.stringify(calls).includes('secret'));
  if (pathname.startsWith('/event/')) assert.match(message.textContent, /show listing/);
  if (pathname.startsWith('/blogs/')) assert.match(message.textContent, /older article/);
}
let handler;
const calls = [];
vm.runInNewContext(js('outbound-tracking.js'), {
  document: {addEventListener: (_, callback) => { handler = callback; }}, URL, Set,
  window: {location: {href: 'https://onemanelectricalband.com/merch/', pathname: '/merch/'}, gtag: (...args) => calls.push(args)}
});
for (const href of ['https://curryink.com/products/omeb?email=secret', 'https://open.spotify.com/track/123?si=secret', 'https://example.com/', 'javascript:void(0)']) {
  handler({target: {closest: () => ({href})}});
}
handler({target: {}});
assert.equal(calls.length, 2);
assert.equal(calls[0][1], 'merch_outbound_click');
assert.equal(calls[1][1], 'music_outbound_click');
assert.ok(!JSON.stringify(calls).includes('secret'));
console.log('Migration events: error context, one event per click, irrelevant links and query/referrer privacy checks passed.');
