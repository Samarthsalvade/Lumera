"""
utils/email_service.py
──────────────────────
Sends OTP emails by calling a Vercel serverless function over HTTPS.

WHY THIS APPROACH:
  HF Spaces blocks outbound SMTP (ports 465/587). This function calls
  a tiny Node.js handler deployed on your existing Vercel frontend project
  which has no such restriction and sends via Gmail SMTP normally.

SETUP:
  1. Deploy frontend/api/send-email.js (already in your frontend folder)
     It auto-deploys with your next  git push origin main

  2. Add these to Vercel dashboard → Settings → Environment Variables:
       GMAIL_USER         = noreplylumera@gmail.com
       GMAIL_APP_PASSWORD = xxxx xxxx xxxx xxxx   (App Password)
       EMAIL_SECRET       = some_long_random_string_you_invent

  3. Add these to HF Spaces Secrets dashboard:
       VERCEL_EMAIL_URL = https://lumera-wheat.vercel.app/api/send-email
       EMAIL_SECRET     = same_long_random_string_as_above

  4. Add to backend/.env for local dev:
       VERCEL_EMAIL_URL = https://lumera-wheat.vercel.app/api/send-email
       EMAIL_SECRET     = same_long_random_string_as_above
       (local dev will call the live Vercel function — that's fine)
"""

import os
import threading
import requests

VERCEL_EMAIL_URL = os.environ.get('VERCEL_EMAIL_URL', '')
EMAIL_SECRET     = os.environ.get('EMAIL_SECRET', '')
APP_NAME         = 'Luméra'


def _send(to_email: str, username: str, code: str, purpose: str) -> None:
    """Blocking HTTP POST to Vercel — always called from a daemon thread."""

    if not VERCEL_EMAIL_URL:
        print(f'⚠️  VERCEL_EMAIL_URL not set — skipping email')
        print(f'   [DEV] OTP for {to_email}: {code}')
        return

    try:
        resp = requests.post(
            VERCEL_EMAIL_URL,
            json={
                'to':       to_email,
                'username': username,
                'code':     code,
                'purpose':  purpose,
                'secret':   EMAIL_SECRET,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            print(f'📧 Email sent ({purpose}) → {to_email}')
        else:
            print(f'❌ Email function error {resp.status_code}: {resp.text}')
            print(f'   [DEV fallback] OTP for {to_email}: {code}')

    except Exception as exc:
        print(f'❌ Email request failed: {exc}')
        print(f'   [DEV fallback] OTP for {to_email}: {code}')


def send_otp_email(to_email: str, username: str, code: str, purpose: str = 'verify') -> None:
    """
    Fire-and-forget: spawns a daemon thread so the Flask endpoint
    returns immediately. The OTP is already in the DB before this
    is called so there is no race condition.
    """
    threading.Thread(
        target=_send,
        args=(to_email, username, code, purpose),
        daemon=True,
    ).start()