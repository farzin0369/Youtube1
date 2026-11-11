# Ready-made YouTube Studio uploader: yt-studio

This repository's existing Python pipeline remains responsible for creating the MP4. The external project `sstani-bgv/yt-studio` is an uploader/Studio manager, not a video generator.

Upstream: https://github.com/sstani-bgv/yt-studio

## Important constraints

- Unofficial tool; it uses private YouTube Studio endpoints that may change and automated use may conflict with YouTube/Google terms. Review the upstream warning before use.
- It does **not** accept a YouTube username/password as a script argument. Authentication requires a dedicated interactive Chrome profile, Google sign-in (including 2FA/CAPTCHA if requested), channel selection, and session capture.
- Captured browser session files are credentials. Never commit them, paste them into chat, or store them unencrypted in this repository.
- Its Studio security token expires after 90 minutes. A GitHub-hosted runner is ephemeral, so a captured session is not a drop-in replacement for the existing OAuth uploader or a zero-setup daily automation solution.
- No production upload should be enabled until authentication and an unlisted/private test upload have been verified on the intended channel.

## Upstream installation and authentication

Use the upstream instructions, which may change:

1. Install Python 3.10+, Chrome, and the package with Playwright support.
2. Open a dedicated browser profile with `ytstudio-safe auth-open --session-name youtube-sandbox --browser-channel chrome`.
3. Sign in yourself, complete any 2FA/CAPTCHA, and select the correct YouTube channel.
4. Capture and bind the session to the exact channel ID using `ytstudio-safe auth-capture --session-name youtube-sandbox --browser-channel chrome --expected-channel-id UC_REPLACE_WITH_CHANNEL_ID`.
5. Capture the short-lived security token with `ytstudio-safe security-capture --session-name youtube-sandbox`.
6. Review a dry run first. Upstream mutations require explicit `--apply` and exact `--confirm` values.

See the upstream README for the current commands and safety model:
https://github.com/sstani-bgv/yt-studio#readme

## Current integration status

This document records the selected ready-made uploader and its operational constraints. It does not claim that the uploader is installed, authenticated, connected to this pipeline, or able to publish. Those steps require a real interactive Google login and session on a controlled machine; no account password or session has been collected by this repository change.
