#!/usr/bin/env python3
"""Build a HyperFrames-compatible HTML composition (1080x1920, RTL Persian).

Visuals are procedural canvas scenes that are a pure function of time t, so
frame-by-frame seeking renders deterministically with no stock footage or
network assets. Captions are word-level kinetic text timed to real audio.
"""
from __future__ import annotations

import hashlib
import html as H
import json
from pathlib import Path

try:
    from .tts import Beat
except ImportError:  # script mode
    from tts import Beat  # type: ignore

MODES = ("cosmos", "neural", "geometry", "waves", "molecule", "nature", "gears")
ACCENT = {"cosmos": "#9db7ff", "neural": "#62e6ff", "geometry": "#e29bff", "waves": "#6fd0ff",
          "molecule": "#5dffc4", "nature": "#9dff7a", "gears": "#ffc46b"}

JS = r"""
(function(){
const MODE="__MODE__",SEED=__SEED__,D=__DUR__,W=1080,H=1920;
const cv=document.getElementById('bg'),c=cv.getContext('2d');
function mk(s){return function(){s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
const R=mk(SEED),CY=H*0.34,TAU=Math.PI*2;
const BASE={cosmos:255,neural:190,geometry:290,waves:200,molecule:165,nature:120,gears:35}[MODE]||220;
function rot(p,a,b){let x=p[0]*Math.cos(a)+p[2]*Math.sin(a),z=-p[0]*Math.sin(a)+p[2]*Math.cos(a);let y=p[1]*Math.cos(b)-z*Math.sin(b);z=p[1]*Math.sin(b)+z*Math.cos(b);return[x,y,z]}
function pr(p,f){const s=f/(f+p[2]);return[W/2+p[0]*s,CY+p[1]*s,s]}
function glow(x,y,r,h,a){const g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,'hsla('+h+',90%,72%,'+a+')');g.addColorStop(1,'hsla('+h+',90%,50%,0)');c.fillStyle=g;c.beginPath();c.arc(x,y,r,0,TAU);c.fill()}
function sphere(x,y,r,h){const g=c.createRadialGradient(x-r*.35,y-r*.35,r*.1,x,y,r);g.addColorStop(0,'hsl('+h+',85%,78%)');g.addColorStop(.6,'hsl('+h+',70%,42%)');g.addColorStop(1,'hsl('+h+',60%,12%)');c.fillStyle=g;c.beginPath();c.arc(x,y,r,0,TAU);c.fill()}
// ---- precomputed deterministic data
const stars=[];for(let i=0;i<280;i++)stars.push([(R()-.5)*2400,(R()-.5)*2400,R()*1800]);
const nodes=[];for(let i=0;i<120;i++){const u=R()*2-1,a=R()*TAU,r=Math.sqrt(1-u*u);nodes.push([r*Math.cos(a)*330,u*330,r*Math.sin(a)*330])}
const edges=[];for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){const d=Math.hypot(nodes[i][0]-nodes[j][0],nodes[i][1]-nodes[j][1],nodes[i][2]-nodes[j][2]);if(d<150)edges.push([i,j])}
const flies=[];for(let i=0;i<70;i++)flies.push([R()*W,R()*H*0.7,R()*TAU,.3+R()*.9]);
function bg(t,h){const g=c.createLinearGradient(0,0,0,H);g.addColorStop(0,'hsl('+h+',55%,7%)');g.addColorStop(.55,'hsl('+(h+25)+',50%,10%)');g.addColorStop(1,'hsl('+(h+40)+',45%,4%)');c.fillStyle=g;c.fillRect(0,0,W,H)}
const V={
cosmos(t,h){
 for(const s of stars){const z=((s[2]-t*140)%1800+1800)%1800;const p=pr([s[0],s[1],z],700),k=p[2];if(p[0]<0||p[0]>W||p[1]<0||p[1]>H)continue;c.fillStyle='hsla('+(h+20)+',60%,88%,'+Math.min(1,k*.9)+')';c.beginPath();c.arc(p[0],p[1],Math.max(.6,k*2.4),0,TAU);c.fill()}
 glow(W/2,CY,520,h,.28);sphere(W/2,CY,230,h);
 c.save();c.translate(W/2,CY);c.rotate(-.35);c.strokeStyle='hsla('+(h+30)+',70%,75%,.55)';c.lineWidth=14;c.beginPath();c.ellipse(0,0,380,95,0,Math.PI,TAU);c.stroke();c.restore();
 const a=t*.9,mx=W/2+Math.cos(a)*430,my=CY+Math.sin(a)*120;sphere(mx,my,34,h+60);
 c.save();c.translate(W/2,CY);c.rotate(-.35);c.strokeStyle='hsla('+(h+30)+',70%,75%,.55)';c.lineWidth=14;c.beginPath();c.ellipse(0,0,380,95,0,0,Math.PI);c.stroke();c.restore()},
neural(t,h){
 const P=nodes.map(n=>pr(rot(n,t*.35,.35+Math.sin(t*.2)*.15),900));
 c.lineWidth=2;edges.forEach((e,i)=>{const a=P[e[0]],b=P[e[1]],al=.12+.3*Math.min(a[2],b[2]);c.strokeStyle='hsla('+h+',90%,70%,'+al+')';c.beginPath();c.moveTo(a[0],a[1]);c.lineTo(b[0],b[1]);c.stroke();if(i%5===0){const q=(t*.7+i*.137)%1;glow(a[0]+(b[0]-a[0])*q,a[1]+(b[1]-a[1])*q,26,h+40,.9)}});
 P.forEach((p,i)=>{glow(p[0],p[1],34*p[2]+8,h,.55);c.fillStyle='hsl('+(h+20)+',90%,85%)';c.beginPath();c.arc(p[0],p[1],3+4*p[2],0,TAU);c.fill()})},
geometry(t,h){
 const N=200,m=2+(t/D)*9,r=380;c.save();c.translate(W/2,CY);c.rotate(t*.12);c.lineWidth=1.6;
 for(let i=0;i<N;i++){const a=i/N*TAU,b=((i*m)%N)/N*TAU;c.strokeStyle='hsla('+(h+i*.5)+',85%,68%,.34)';c.beginPath();c.moveTo(Math.cos(a)*r,Math.sin(a)*r);c.lineTo(Math.cos(b)*r,Math.sin(b)*r);c.stroke()}
 c.restore();
 for(let i=0;i<420;i++){const u=i/420*TAU*3,p=rot([(2+Math.cos(u*2/3))*Math.cos(u)*70,(2+Math.cos(u*2/3))*Math.sin(u)*70,Math.sin(u*2/3)*140],t*.6,t*.4),q=pr(p,900);glow(q[0],q[1],10*q[2]+3,h+i*.3,.8)}},
waves(t,h){
 const n=34,sp=26,x0=W/2-sp*(n-1)/2,y0=CY-sp*(n-1)/2,s1=[W/2-170*Math.cos(t*.4),CY],s2=[W/2+170*Math.cos(t*.4),CY+80*Math.sin(t*.5)];
 for(let i=0;i<n;i++)for(let j=0;j<n;j++){const x=x0+i*sp,y=y0+j*sp,v=Math.sin(Math.hypot(x-s1[0],y-s1[1])*.045-t*3.2)+Math.sin(Math.hypot(x-s2[0],y-s2[1])*.045-t*3.2),k=(v+2)/4;c.fillStyle='hsla('+(h+k*70)+',90%,'+(40+k*40)+'%,'+(.25+k*.7)+')';c.beginPath();c.arc(x,y,2+k*9,0,TAU);c.fill()}
 glow(s1[0],s1[1],60,h+50,.6);glow(s2[0],s2[1],60,h+50,.6)},
molecule(t,h){
 const c0=[0,0,0],sat=[0,1,2].map(i=>{const a=i*TAU/3+t*.5,b=Math.sin(t*.3+i)*.8;return[Math.cos(a)*250,Math.sin(b)*150,Math.sin(a)*250]}).map(p=>rot(p,t*.25,.25));
 const C=pr(c0,900),S=sat.map(p=>pr(p,900));
 S.forEach(s=>{c.strokeStyle='hsla('+h+',60%,80%,.55)';c.lineWidth=22*s[2];c.beginPath();c.moveTo(C[0],C[1]);c.lineTo(s[0],s[1]);c.stroke()});
 const items=[[C,100,h,0],...S.map((s,i)=>[s,62,h+50+i*40,sat[i][2]])].sort((a,b)=>b[3]-a[3]);
 items.forEach(it=>{glow(it[0][0],it[0][1],it[1]*2.2,it[2],.3);sphere(it[0][0],it[0][1],it[1]*it[0][2],it[2])});
 for(let k=0;k<3;k++){const a=t*(2+k)+k*2,p=pr(rot([Math.cos(a)*(190+k*60),Math.sin(a)*(70+k*30),Math.sin(a*1.3)*120],.4*k,t*.3),900);glow(p[0],p[1],22,h+100,.95)}},
nature(t,h){
 function br(x,y,l,a,d){if(d>9||l<4)return;const sw=Math.sin(t*.9+d*.7)*.05,a2=a+sw,x2=x+Math.cos(a2)*l,y2=y+Math.sin(a2)*l;c.strokeStyle='hsl('+(30+d*10)+',45%,'+(28+d*4)+'%)';c.lineWidth=Math.max(1.2,(9-d)*2.6);c.beginPath();c.moveTo(x,y);c.lineTo(x2,y2);c.stroke();if(d>=7){glow(x2,y2,22,h+d*6,.55)}br(x2,y2,l*.76,a2-.42,d+1);br(x2,y2,l*.76,a2+.38,d+1)}
 br(W/2,CY+420,170,-Math.PI/2,0);
 for(const f of flies){const x=f[0]+Math.sin(t*f[3]+f[2])*70,y=f[1]+Math.cos(t*f[3]*.8+f[2])*50;glow(x,y,16,h+60,.5+.4*Math.sin(t*2+f[2]))}},
gears(t,h){
 function gear(x,y,r,n,a,hh){c.save();c.translate(x,y);c.rotate(a);c.beginPath();for(let i=0;i<n*2;i++){const ang=i/(n*2)*TAU,rr=(i%2?r:r*1.14),w=TAU/(n*4);c.lineTo(Math.cos(ang-w)*rr,Math.sin(ang-w)*rr);c.lineTo(Math.cos(ang+w)*rr,Math.sin(ang+w)*rr)}c.closePath();const g=c.createLinearGradient(-r,-r,r,r);g.addColorStop(0,'hsl('+hh+',65%,62%)');g.addColorStop(1,'hsl('+hh+',60%,24%)');c.fillStyle=g;c.fill();c.globalCompositeOperation='destination-out';c.beginPath();c.arc(0,0,r*.38,0,TAU);c.fill();c.globalCompositeOperation='source-over';c.strokeStyle='hsla('+hh+',70%,85%,.5)';c.lineWidth=4;c.beginPath();c.arc(0,0,r*.38,0,TAU);c.stroke();c.restore()}
 glow(W/2,CY,480,h,.2);const k=t*.5;gear(W/2-150,CY-40,200,18,k,h);gear(W/2+205,CY+120,120,11,-k*18/11+.16,h+15);gear(W/2-60,CY+310,95,9,k*2*0+(-k*18/9)+.3,h+30)}
};
function draw(t){
 const h=BASE+28*Math.sin(t*.25);c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,W,H);bg(t,h);
 const z=1+.06*Math.min(1,t/D);c.save();c.translate(W/2,CY);c.scale(z,z);c.translate(-W/2,-CY);(V[MODE]||V.cosmos)(t,h);c.restore()}
window.__bamoDraw=draw;window.__bamoClock={t:0};draw(0);
})();
"""

HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=1080, height=1920"/>
<title>__TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@500;800;900&display=block" rel="stylesheet"/>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:#05060d;font-family:"Vazirmatn","Noto Naskh Arabic","Noto Sans Arabic",Tahoma,sans-serif;color:#fff;direction:rtl}
#root{position:relative;width:1080px;height:1920px;overflow:hidden}
#bg{position:absolute;inset:0;width:1080px;height:1920px}
.vig{position:absolute;inset:0;z-index:2;pointer-events:none;background:radial-gradient(ellipse at 50% 38%,rgba(0,0,0,0) 38%,rgba(0,0,0,.55) 100%),linear-gradient(180deg,rgba(0,0,0,.35) 0%,rgba(0,0,0,0) 22%,rgba(0,0,0,0) 52%,rgba(0,0,0,.78) 82%,rgba(0,0,0,.92) 100%)}
#pill{position:absolute;top:150px;left:0;right:0;text-align:center;z-index:6;opacity:0}
#pill span{display:inline-block;padding:10px 30px;border-radius:999px;font-weight:800;font-size:30px;color:__ACC__;border:2px solid __ACC__;background:rgba(0,0,0,.35);letter-spacing:.5px}
#ttl{position:absolute;top:230px;left:60px;right:60px;text-align:center;font-weight:900;font-size:62px;line-height:1.35;z-index:6;opacity:0;text-shadow:0 4px 24px rgba(0,0,0,.9)}
.beat{position:absolute;left:70px;right:70px;top:1130px;height:430px;display:flex;align-items:flex-start;justify-content:center;flex-wrap:wrap;align-content:flex-start;text-align:center;font-weight:900;font-size:68px;line-height:1.55;z-index:6;opacity:0;text-shadow:0 4px 22px rgba(0,0,0,.95),0 0 3px #000}
.beat .w{display:inline-block;margin:0 9px;opacity:.28;transform:translateY(14px)}
#bar{position:absolute;left:70px;right:70px;bottom:250px;height:8px;border-radius:8px;background:rgba(255,255,255,.18);z-index:6;overflow:hidden}
#fill{height:100%;width:100%;background:__ACC__;transform-origin:100% 50%;transform:scaleX(0);border-radius:8px}
#brand{position:absolute;left:0;right:0;bottom:170px;text-align:center;font-weight:800;font-size:34px;z-index:6;color:rgba(255,255,255,.92);text-shadow:0 2px 12px #000}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="1080" data-height="1920">
<canvas id="bg" class="clip" width="1080" height="1920" data-start="0" data-duration="__DUR__" data-track-index="0"></canvas>
<div class="vig clip" data-start="0" data-duration="__DUR__" data-track-index="1"></div>
<div id="pill" class="clip" data-start="0" data-duration="__DUR__" data-track-index="2"><span>__CAT__</span></div>
<div id="ttl" class="clip" data-start="0" data-duration="__DUR__" data-track-index="3">__TITLE__</div>
__BEATS__
<div id="bar" class="clip" data-start="0" data-duration="__DUR__" data-track-index="4"><div id="fill"></div></div>
<div id="brand" class="clip" data-start="0" data-duration="__DUR__" data-track-index="5">بامو · @12bamo</div>
<audio id="vo" class="clip" src="assets/audio.mp3" data-start="0" data-duration="__DUR__" data-track-index="40" data-volume="1"></audio>
</div>
<script>__JS__</script>
<script>
window.__timelines=window.__timelines||{};
const tl=gsap.timeline({paused:true});
const clock={t:0};
tl.to(clock,{t:__DUR__,duration:__DUR__,ease:"none",onUpdate:function(){window.__bamoDraw(clock.t)}},0);
tl.fromTo("#pill",{opacity:0,y:-20},{opacity:1,y:0,duration:.5,ease:"power2.out"},0.15);
tl.fromTo("#ttl",{opacity:0,y:24},{opacity:1,y:0,duration:.7,ease:"power3.out"},0.3);
tl.to("#fill",{scaleX:1,duration:__DUR__,ease:"none"},0);
__GSAP__
window.__timelines["main"]=tl;
</script>
</body>
</html>
"""


def _seed(idea_id: str) -> int:
    return int(hashlib.sha256(idea_id.encode()).hexdigest()[:8], 16)


def pick_mode(idea: dict) -> str:
    m = idea.get("visual")
    return m if m in MODES else MODES[_seed(idea.get("id", "x")) % len(MODES)]


def build_html(idea: dict, beats: list[Beat], duration: float) -> str:
    mode = pick_mode(idea)
    acc = ACCENT[mode]
    divs: list[str] = []
    gs: list[str] = []
    for i, b in enumerate(beats):
        words = b.text.split()
        spans = "".join(f'<span class="w" id="b{i}w{j}">{H.escape(w)}</span>' for j, w in enumerate(words))
        slot = max(0.8, b.end - b.start + 0.25)
        divs.append(
            f'<div id="beat{i}" class="beat clip" data-start="{b.start:.2f}" data-duration="{slot:.2f}" '
            f'data-track-index="{10 + i}">{spans}</div>'
        )
        gs.append(f'tl.fromTo("#beat{i}",{{opacity:0}},{{opacity:1,duration:.12}},{b.start:.2f});')
        gs.append(f'tl.to("#beat{i}",{{opacity:0,duration:.18}},{b.end + 0.18:.2f});')
        weights = [len(w) + 1.5 for w in words]
        tot = sum(weights)
        span_t = max(0.4, (b.end - b.start) * 0.94)
        t = b.start
        for j, w in enumerate(weights):
            dur = span_t * w / tot
            gs.append(
                f'tl.to("#b{i}w{j}",{{opacity:1,y:0,color:"{acc}",duration:.16,ease:"power2.out"}},{t:.3f});'
                f'tl.to("#b{i}w{j}",{{color:"#ffffff",duration:.3}},{t + dur + 0.05:.3f});'
            )
            t += dur
    js = JS.replace("__MODE__", mode).replace("__SEED__", str(_seed(idea["id"]))).replace("__DUR__", f"{duration:.2f}")
    out = (HTML.replace("__JS__", js)
           .replace("__BEATS__", "\n".join(divs))
           .replace("__GSAP__", "\n".join(gs))
           .replace("__TITLE__", H.escape(idea["title"]))
           .replace("__CAT__", H.escape(idea["category"]))
           .replace("__ACC__", acc)
           .replace("__DUR__", f"{duration:.2f}"))
    return out


def write_project(idea: dict, beats: list[Beat], duration: float, audio: Path, workdir: Path) -> Path:
    (workdir / "assets").mkdir(parents=True, exist_ok=True)
    target = workdir / "assets" / "audio.mp3"
    if audio.resolve() != target.resolve():
        target.write_bytes(audio.read_bytes())
    (workdir / "index.html").write_text(build_html(idea, beats, duration), encoding="utf-8")
    (workdir / "timeline.json").write_text(
        json.dumps({"idea": idea["id"], "duration": duration, "beats": [b.__dict__ for b in beats]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return workdir / "index.html"
