import test from "node:test";
import assert from "node:assert/strict";
import { planVideo } from "../src/planner.mjs";

test("detects distinct subject domains",()=>{
  assert.equal(planVideo("سیاه‌چاله و کهکشان").analysis.topic,"astronomy");
  assert.equal(planVideo("یک معادله هندسه و تابع").analysis.topic,"mathematics");
  assert.equal(planVideo("واکنش مولکول و اتم").analysis.topic,"chemistry");
  assert.equal(planVideo("داستان طنز روباه").analysis.topic,"comedy");
});
test("creates timed, narration-bound, varied shots",()=>{
  const p=planVideo("نور خم می‌شود. زمان نزدیک سیاه‌چاله کندتر می‌گذرد. زمین در مدار می‌چرخد.",{duration:24});
  assert.equal(p.scenes.length,3);
  assert.equal(p.scenes[0].start,0);
  assert.equal(p.scenes.at(-1).end,24);
  assert.ok(p.scenes.every(s=>s.visualIntent===s.narration));
  assert.equal(new Set(p.scenes.map(s=>s.shot)).size,3);
});
test("rejects empty scripts",()=>assert.throws(()=>planVideo("  "),/non-empty/));
