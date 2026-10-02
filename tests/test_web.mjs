// Extracts the LOGIC-START/END block from each web tool and runs assertions in node.
import fs from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "web");
function load(file, exports) {
  const html = fs.readFileSync(path.join(dir, file), "utf8");
  const m = /\/\/ LOGIC-START([\s\S]*?)\/\/ LOGIC-END/.exec(html);
  assert.ok(m, file + ": no logic block");
  const ctx = vm.createContext({});
  vm.runInContext(m[1] + `;globalThis.__x={${exports.join(",")}}`, ctx);
  return ctx.__x;
}
let n = 0;
const t = (name, fn) => { fn(); n++; console.log("ok  ", name); };

t("jsontool", () => {
  const j = load("jsontool.html", ["parseJSON", "sortKeys", "queryPath", "toCSV", "flatten"]);
  assert.equal(j.parseJSON('{"a":1}').ok, true);
  const bad = j.parseJSON('{\n  "a": 1,\n  "b": \n}');
  assert.equal(bad.ok, false);
  assert.ok(bad.line >= 3, "line reported: " + bad.line);
  assert.deepEqual(Object.keys(j.sortKeys({ b: 1, a: { d: 1, c: 2 } })), ["a", "b"]);
  const v = { users: [{ name: "a", id: 1 }, { name: "b", id: 2 }] };
  assert.deepEqual(Array.from(j.queryPath(v, "users[*].id")), [1, 2]);
  assert.deepEqual(Array.from(j.queryPath(v, "$.users[1].name")), ["b"]);
  assert.deepEqual(Array.from(j.queryPath(v, "users[5]")), []);
  assert.equal(j.toCSV([{ a: 1, b: { c: 'x,"y"' } }, { a: 2, d: null }]), 'a,b.c,d\n1,"x,""y""",\n2,,');
});

t("textdiff", () => {
  const d = load("textdiff.html", ["diffLines", "wordDiff", "stats"]);
  const r = d.diffLines("a\nb\nc", "a\nB\nc\nd", false, false);
  assert.deepEqual(JSON.parse(JSON.stringify(d.stats(r))), { added: 2, removed: 1, same: 2 });
  assert.equal(d.stats(d.diffLines("x  y", "X Y", true, true)).added, 0);
  const w = d.wordDiff("the quick fox", "the slow fox");
  assert.equal(w.filter(x => x.t === "del").map(x => x.a).join(""), "quick");
  assert.equal(d.stats(d.diffLines("", "", false, false)).added, 0);
});

t("regex", () => {
  const r = load("regex.html", ["runRegex", "segments", "replaceAll"]);
  const res = r.runRegex("(\\w+)@(\\w+)\\.com", "g", "a@b.com x c@d.com");
  assert.equal(res.matches.length, 2);
  assert.deepEqual(Array.from(res.matches[1].groups), ["c", "d"]);
  assert.ok(r.runRegex("(", "g", "x").error);
  assert.equal(r.runRegex("x*", "g", "aaa").matches.length, 4); // empty matches don't loop forever
  const segs = r.segments("ab12cd", r.runRegex("\\d+", "g", "ab12cd").matches);
  assert.deepEqual(Array.from(segs, s => s.hit), [false, true, false]);
  assert.equal(r.replaceAll("(a)(b)", "g", "abab", "$2$1").out, "baba");
});

t("invoice", () => {
  const i = load("invoice.html", ["computeTotals", "money"]);
  const tot = i.computeTotals([{ qty: 3, price: 19.99 }, { qty: 1, price: 0.1 }], 10, 8.5);
  assert.equal(tot.subtotal, 60.07);
  assert.equal(tot.discount, 6.01);
  assert.equal(tot.tax, 4.6); // (60.07-6.01) * 8.5% = 4.5951
  assert.equal(tot.total, 58.66);
  assert.equal(i.computeTotals([], 0, 0).total, 0);
  assert.equal(i.money(1234.5, "$"), "$1,234.50");
});

t("subs", () => {
  const s = load("subs.html", ["monthlyCost", "nextRenewal", "summarize", "toCSV", "ymd"]);
  assert.equal(s.ymd(s.nextRenewal("2025-03-10", 12, new Date(2026, 9, 2))), "2027-03-10"); // regression: no UTC date shift
  assert.equal(s.monthlyCost(120, 12), 10);
  assert.equal(Math.round(s.monthlyCost(10, 0.25) * 100) / 100, 43.33);
  const today = new Date(2026, 9, 2);
  assert.equal(s.nextRenewal("2026-01-31", 1, today).toISOString().slice(0, 10) > "2026-10-01", true);
  const nr = s.nextRenewal("2025-10-05", 12, today);
  assert.equal(nr.getFullYear() + "-" + (nr.getMonth() + 1) + "-" + nr.getDate(), "2026-10-5");
  const sum = s.summarize([{ amt: "12", per: "1", next: "2026-10-04" }, { amt: "120", per: "12", next: "2026-12-01" }], today);
  assert.deepEqual(JSON.parse(JSON.stringify(sum)), { monthly: 22, yearly: 264, count: 2, soon: 1 });
  assert.ok(s.toCSV([{ name: 'A,"B"', amt: "5", per: "1", next: "2026-01-01" }]).includes('"A,""B""",5,monthly'));
});

t("imgtool", () => {
  const m = load("imgtool.html", ["fitSize", "outName", "fmtBytes"]);
  assert.deepEqual(JSON.parse(JSON.stringify(m.fitSize(4000, 3000, 1600))), { w: 1600, h: 1200 });
  assert.deepEqual(JSON.parse(JSON.stringify(m.fitSize(800, 600, 1600))), { w: 800, h: 600 });
  assert.equal(m.outName("my.photo.PNG", "image/webp"), "my.photo-small.webp");
  assert.equal(m.fmtBytes(1536), "1.5 KB");
});

t("focus", () => {
  const f = load("focus.html", ["fmtTime", "nextPhase", "phaseSeconds", "todayStats"]);
  assert.equal(f.fmtTime(1500), "25:00");
  assert.equal(f.fmtTime(59.2), "01:00");
  assert.equal(f.fmtTime(-3), "00:00");
  assert.equal(f.nextPhase("focus", 3), "break");
  assert.equal(f.nextPhase("focus", 4), "long");
  assert.equal(f.nextPhase("focus", 0), "break");
  assert.equal(f.nextPhase("long", 4), "focus");
  assert.equal(f.phaseSeconds("break", { fm: 25, bm: 5, lm: 15 }), 300);
  const now = Date.now();
  assert.equal(f.todayStats([{ at: now, min: 25 }, { at: now - 3 * 864e5, min: 25 }], now).sessions, 1);
});

t("textstats", () => {
  const s = load("textstats.html", ["analyze", "countSyllables", "words"]);
  const a = s.analyze("The cat sat on the mat. It was a sunny day!\n\nNew paragraph here.");
  assert.equal(a.words, 14);
  assert.equal(a.sentences, 3);
  assert.equal(a.paragraphs, 2);
  assert.ok(a.flesch > 80, "simple text is easy: " + a.flesch);
  assert.equal(s.countSyllables("banana"), 3);
  assert.equal(s.countSyllables("the"), 1);
  assert.equal(s.analyze("").words, 0);
  assert.equal(s.analyze("word word word other").top[0][0], "word");
});

console.log(`\n${n} web logic suites passed`);
