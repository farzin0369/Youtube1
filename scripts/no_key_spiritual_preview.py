#!/usr/bin/env python3
"""No-key Persian spiritual preview. Does not publish."""
import asyncio, json, random, subprocess, re
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageFont
import edge_tts

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"/"no_key_preview"; W,H=720,1280
FONTS=["/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
STORIES=[
{"id":"closed_door","title":"درِ بسته، پایان راه نیست","hook":"اگر دری بسته شد، شاید هنوز قصه تمام نشده باشد.","scenes":[("گاهی تمام تلاشمان را می‌کنیم و باز هم راهی باز نمی‌شود.","quiet mountain sunrise"),("مردی خسته، هر روز مقابل دری می‌ایستاد که باز نمی‌شد.","old wooden door nature"),("یک روز از انتظار دست کشید و صدای کمک‌خواهی همسایه‌اش را شنید.","person helping another person"),("فهمید بعضی درها بسته می‌مانند تا ما راهِ مهربانی را ببینیم.","sunlight forest path")],"ending":"از خدا فقط درِ باز نخواه؛ چشمِ دیدنِ راه‌های دیگر را هم بخواه."},
{"id":"small_seed","title":"معجزه از یک دانه شروع می‌شود","hook":"شاید چیزی که امروز کوچک می‌بینی، فردا سایه‌بانت شود.","scenes":[("دانه‌ای کوچک زیر خاک، هیچ نشانی از شکوفه نداشت.","small seed soil plant"),("باران می‌آمد و آفتاب می‌تابید، اما رشدش دیده نمی‌شد.","rain drops young plant"),("روزها گذشت؛ ریشه‌ها در تاریکی، آرام و بی‌صدا قوی شدند.","green seedling sunlight"),("وقتی جوانه سر زد، معلوم شد سکوت همیشه نشانهٔ توقف نیست.","young tree golden sunrise")],"ending":"به رشدِ پنهانِ خودت ایمان داشته باش؛ قدم کوچک امروز را بردار."},
{"id":"last_coin","title":"آخرین سکه","hook":"گاهی بخشیدنِ کم، قلب را از ثروت پُر می‌کند.","scenes":[("زن فقط یک سکه داشت و خودش هم روز سختی را می‌گذراند.","hands holding single coin"),("در راه، کسی را دید که از شدت درماندگی سر به زیر انداخته بود.","person sitting street thoughtful"),("سکه را بخشید؛ نه برای دیده شدن، فقط برای کم کردنِ رنجی.","hands offering help closeup"),("آن روز پول بیشتری پیدا نکرد، اما امیدی ساخت که قیمت نداشت.","warm sunlight city street")],"ending":"ارزش تو فقط در آنچه نگه می‌داری نیست؛ در خیری است که جاری می‌کنی."},
{"id":"silent_prayer","title":"دعایی که بی‌صدا بود","hook":"اگر کلماتت تمام شده، شاید هنوز می‌توانی آرام بمانی.","scenes":[("مردی روبه‌روی پنجره نشست و دیگر نمی‌دانست چه بگوید.","person by window morning light"),("نگرانی‌ها در ذهنش می‌چرخیدند و هیچ پاسخی پیدا نمی‌شد.","rainy window soft light"),("دست از جنگیدن با هر فکر برداشت و چند نفس آرام کشید.","hands resting peaceful nature"),("مشکل یک‌شبه حل نشد، اما توانِ روبه‌رو شدن با آن برگشت.","sunrise calm lake")],"ending":"گاهی نخستین پاسخ، آرامشی است که به تو توانِ قدم بعدی می‌دهد."},
{"id":"honest_builder","title":"پولی که دیر رسید","hook":"آیا حاضری برای سودِ بیشتر، آرامشت را بفروشی؟","scenes":[("بنّایی می‌توانست مصالح ارزان و بی‌کیفیت را پنهانی جایگزین کند.","construction worker hands tools"),("هیچ‌کس متوجه نمی‌شد؛ پول بیشتری هم همان روز به دست می‌آورد.","building materials closeup"),("اما تصویر خانواده‌ای که در آن خانه زندگی می‌کردند، رهایش نکرد.","family home sunlight"),("کار را درست انجام داد؛ درآمدش کمتر بود، وجدانش سبک‌تر.","finished modest house morning")],"ending":"رزقِ خوب فقط پولِ واردشده نیست؛ خیالی است که شب آسوده می‌خوابد."},
{"id":"old_tree","title":"درختی که هنوز سایه می‌داد","hook":"فکر می‌کنی دیگر فایده‌ای نداری؟ این قصه را بشنو.","scenes":[("درخت پیر، دیگر میوهٔ زیادی نمی‌داد و شاخه‌هایش خمیده بود.","old tree field"),("مردم می‌گفتند باید جایش را به درختی جوان بدهند.","old tree meadow sunlight"),("در روز گرم، مسافری زیر سایه‌اش نشست و نفسی تازه کرد.","traveler resting under tree"),("درخت فهمید ارزشش فقط با میوه سنجیده نمی‌شود.","large tree golden hour")],"ending":"تا وقتی می‌توانی پناه، تجربه یا مهربانی بدهی، حضورت معنا دارد."},
{"id":"patient_craftsman","title":"استادکار و ترک کوچک","hook":"یک اشتباه کوچک را پنهان می‌کنی یا درستش می‌کنی؟","scenes":[("استادکار روی ظرفی زیبا ترک باریکی دید؛ مشتری هنوز خبر نداشت.","artisan pottery hands"),("می‌توانست آن را رنگ کند تا ترک از چشم‌ها پنهان بماند.","pottery workshop clay"),("اما ظرف را کنار گذاشت و کار را از نو آغاز کرد.","hands shaping clay pottery"),("اعتماد مشتری، سال‌ها بعد از فروش همان ظرف هم باقی ماند.","finished handmade ceramic bowl")],"ending":"اعتبار آرام‌آرام ساخته می‌شود و با یک پنهان‌کاری می‌تواند فرو بریزد."},
{"id":"lantern","title":"چراغِ کوچک","hook":"برای روشن کردن راه، لازم نیست تمام دنیا را روشن کنی.","scenes":[("مسافر در تاریکی نگران بود که مسیرش تا خانه خیلی طولانی است.","lantern dark path"),("چراغ کوچک او فقط چند قدم جلوتر را روشن می‌کرد.","warm lantern forest path"),("با هر قدم، چند قدم بعدی آشکار می‌شد و ترسش کمتر.","path through forest sunrise"),("وقتی به خانه رسید، فهمید نورِ کافی همان نوری بود که داشت.","warm light cottage evening")],"ending":"قدم بعدی را با دانسته‌های امروز بردار؛ لازم نیست همهٔ فردا را ببینی."}
]
def font(size):
 for p in FONTS:
  if Path(p).exists():
   try:return ImageFont.truetype(p,size)
   except OSError:pass
 return ImageFont.load_default()
def brand_font(size):
 p="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
 try:return ImageFont.truetype(p,size)
 except OSError:return ImageFont.load_default()
def relevant_image(title, query):
 stop={"the","and","for","with","from","under","over","into","small","person","closeup","close","light","warm"}
 words=lambda value:set(re.findall(r"[a-z]+",value.lower()))-stop
 q=words(query); t=words(title)
 return bool(q & t)
def commons(query,path):
 params={"action":"query","format":"json","generator":"search","gsrsearch":"filetype:bitmap "+query,"gsrnamespace":6,"gsrlimit":8,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1600}
 try:
  req=Request("https://commons.wikimedia.org/w/api.php?"+urlencode(params),headers={"User-Agent":"ImamAli110Preview/1.0"})
  with urlopen(req,timeout=18) as r:data=json.loads(r.read().decode())
  pages=list((data.get("query",{}).get("pages") or {}).values());random.Random(query).shuffle(pages)
  for page in pages:
   info=(page.get("imageinfo") or [{}])[0];url=info.get("thumburl") or info.get("url")
   if not url or not url.lower().split("?")[0].endswith((".jpg",".jpeg",".png",".webp")):continue
   title=page.get("title","")
   if not relevant_image(title,query):continue
   try:
    with urlopen(Request(url,headers={"User-Agent":"ImamAli110Preview/1.0"}),timeout=20) as r:raw=r.read()
    if len(raw)<10000:continue
    path.write_bytes(raw);m=info.get("extmetadata") or {}
    return {"scene":title,"artist":m.get("Artist",{}).get("value","Not listed"),"license":m.get("LicenseShortName",{}).get("value","Check source page"),"license_url":m.get("LicenseUrl",{}).get("value",""),"source_url":info.get("descriptionurl","")}
   except Exception:pass
 except Exception:pass
 return None
def fallback(path,n):
 base=[(17,31,55),(32,48,62),(37,55,45),(58,43,35)][(n-1)%4];im=Image.new("RGB",(W,H),base);d=ImageDraw.Draw(im)
 for i in range(9):
  c=tuple(min(255,x+i*5) for x in base);y=80+i*65;d.ellipse((-150+i*40,y,850+i*70,y+300),fill=c)
 d.ellipse((850,65,1040,255),fill=(230,193,120));im.save(path,quality=92)
def overlay(path,caption):
 im=Image.open(path).convert("RGB").resize((W,H));layer=Image.new("RGBA",im.size,(0,0,0,0));d=ImageDraw.Draw(layer)
 d.rectangle((40,35,W-40,120),fill=(0,0,0,135));d.rounded_rectangle((55,H-250,W-55,H-60),radius=26,fill=(0,0,0,178))
 d.text((W-72,60),"ImamAli110",font=brand_font(30),fill=(247,216,153),anchor="ra")
 f=font(43);lines=[];cur=""
 for word in caption.split():
  cand=(cur+" "+word).strip()
  try:wide=d.textbbox((0,0),cand,font=f,direction="rtl",language="fa")[2]>W-180
  except TypeError:wide=len(cand)>35
  if wide and cur:lines.append(cur);cur=word
  else:cur=cand
 if cur:lines.append(cur)
 y=H-156-(min(3,len(lines))*62)//2
 for line in lines[:3]:
  d.text((W-90,y),line,font=f,fill="white",anchor="ra",direction="rtl",language="fa",stroke_width=1,stroke_fill=(0,0,0));y+=62
 Image.alpha_composite(im.convert("RGBA"),layer).convert("RGB").save(path,quality=94)
async def voice(text,path):await edge_tts.Communicate(text,voice="fa-IR-FaridNeural",rate="-5%").save(str(path))
def run():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/"scenes").mkdir(exist_ok=True);story=STORIES[date.today().toordinal()%len(STORIES)]
 script=" ".join([story["hook"],*(s[0] for s in story["scenes"]),story["ending"]])
 (OUT/"script_fa.txt").write_text(story["title"]+"\n\nقلاب: "+story["hook"]+"\n\n"+"\n".join(f"{i+1}. {s[0]}" for i,s in enumerate(story["scenes"]))+"\n\nپایان: "+story["ending"]+"\n",encoding="utf-8")
 credits=[];scenes=[];scene_qc=[]
 for i,(caption,query) in enumerate(story["scenes"],1):
  p=OUT/"scenes"/f"scene_{i:02d}.jpg";meta=commons(query,p)
  if meta:
   meta["scene_number"]=i;meta["requested_query"]=query;credits.append(meta);scene_qc.append({"scene_number":i,"caption":caption,"query":query,"image_source":"Wikimedia Commons","image_title":meta.get("scene",""),"fallback":False,"status":"candidate_requires_visual_review"})
   try:
    im=Image.open(p).convert("RGB");ratio=max(W/im.width,H/im.height);im=im.resize((int(im.width*ratio),int(im.height*ratio)));x,y=(im.width-W)//2,(im.height-H)//2;im.crop((x,y,x+W,y+H)).save(p,quality=94)
   except Exception:fallback(p,i);credits[-1]["used_fallback"]=True
  else:fallback(p,i);credits.append({"scene_number":i,"requested_query":query,"note":"Commons unavailable; abstract generated background used."});scene_qc.append({"scene_number":i,"caption":caption,"query":query,"image_source":"abstract fallback","image_title":"","fallback":True,"status":"rejected_no_relevant_image"})
  overlay(p,caption);scenes.append(p)
 audio=OUT/"narration_fa.mp3";asyncio.run(voice(script,audio))
 probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)],capture_output=True,text=True,check=True,timeout=30)
 duration=max(8.0,float(probe.stdout.strip()));each=duration/len(scenes)+0.3;video=OUT/"imamali110_no_key_preview.mp4";cmd=["ffmpeg","-y","-hide_banner","-loglevel","error"]
 for p in scenes:cmd+=["-loop","1","-t",f"{each:.3f}","-i",str(p)]
 cmd+=["-i",str(audio)];filt="".join(f"[{i}:v]scale={W}:{H},setsar=1,format=yuv420p[v{i}];" for i in range(len(scenes)))+"".join(f"[v{i}]" for i in range(len(scenes)))+f"concat=n={len(scenes)}:v=1:a=0[v]"
 cmd+=["-filter_complex",filt,"-map","[v]","-map",f"{len(scenes)}:a:0","-c:v","libx264","-preset","veryfast","-crf","20","-r","24","-c:a","aac","-b:a","192k","-pix_fmt","yuv420p","-shortest","-movflags","+faststart",str(video)]
 subprocess.run(cmd,check=True,timeout=600)
 (OUT/"image_credits.json").write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding="utf-8")
 external=sum(not item["fallback"] for item in scene_qc)
 approved=external==len(scene_qc) and len(scene_qc)==4
 quality={"status":"PASS_PREVIEW_ONLY" if approved else "REJECTED_NOT_FOR_PUBLISHING","approved_for_publishing":False,"reason":"All four scenes have external image candidates, but human visual review is still required." if approved else f"Only {external}/4 scenes have matching external image candidates; abstract fallbacks are not acceptable for publishing.","external_image_candidates":external,"scene_count":len(scene_qc),"scenes":scene_qc,"automated_checks":["Persian script generated","vertical 720x1280 video rendered","narration rendered","image credits emitted"],"manual_review_required":["verify each image semantically matches narration","check Persian typography and line wrapping","listen to narration for pronunciation and emotional pacing","confirm pacing and scene transitions"]}
 (OUT/"quality_report.json").write_text(json.dumps(quality,ensure_ascii=False,indent=2),encoding="utf-8")
 (OUT/"preview_manifest.json").write_text(json.dumps({"title":story["title"],"story_id":story["id"],"format":"720x1280 vertical Shorts preview","voice":"Microsoft Edge TTS fa-IR-FaridNeural","published":False,"source":"curated story bank; no Groq, Pexels, or API keys required","video":video.name,"credits_file":"image_credits.json"},ensure_ascii=False,indent=2),encoding="utf-8")
 print("PREVIEW_READY="+str(video));print("STORY_ID="+story["id"]);print(f"VOICE_SECONDS={duration:.1f}");print("EXTERNAL_IMAGES="+str(external));print("QUALITY_STATUS="+quality["status"]);print("PUBLISHING=DISABLED")
if __name__=="__main__":run()
