#!/usr/bin/env python3
"""One-time optional OAuth helper for read-only YouTube Analytics access.

This creates a separate refresh token so existing upload credentials are not changed.
Use the same Google OAuth Desktop client as the YouTube upload integration.
"""
from __future__ import annotations

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]


def main() -> None:
    print("=== Optional YouTube Analytics token ===")
    print("Use the same OAuth client ID/secret as the channel integration.")
    client_id = input("Client ID: ").strip()
    client_secret = input("Client secret: ").strip()
    if not client_id or not client_secret:
        raise SystemExit("Client ID and client secret are required.")
    config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")
    if not creds.refresh_token:
        raise SystemExit(
            "Google did not return a refresh token. Revoke only the analytics grant and retry."
        )
    print("\nAdd this separate secret to GitHub Actions:")
    print("Name: YOUTUBE_ANALYTICS_REFRESH_TOKEN")
    print(f"Value: {creds.refresh_token}")
    print("Do not replace YOUTUBE_REFRESH_TOKEN; that token is used for uploads/comments.")


if __name__ == "__main__":
    main()
