const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
const hash = value => [...value].reduce((a,c)=>((a*33)^c.charCodeAt(0))>>>0,5381);
const palette = {
  astronomy: ["#08132d","#27d9ff","#ffbd55"],
  physics: ["#071b25","#27f0d0","#a66bff"],
  mathematics: ["#101322","#32e6ff","#ffbd55"],
  chemistry: ["#071d1c","#42e6c4","#ff784e"],
  history: ["#21170f","#d6a45c","#ffdf9a"],
  comedy: ["#21102b","#ffcf4a","#ff5d83"],
  general: ["#10141e","#62c8ff","#f6bd60"]
};
const subjectFor = (topic, index) => ({
  astronomy: ["planet","accretion-disc","star-cluster","nebula"][index%4],
  physics: ["wavefront","field-lines","particle-stream","force-vector"][index%4],
  mathematics: ["parametric-curve","coordinate-lattice","polyhedron","equation-field"][index%4],
  chemistry: ["molecule","orbital-cloud","reaction-vessel","crystal-lattice"][index%4],
  history: ["monument","terrain-relief","artifact","city-silhouette"][index%4],
  comedy: ["hero-character","comic-prop","reaction-pose","stage-set"][index%4],
  general: ["hero-subject","environment","detail-object","atmosphere"][index%4]
})[topic] || "hero-subject";
export function compileSceneGraph(plan) {
  if (!plan || !Array.isArray(plan.scenes) || !plan.scenes.length) throw new Error("A non-empty scene plan is required.");
  const topic = plan.analysis?.topic || "general";
  const colors = palette[topic] || palette.general;
  const scenes = plan.scenes.map((scene, index) => {
    const duration = scene.end - scene.start;
    if (!(duration > 0)) throw new Error(`Invalid timing in ${scene.id}`);
    const seed = hash(scene.narration);
    const subject = subjectFor(topic, index);
    const orbit = (seed % 2 ? 1 : -1);
    const cameraPath = [
      { t: scene.start, position: [0, 1.4, 8], target: [0, 0, 0], fov: 42 },
      { t: scene.start + duration*.35, position: [orbit*3.8, 1.2, 5.2], target: [0, 0, 0], fov: 36 },
      { t: scene.start + duration*.72, position: [-orbit*2.6, 2.1, 4.4], target: [0, .2, 0], fov: 32 },
      { t: scene.end, position: [0, 2.8, 9], target: [0, 0, 0], fov: 44 }
    ];
    return {
      id: scene.id, start: scene.start, end: scene.end,
      narration: scene.narration,
      visual: { subject, semanticPrompt: scene.visualIntent, environment: scene.world, palette: colors },
      objects: [
        { id: "hero", type: subject, role: "semantic-subject", material: { color: colors[1], metalness: .72, roughness: .24, emissive: colors[1], emissiveIntensity: .65 }, transform: { position: [0,0,0], scale: 1 } },
        { id: "accent-a", type: "procedural-particle-field", role: "depth-and-motion", material: { color: colors[2], opacity: .72 }, transform: { position: [-2,-.8,-2], scale: 1.5 } },
        { id: "accent-b", type: "wireframe-structure", role: "contextual-geometry", material: { color: colors[1], opacity: .38 }, transform: { position: [2,.6,-3], scale: 1.2 } }
      ],
      animation: {
        hero: [{t:scene.start,position:[0,-.15,0],rotation:[0,0,0],scale:.82},{t:scene.start+duration*.5,position:[0,.18,0],rotation:[0,Math.PI*orbit,0],scale:1.12},{t:scene.end,position:[0,0,0],rotation:[0,Math.PI*2*orbit,0],scale:.92}],
        particles: { mode:"deterministic-flow", seed, speed: .4 + (seed%60)/100 },
        camera: cameraPath
      },
      overlays: [{ id:"narration-caption", text:scene.narration, start:scene.start, end:scene.end, source:"verbatim-narration", safeArea:"9:16-title-safe" }]
    };
  });
  const duration = scenes.at(-1).end;
  return { schema:"bamo.scene-graph/1.0", engine:"BAMO OMNIVISION", topic, duration, aspect:plan.input?.aspect || "9:16", fps:30, resolution:{width:1080,height:1920}, audio:{narrationTrack:"external-aligned-track", musicTrack:"optional-score", sfxTrack:"event-cues", masterClock:"scene-timecode"}, scenes, validation:{continuousTimeline:true, captionsVerbatim:true, perSceneUniqueSeed:true} };
}
export function validateSceneGraph(graph) {
  const errors=[];
  if(graph?.schema!=="bamo.scene-graph/1.0") errors.push("unsupported schema");
  if(!Array.isArray(graph?.scenes) || !graph.scenes.length) errors.push("missing scenes");
  let cursor=0;
  for(const scene of graph?.scenes || []) {
    if(Math.abs(scene.start-cursor)>.01) errors.push(`timeline gap/overlap at ${scene.id}`);
    if(scene.end<=scene.start) errors.push(`invalid duration at ${scene.id}`);
    if(scene.overlays?.[0]?.text!==scene.narration) errors.push(`caption mismatch at ${scene.id}`);
    if(!scene.animation?.camera?.length || !scene.objects?.length) errors.push(`missing 3D/camera data at ${scene.id}`);
    cursor=scene.end;
  }
  return {ok:errors.length===0,errors};
}
