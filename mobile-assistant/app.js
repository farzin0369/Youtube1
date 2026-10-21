const $=s=>document.querySelector(s);
const chatForm=$("#chat-form"),promptBox=$("#prompt"),messages=$("#messages"),welcome=$("#welcome"),sendButton=$("#send"),settingsDialog=$("#settings-dialog");
const keys={url:"hamrah.apiUrl",model:"hamrah.model",key:"hamrah.apiKey"};
function settings(){return {url:localStorage.getItem(keys.url)||"",model:localStorage.getItem(keys.model)||"",key:localStorage.getItem(keys.key)||""}}
function loadSettings(){const s=settings();$("#api-url").value=s.url;$("#model-name").value=s.model;$("#api-key").value=s.key}
function appendMessage(role,text,extraClass=""){welcome.hidden=true;const el=document.createElement("article");el.className="message "+role+(extraClass?" "+extraClass:"");const label=document.createElement("div");label.className="message-label";label.textContent=role==="user"?"شما":"همراه هوشمند";const body=document.createElement("div");body.textContent=text;el.append(label,body);messages.append(el);$("#chat").scrollTop=$("#chat").scrollHeight;return el}
function openAction(action){if(action==="google"){window.open("https://www.google.com/search?q="+encodeURIComponent(promptBox.value.trim()||""),"_blank","noopener");return true}if(action==="github"){window.open("https://github.com/farzin0369/Youtube1","_blank","noopener");return true}return false}
document.querySelectorAll("[data-action]").forEach(b=>b.addEventListener("click",()=>openAction(b.dataset.action)));
document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>{promptBox.value=b.dataset.prompt;promptBox.focus()}));
$("#settings-open").addEventListener("click",()=>{loadSettings();settingsDialog.showModal()});
$("#save-settings").addEventListener("click",()=>{localStorage.setItem(keys.url,$("#api-url").value.trim().replace(/\/$/,""));localStorage.setItem(keys.model,$("#model-name").value.trim());localStorage.setItem(keys.key,$("#api-key").value.trim());});
$("#clear-settings").addEventListener("click",()=>{Object.values(keys).forEach(k=>localStorage.removeItem(k));loadSettings();});
promptBox.addEventListener("input",()=>{promptBox.style.height="auto";promptBox.style.height=Math.min(promptBox.scrollHeight,180)+"px"});
promptBox.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();chatForm.requestSubmit()}});
let history=[];
async function askAI(text,assistantNode){const s=settings();if(!s.url||!s.model||!s.key){assistantNode.classList.add("error");assistantNode.lastChild.textContent="برای پاسخ واقعی باید نشانی API، نام مدل و کلید را در ⚙ تنظیم کنی. این نسخه به‌تنهایی مدل هوش مصنوعی یا سرور رایگان داخلی ندارد.";return}
const endpoint=s.url.endsWith("/chat/completions")?s.url:s.url+"/chat/completions";
try{const res=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+s.key},body:JSON.stringify({model:s.model,messages:[{role:"system",content:"تو یک دستیار دقیق، مودب و توانمند هستی. به زبان کاربر پاسخ بده. درباره توانایی اجرای کارها صادق باش. اگر کار نیازمند اقدام بیرونی است، توضیح بده چه چیزی را واقعاً می‌توانی انجام بدهی و بدون تأیید ادعا نکن."},...history,{role:"user",content:text}],temperature:0.7})});if(!res.ok)throw new Error("خطای سرویس: HTTP "+res.status+"؛ نشانی، کلید و مدل را بررسی کن.");const data=await res.json();const answer=data.choices?.[0]?.message?.content;if(!answer)throw new Error("پاسخ قابل‌خواندن از API دریافت نشد.");history.push({role:"user",content:text},{role:"assistant",content:answer});if(history.length>24)history=history.slice(-24);assistantNode.lastChild.textContent=answer}catch(err){assistantNode.classList.add("error");assistantNode.lastChild.textContent="اتصال برقرار نشد: "+(err.message||"خطای ناشناخته")+". اگر مرورگر خطای CORS نشان دهد، سرویس API باید دسترسی مرورگر را فعال کند."}}
chatForm.addEventListener("submit",async e=>{e.preventDefault();const text=promptBox.value.trim();if(!text||sendButton.disabled)return;appendMessage("user",text);promptBox.value="";promptBox.style.height="auto";sendButton.disabled=true;const reply=appendMessage("assistant","در حال آماده‌سازی پاسخ…");await askAI(text,reply);sendButton.disabled=false;promptBox.focus()});
if("serviceWorker" in navigator && location.protocol.startsWith("http"))window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));


// Safe GitHub repository inspection: read-only; never edits or merges code.
async function inspectRepository(){
  const userNode=appendMessage("user","مخزن GitHub را بررسی کن");
  const reply=appendMessage("assistant","در حال خواندن فهرست فایل‌های مخزن به‌صورت فقط‌خواندنی…");
  try{
    const response=await fetch("https://api.github.com/repos/farzin0369/Youtube1/git/trees/main?recursive=1",{headers:{"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}});
    if(!response.ok)throw new Error("GitHub API پاسخ HTTP "+response.status+" داد.");
    const data=await response.json();
    const paths=(data.tree||[]).filter(x=>x.type==="blob").map(x=>x.path);
    const relevant=paths.filter(p=>/^(app|scripts|mobile-assistant|\.github\/workflows|docs)\//.test(p)).slice(0,90);
    reply.lastChild.textContent="بررسی فقط‌خواندنی مخزن انجام شد. تعداد فایل‌های قابل مشاهده: "+paths.length+"\n\nفایل‌های مهم (حداکثر ۹۰ مورد):\n"+(relevant.length?relevant.map(p=>"• "+p).join("\n"):"فایلی در مسیرهای منتخب پیدا نشد.")+"\n\nاین قابلیت فقط فایل‌های شاخه main را می‌خواند؛ هنوز کدی را تغییر نمی‌دهد، تست اجرا نمی‌کند و Pull Request نمی‌سازد.";
  }catch(err){
    reply.classList.add("error");
    reply.lastChild.textContent="نتوانستم مخزن را از GitHub بخوانم: "+err.message+"\nبررسی به دسترسی شبکه و عمومی بودن مخزن وابسته است. این ابزار هیچ تغییری در مخزن ایجاد نمی‌کند.";
  }
}
document.querySelectorAll('[data-action="inspect"]').forEach(b=>b.addEventListener("click",inspectRepository));
