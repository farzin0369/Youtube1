# YouTube Automation — Imam Ali

اتوماسیون امن برای [imamali.110](https://www.youtube.com/@imamali.110)

## زمان‌بندی (Asia/Tehran)
| 06:00 | Short |
| 20:30 | Long |

## حالت ایمن
آپلود فقط private/unlisted — انتشار عمومی خاموش است.

## Pipeline
1. موضوع (`app/research.py`)
2. اسکریپت فارسی (`app/script_gen.py`)
3. TTS (`app/tts.py`)
4. ویدیو + کپشن + تامبنیل (`app/video_render.py`)
5. آپلود خصوصی (`app/youtube_client.py`)

## Secrets
`YOUTUBE_CLIENT_ID` · `YOUTUBE_CLIENT_SECRET` · `YOUTUBE_REFRESH_TOKEN` · `OPENAI_API_KEY`

## اجرا
```bash
pip install -r requirements.txt
python -m app.pipeline --kind short --publish-mode private
python -m app.pipeline --kind long --dry-run
```
