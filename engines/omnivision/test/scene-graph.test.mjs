import test from "node:test";
import assert from "node:assert/strict";
import { planVideo } from "../src/planner.mjs";
import { compileSceneGraph, validateSceneGraph } from "../src/scene-graph.mjs";

test("compiles narration into timed 3D objects, animation and camera tracks",()=>{
  const graph=compileSceneGraph(planVideo("سیاه‌چاله نور را خم می‌کند. زمان در نزدیکی آن کند می‌شود.",{duration:20}));
  assert.equal(graph.schema,"bamo.scene-graph/1.0");
  assert.equal(graph.scenes.length,2);
  assert.ok(graph.scenes.every(s=>s.objects.length>=3 && s.animation.camera.length>=3));
  assert.deepEqual(validateSceneGraph(graph),{ok:true,errors:[]});
});
test("rejects broken timeline and caption mismatch",()=>{
  const graph=compileSceneGraph(planVideo("یک معادله هندسی را بررسی می‌کنیم.",{duration:10}));
  graph.scenes[0].overlays[0].text="متن اشتباه";
  assert.equal(validateSceneGraph(graph).ok,false);
});
