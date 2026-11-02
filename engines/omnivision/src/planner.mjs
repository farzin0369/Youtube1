const TOPICS = [
  { id:"astronomy", terms:["black hole","سیاه‌چاله","سیاره","ستاره","کهکشان","فضا","خورشید","زمین"], world:"cosmic", assets:["starfield","planet","accretion-disk","nebula"], palette:["deep-space","stellar-gold","plasma-blue"] },
  { id:"physics", terms:["gravity","گرانش","نور","زمان","انرژی","فیزیک","موج","الکترون"], world:"physics-lab", assets:["field-lines","particle-trails","wavefront","force-vectors"], palette:["midnight","electric-cyan","ion-violet"] },
  { id:"mathematics", terms:["ریاضی","هندسه","معادله","عدد","تابع","مثلث","دایره","فرمول"], world:"abstract-math", assets:["parametric-curves","equation-glyphs","geometric-solids","coordinate-grid"], palette:["graphite","neon-cyan","amber"] },
  { id:"chemistry", terms:["شیمی","مولکول","اتم","واکنش","عنصر","پیوند"], world:"molecular-lab", assets:["atom-orbitals","molecule-bonds","reaction-particles","glassware"], palette:["lab-dark","molecular-teal","reaction-orange"] },
  { id:"history", terms:["تاریخ","امپراتوری","باستان","جنگ","پادشاه","تمدن"], world:"historical-reconstruction", assets:["architecture","terrain","period-props","crowd-silhouettes"], palette:["earth","bronze","torchlight"] },
  { id:"comedy", terms:["طنز","شوخی","روباه","خنده","بامزه","کمدی"], world:"character-stage", assets:["expressive-character","comic-props","reaction-beats","stylized-set"], palette:["bold-primary","warm-key","graphic-accent"] }
];
const words = s => (s.match(/[\p{L}\p{N}]+/gu) || []);
function sentences(text) {
  return text.split(/(?<=[.!?؟؛])\s+|\n+/u).map(s=>s.trim()).filter(Boolean);
}
function chooseTopic(text) {
  const lower=text.toLocaleLowerCase("fa");
  const scores=TOPICS.map(t=>({...t,score:t.terms.reduce((n,w)=>n+(lower.includes(w.toLocaleLowerCase("fa"))?1:0),0)}));
  scores.sort((a,b)=>b.score-a.score);
  return scores[0].score ? scores[0] : {id:"general",world:"cinematic-documentary",assets:["environment","subject","atmosphere"],palette:["film-neutral","motivated-light","accent"]};
}
function shotFor(index,total,topic) {
  const sequence=["establishing-aerial","macro-reveal","tracking-action","hero-orbit","detail-cutaway","wide-resolution"];
  const shot=sequence[index%sequence.length];
  const camera={
    "establishing-aerial":"slow crane-in with layered atmospheric parallax",
    "macro-reveal":"macro push-through with shallow depth of field",
    "tracking-action":"lateral tracking shot with subject-locked focus",
    "hero-orbit":"controlled 120-degree orbit with foreground parallax",
    "detail-cutaway":"rack-focus close-up with motivated camera drift",
    "wide-resolution":"pull-back reveal into a composed wide frame"
  }[shot];
  return {shot,camera,transition:index===0?"cold-open":index===total-1?"match-cut-to-outro":"motion-match-cut"};
}
export function planVideo(input,{duration=30,aspect="9:16"}={}) {
  const text=String(input||"").trim();
  if(!text) throw new Error("A non-empty narration/script is required.");
  const topic=chooseTopic(text), lines=sentences(text);
  const chunks=lines.length>1?lines:[text];
  const scenes=chunks.map((line,i)=>{
    const beat=shotFor(i,chunks.length,topic);
    return {
      id:"scene-"+String(i+1).padStart(2,"0"),
      narration:line,
      visualIntent:line,
      world:topic.world,
      subject:topic.assets[i%topic.assets.length],
      supportingElements:topic.assets.filter((_,j)=>j!==i%topic.assets.length).slice(0,2),
      camera:beat.camera,
      shot:beat.shot,
      transition:beat.transition,
      lighting:{key:"motivated-area-light",fill:"low-intensity-bounce",atmosphere:"depth-layered"},
      motion:{subject:"action-derived",environment:"slow-independent-drift",camera:"continuous-authored-move"},
      textOverlay:{source:"exact-narration",safeArea:"platform-safe",maxLines:2}
    };
  });
  const weights=chunks.map(s=>Math.max(1,words(s).length));
  const sum=weights.reduce((a,b)=>a+b,0);
  let cursor=0;
  const timed=scenes.map((s,i)=>{
    const start=cursor, end=i===scenes.length-1?duration:cursor+duration*weights[i]/sum; cursor=end;
    return {...s,start:Number(start.toFixed(3)),end:Number(end.toFixed(3))};
  });
  return {
    engine:"BAMO OMNIVISION",engineVersion:"0.1.0",status:"plan-only",
    input:{text,duration,aspect},analysis:{topic:topic.id,world:topic.world,confidence:"heuristic-fallback",wordCount:words(text).length},
    artDirection:{palette:topic.palette,style:"cinematic-3d",visualRule:"Every shot must depict the meaning of its own narration; never reuse a generic background as a substitute."},
    audio:{narration:"source-script",music:"adaptive-score-placeholder",sfx:"event-cued-placeholder",sync:"scene-timecode"},
    scenes:timed,
    qualityGates:["scene-narration-semantic-review","shot-silhouette-diversity","text-safe-area","audio-duration-and-sync","black-frame-detection","render-resolution-and-frame-rate"]
  };
}
