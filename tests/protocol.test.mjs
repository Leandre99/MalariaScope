// node --test tests/ — WHO counting rule (public/protocol.js)
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const P = require("../public/protocol.js");

function sessionWith(fields) {
  let s = P.newSession("T-1", false);
  for (const [wbc, parasites] of fields) {
    s = P.addField(s, { wbcCount: wbc, parasiteCount: parasites });
  }
  return s;
}

test("empty session asks for the first field", () => {
  const g = P.guidance(P.newSession("T-1"));
  assert.equal(g.canFinish, false);
  assert.equal(g.target, 200);
});

test("addField accumulates totals without mutating the old session", () => {
  const a = sessionWith([[10, 5]]);
  const b = P.addField(a, { wbcCount: 12, parasiteCount: 3 });
  assert.deepEqual(a.totals, { wbc: 10, parasites: 5 });
  assert.deepEqual(b.totals, { wbc: 22, parasites: 8 });
  assert.equal(b.fields.length, 2);
});

test("under 200 WBC: keep capturing, shows remaining", () => {
  const g = P.guidance(sessionWith([[128, 400]]));
  assert.equal(g.canFinish, false);
  assert.equal(g.remainingWbc, 72);
  assert.match(g.message, /72 WBC to go/);
});

test(">= 200 WBC with >= 100 parasites: enough", () => {
  const g = P.guidance(sessionWith([[120, 60], [85, 45]]));
  assert.equal(g.canFinish, true);
  assert.equal(g.target, 200);
});

test(">= 200 WBC with < 100 parasites: extend target to 500", () => {
  const g = P.guidance(sessionWith([[210, 40]]));
  assert.equal(g.canFinish, false);
  assert.equal(g.target, 500);
  assert.equal(g.extended, true);
  assert.equal(g.remainingWbc, 290);
});

test(">= 500 WBC: enough whatever the parasite count", () => {
  const g = P.guidance(sessionWith([[300, 0], [210, 2]]));
  assert.equal(g.canFinish, true);
  assert.equal(g.target, 500);
});

test("density = parasites x 8000 / WBC, null without WBC", () => {
  assert.equal(P.density(sessionWith([[200, 150]])), 6000);
  assert.equal(P.density(sessionWith([[0, 3]])), null);
});
