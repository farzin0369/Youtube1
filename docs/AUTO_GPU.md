# اتومات GPU

## مسیر اصلی الان: **Colab CLI**

Kaggle را کنار گذاشتیم (به خواست تو).

1. یک‌بار توکن بساز → Secret `COLAB_CLI_TOKEN_JSON`
2. راهنما: [COLAB_CLI_SETUP.md](COLAB_CLI_SETUP.md)
3. Workflow: `.github/workflows/colab_cli_gpu.yml`

```
GitHub Actions
    → colab run --gpu T4 scripts/colab_render_minimal.py
    → video_raw.mp4
    → (بعداً) صدا + زیرنویس + یوتیوب
```

بدون Secret → فقط Mixkit (روزانه پایدار).
