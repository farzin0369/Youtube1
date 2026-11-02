const clean=s=>String(s||"").replace(/\s+/gu," ").trim();
export function compileTimeline(graph,wordEvents,audioDuration,{maxCaptionWords=5,maxCaptionSeconds=2.8}={}){
 if(!graph?.scenes?.length)throw new Error("Scene graph is required");
 if(!Number.isFinite(audioDuration)||audioDuration<=0)throw new Error("A positive audio duration is required");
 const scenes=graph.scenes;
 if(Math.abs(scenes.at(-1).end-audioDuration)>Math.max(.35,audioDuration*.025))throw new Error("Audio duration and authored scene timeline differ; retiming is required");
 const words=(wordEvents||[]).map((e,i)=>({text:clean(e.text),start:Number(e.start),end:Number(e.end),index:i})).filter(e=>e.text);
 let previous=0;
 for(const w of words){if(!Number.isFinite(w.start)||!Number.isFinite(w.end)||w.start<0||w.end<=w.start||w.start<previous-.015)throw new Error("Word timestamps are invalid or non-monotonic");if(w.end>audioDuration+.08)throw new Error("A word event exceeds the audio duration");previous=w.start;}
 const sceneFor=t=>scenes.find(s=>t>=s.start-.015&&t<s.end-.015)||scenes.at(-1);
 const captions=[];let group=[];
 const flush=()=>{if(!group.length)return;const first=group[0],last=group.at(-1);captions.push({start:first.start,end:last.end,text:group.map(w=>w.text).join(" "),sceneId:first.sceneId,wordIndexes:group.map(w=>w.index)});group=[];};
 for(const w of words){const scene=sceneFor((w.start+w.end)/2),current={...w,sceneId:scene.id};if(group.length&&(group.length>=maxCaptionWords||current.end-group[0].start>maxCaptionSeconds||group[0].sceneId!==current.sceneId))flush();group.push(current);}flush();
 const cues=words.map(w=>{const scene=sceneFor((w.start+w.end)/2);return {time:Number(w.start.toFixed(3)),sceneId:scene.id,word:w.text,visualCue:{type:"word-emphasis",token:w.text.replace(/[،؛.!؟,:]+$/u,""),weight:1},audioCue:{type:"voice-word",start:w.start,end:w.end}};});
 const errors=[];if(!words.length)errors.push("no word-level alignment events");if(captions.some(c=>c.end<=c.start))errors.push("invalid caption duration");if(captions.some(c=>!scenes.some(s=>s.id===c.sceneId)))errors.push("caption references unknown scene");
 return {schema:"bamo.av-timeline/1.0",duration:audioDuration,source:"measured-word-boundaries",captions,wordCues:cues,sceneAudio:scenes.map(s=>({sceneId:s.id,start:s.start,end:s.end,voiceStart:Math.max(0,s.start),voiceEnd:Math.min(audioDuration,s.end)})),validation:{ok:errors.length===0,errors,wordCount:words.length,captionCount:captions.length}};
}
export function validateTimeline(t){const errors=[];if(t?.schema!=="bamo.av-timeline/1.0")errors.push("unsupported timeline schema");if(!t?.validation?.wordCount)errors.push("missing measured word alignment");let last=-1;for(const c of t?.captions||[]){if(c.start<last-.015||c.end<=c.start)errors.push("caption timing overlap or invalid duration");last=c.end;}return {ok:errors.length===0,errors};}
