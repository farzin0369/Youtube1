import test from "node:test";
import assert from "node:assert/strict";
import { compileAudioVisualPipeline } from "../src/pipeline.mjs";

const tts = {
  ok: true, path: "/tmp/voice.mp3", provider: "edge-tts", duration_seconds: 4,
  scene_timings: [{start_seconds:0,end_seconds:1.8},{start_seconds:1.8,end_seconds:4}],
  word_events: [
    {text:"نور",start:.1,end:.4},{text:"می‌تابد",start:.45,end:.9},
    {text:"زمین",start:2,end:2.4},{text:"روشن",start:2.45,end:2.8}
  ]
};
test("joins Persian TTS scene and measured word timings into a validated AV pipeline",()=>{
  const result=compileAudioVisualPipeline("نور می‌تابد. زمین روشن",tts);
  assert.equal(result.validation.ok,true);
  assert.equal(result.graph.scenes[0].start,0);
  assert.equal(result.graph.scenes[1].start,1.8);
  assert.equal(result.timeline.wordCues.length,4);
  assert.equal(result.audio.duration,4);
});
test("refuses guessed or missing TTS alignment",()=>{
  assert.throws(()=>compileAudioVisualPipeline("متن", {...tts,word_events:[]}),/word events/);
  assert.throws(()=>compileAudioVisualPipeline("متن", {...tts,scene_timings:[{start_seconds:0,end_seconds:2},{start_seconds:2,end_seconds:4}]}),/scene count/);
});

test("preserves measured TTS pauses as explicit gaps without shifting word timing",()=> {
  const paused = {
    ...tts,
    scene_timings: [{start_seconds:0,end_seconds:1.5},{start_seconds:1.8,end_seconds:4}],
    word_events: [{text:"آغاز",start:.1,end:.4},{text:"ادامه",start:2,end:2.3}]
  };
  const result = compileAudioVisualPipeline("نور می‌تابد. زمین روشن",paused);
  assert.equal(result.validation.ok,true);
  assert.deepEqual(result.graph.pauses,[{start:1.5,end:1.8}]);
  assert.equal(result.timeline.wordCues[1].sceneId,"scene-02");
});
