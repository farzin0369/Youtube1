#!/usr/bin/env python3
"""Offline Blender renderer variety proof; fixtures are NOT AI-director output."""
from __future__ import annotations
import json, subprocess
from pathlib import Path
from app.bamo_motion_engine import render_project

OUT = Path("output/bamo-scene-variety")
OUT.mkdir(parents=True, exist_ok=True)
PALETTE = {"background":"#07111f","key":"#20c9ff","accent":"#ffbd59"}
def obj(id, kind, pos, scale, material, action="none", amount=0.0):
    return {"id":id,"kind":kind,"role":id.replace("_"," "),"position":pos,"scale":scale,
            "rotation":[0,0,0],"material":material,"action":action,"action_amount":amount}
def graph(thesis, camera, objects, relations):
    return {"visual_thesis":thesis,"camera":{"move":camera,"angle":"eye","focus":"main subject"},
            "palette":PALETTE,"objects":objects,"relationships":relations}

# Three deliberately different fixture compositions exercise the same production Blender scene-graph renderer.
wave = graph("Two wave sources create a shared interference field","orbit",[
    obj("source_left","sphere",[-2.3,0,1],[.34,.34,.34],"key","pulse",1),
    obj("source_right","sphere",[2.3,0,1],[.34,.34,.34],"accent","pulse",1),
    obj("wave_front_a","torus",[-2.3,0,1],[1.0,1.0,.035],"key","rise",.2),
    obj("wave_front_b","torus",[2.3,0,1],[1.0,1.0,.035],"accent","rise",.2),
    obj("interference_axis","line",[0,-3,.5],[0,6,0],"neutral"),
], [{"from":"source_left","to":"source_right","kind":"connect"}])
chem = graph("A bonded molecular structure with a moving central atom","push_in",[
    obj("atom_a","sphere",[-1.7,0,1.2],[.48,.48,.48],"accent","pulse",1),
    obj("atom_b","sphere",[0,1.2,1.2],[.34,.34,.34],"key","pulse",1),
    obj("atom_c","sphere",[1.7,0,1.2],[.48,.48,.48],"accent","pulse",1),
    obj("atom_d","sphere",[0,-1.2,1.2],[.34,.34,.34],"key","pulse",1),
    obj("bond_ab","line",[-1.7,0,1.2],[1.7,1.2,0],"neutral"),
    obj("bond_bc","line",[0,1.2,1.2],[1.7,-1.2,0],"neutral"),
    obj("bond_cd","line",[1.7,0,1.2],[-1.7,-1.2,0],"neutral"),
    obj("bond_da","line",[0,-1.2,1.2],[-1.7,1.2,0],"neutral"),
], [{"from":"atom_a","to":"atom_b","kind":"connect"},{"from":"atom_b","to":"atom_c","kind":"connect"}])
neural = graph("A connected neural network with pulsing signal nodes","tracking",[
    obj("neuron_1","icosphere",[-2.4,0,1],[.36,.36,.36],"key","pulse",1),
    obj("neuron_2","icosphere",[-.8,1.1,1.8],[.3,.3,.3],"accent","pulse",1),
    obj("neuron_3","icosphere",[.8,-.8,1.3],[.36,.36,.36],"key","pulse",1),
    obj("neuron_4","icosphere",[2.4,.6,1.7],[.3,.3,.3],"accent","pulse",1),
    obj("synapse_1","line",[-2.4,0,1],[1.6,1.1,.8],"neutral"),
    obj("synapse_2","line",[-.8,1.1,1.8],[1.6,-1.9,-.5],"neutral"),
    obj("synapse_3","line",[.8,-.8,1.3],[1.6,1.4,.4],"neutral"),
], [{"from":"neuron_1","to":"neuron_2","kind":"connect"},{"from":"neuron_2","to":"neuron_3","kind":"connect"},{"from":"neuron_3","to":"neuron_4","kind":"connect"}])

scenes = [
 {"duration":1.5,"text":"تداخل موج‌ها","narration":"دو موج با یکدیگر تداخل می‌کنند","visual_prompt":"wave interference","scene_graph":wave},
 {"duration":1.5,"text":"پیوند مولکولی","narration":"اتم‌ها با پیوند شیمیایی به هم متصل می‌شوند","visual_prompt":"molecular bond","scene_graph":chem},
 {"duration":1.5,"text":"شبکه عصبی","narration":"نورون‌ها از راه اتصال‌های عصبی پیام می‌فرستند","visual_prompt":"neural network","scene_graph":neural},
]
video = render_project({"format":"short","fps":24,"scenes":scenes}, OUT/"bamo-three-domain-renderer-proof.mp4")
probe = subprocess.run(["ffprobe","-v","error","-count_frames","-select_streams","v:0","-show_entries","stream=codec_name,width,height,r_frame_rate,nb_read_frames","-of","json",str(video)],check=True,capture_output=True,text=True,timeout=60)
stream=json.loads(probe.stdout)["streams"][0]
evidence={"classification":"offline_fixture_renderer_test_not_ai_director_or_production_approval",
 "renderer":"Blender Cycles CPU","video":str(video),"bytes":video.stat().st_size,
 "codec":stream.get("codec_name"),"width":stream.get("width"),"height":stream.get("height"),
 "fps":stream.get("r_frame_rate"),"frames":int(stream.get("nb_read_frames","0")),
 "fixture_domains":["wave_interference","molecular_bond","neural_network"],
 "camera_moves":["orbit","push_in","tracking"],"scene_graph_object_counts":[5,8,7]}
(OUT/"render-evidence.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(evidence,ensure_ascii=False,indent=2),flush=True)
if evidence["width"]!=720 or evidence["height"]!=1280 or evidence["fps"]!="24/1" or evidence["frames"]!=108 or evidence["bytes"]<30000:
 raise SystemExit("Renderer variety proof failed media validation")
