#!/usr/bin/env python3
"""One-time helper: get YOUTUBE_REFRESH_TOKEN for GitHub Secrets.

Run on your computer (not on GitHub Actions):

  pip install google-auth-oauthlib google-auth-httplib2
  python scripts/get_youtube_token.py

Browser opens once → login with the YouTube channel Google account → Allow.
Then copy the three values into GitHub Actions secrets.
"""
from __future__ import annotations

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube",
]


def main() -> None:
    print("=== YouTube token (one time) ===\n")
    client_id = input("Client ID: ").strip()
    client_secret = input("Client secret: ").strip()
    if not client_id or not client_secret:
        raise SystemExit("Client ID and Client secret are required.")

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        raise SystemExit(
            "No refresh_token returned. Revoke app access at "
            "https://myaccount.google.com/permissions and run again."
        )

    print("\n========== PUT THESE IN GITHUB SECRETS ==========")
    print("Name: YOUTUBE_CLIENT_ID")
    print(f"Value: {client_id}\n")
    print("Name: YOUTUBE_CLIENT_SECRET")
    print(f"Value: {client_secret}\n")
    print("Name: YOUTUBE_REFRESH_TOKEN")
    print(f"Value: {creds.refresh_token}")
    print("================================================")
    print("\nGitHub → Youtube1 → Settings → Secrets and variables → Actions")
    print("Then tell Grok: token is ready")


if __name__ == "__main__":
    main()
