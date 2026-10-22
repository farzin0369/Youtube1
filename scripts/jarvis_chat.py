import json, os, sys, time
from openai import OpenAI
SYSTEM = """تو Jarvis، دستیار اجرایی کاربر هستی. فارسی طبیعی پاسخ بده. فقط درباره اقداماتی ادعا کن که واقعاً انجام و بررسی شده‌اند. برای محتوای YouTube اصیل باش و از کپی و تعامل جعلی پرهیز کن."""
MODELS=["minimax/minimax-m3.1-flash:free","google/gemma-4-26b-a4b-it:free","nvidia/nemotron-3-super-120b-a12b:free"]
def run(prompt, history):
 key=os.getenv("OPENROUTER_API_KEY","").strip()
 if not key: raise RuntimeError("Secret با نام OPENROUTER_API_KEY در GitHub تنظیم نشده است.")
 client=OpenAI(base_url="https://openrouter.ai/api/v1",api_key=key,timeout=45,max_retries=0)
 messages=[{"role":"system","content":SYSTEM}]
 for m in history[-16:]:
  if isinstance(m,dict) and m.get("role") in ("user","assistant") and isinstance(m.get("content"),str): messages.append({"role":m["role"],"content":m["content"][:6000]})
 messages.append({"role":"user","content":prompt[:12000]})
 errors=[]
 for model in MODELS:
  try:
   t=time.monotonic(); r=client.chat.completions.create(model=model,messages=messages,max_tokens=1000,temperature=.35)
   ans=r.choices[0].message.content
   if ans and ans.strip():
    print(f"[Jarvis] model={model} elapsed={time.monotonic()-t:.1f}s",file=sys.stderr); return ans.strip()
   errors.append(model+": empty response")
  except Exception as e: errors.append(model+": "+type(e).__name__+" "+str(e)[:180])
 raise RuntimeError("مدل‌های رایگان OpenRouter پاسخ ندادند: "+" | ".join(errors))
if __name__=="__main__":
 try: h=json.loads(os.getenv("HISTORY","[]")); h=h if isinstance(h,list) else []
 except Exception: h=[]
 try: print(run(os.getenv("PROMPT","سلام جارویس"),h))
 except Exception as e: print("Jarvis error: "+str(e),file=sys.stderr); sys.exit(1)
