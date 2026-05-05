"""
utils/email_service.py
──────────────────────
Local dev  → sends via Gmail SMTP directly (works on Mac/Linux, port 465 open)
Production → calls Vercel serverless function over HTTPS (HF Spaces blocks SMTP)

Local .env needs:
    GMAIL_USER=noreplylumera@gmail.com
    GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

Production HF Spaces Secrets needs:
    VERCEL_EMAIL_URL=https://lumera-wheat.vercel.app/api/send-email
    EMAIL_SECRET=your_shared_secret
"""

import os
import threading
import smtplib
import ssl
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_USER       = os.environ.get('GMAIL_USER', '')
GMAIL_PASSWORD   = os.environ.get('GMAIL_APP_PASSWORD', '')
VERCEL_EMAIL_URL = os.environ.get('VERCEL_EMAIL_URL', '')
EMAIL_SECRET     = os.environ.get('EMAIL_SECRET', '')
APP_NAME         = 'Luméra'


# ── HTML template ──────────────────────────────────────────────────────────────

def _build_html(username: str, code: str, purpose: str) -> str:
    if purpose == 'reset':
        headline    = 'Reset your password'
        subline     = 'Use the code below to reset your Luméra password. It expires in <strong>10 minutes</strong>.'
        footer_note = "If you didn't request a password reset, you can safely ignore this email."
    elif purpose == 'login':
        headline    = 'Your login code'
        subline     = 'Use the code below to sign in to Luméra. It expires in <strong>10 minutes</strong>.'
        footer_note = "If you didn't try to log in, you can safely ignore this email."
    else:
        headline    = 'Verify your email'
        subline     = 'Welcome to Luméra! Enter the code below to activate your account. It expires in <strong>10 minutes</strong>.'
        footer_note = "If you didn't create a Luméra account, you can safely ignore this email."

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f5f3ff;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f3ff;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(109,40,217,.10);">
        <tr>
          <td style="background:linear-gradient(135deg,#7c3aed,#a855f7);padding:32px 40px;text-align:center;">
            <div style="font-size:26px;font-weight:800;color:#fff;">✦ {APP_NAME}</div>
            <div style="color:#e9d5ff;font-size:13px;margin-top:4px;">AI Skincare Analysis</div>
          </td>
        </tr>
        <tr>
          <td style="padding:40px 40px 32px;">
            <p style="margin:0 0 8px;font-size:22px;font-weight:700;color:#1e1b4b;">{headline}</p>
            <p style="margin:0 0 28px;font-size:15px;color:#64748b;line-height:1.6;">
              Hi <strong>{username}</strong>, {subline}
            </p>
            <div style="background:#f5f3ff;border:2px dashed #a78bfa;border-radius:12px;
                        padding:24px;text-align:center;margin-bottom:28px;">
              <div style="font-size:42px;font-weight:800;letter-spacing:10px;color:#7c3aed;">{code}</div>
              <div style="font-size:12px;color:#a78bfa;margin-top:8px;">Expires in 10 minutes</div>
            </div>
            <p style="margin:0;font-size:13px;color:#94a3b8;">{footer_note}</p>
          </td>
        </tr>
        <tr>
          <td style="background:#faf9ff;padding:20px 40px;border-top:1px solid #ede9fe;text-align:center;">
            <p style="margin:0;font-size:12px;color:#c4b5fd;">© {APP_NAME} · Built with care for your skin</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _subject(purpose: str) -> str:
    return {
        'reset': f'Your {APP_NAME} password reset code',
        'login': f'Your {APP_NAME} login code',
    }.get(purpose, f'Verify your {APP_NAME} account')


def _plain(username: str, code: str, purpose: str) -> str:
    label = {'reset': 'password reset', 'login': 'login'}.get(purpose, 'verification')
    return f"Hi {username},\n\nYour {label} code is: {code}\n\nExpires in 10 minutes.\n\n— The {APP_NAME} team"


# ── SMTP (local dev) ───────────────────────────────────────────────────────────

def _send_smtp(to_email: str, username: str, code: str, purpose: str) -> None:
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print(f'⚠️  GMAIL_USER / GMAIL_APP_PASSWORD not set')
        print(f'   [DEV] OTP for {to_email}: {code}')
        return
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = _subject(purpose)
        msg['From']    = f'{APP_NAME} <{GMAIL_USER}>'
        msg['To']      = to_email
        msg.attach(MIMEText(_plain(username, code, purpose), 'plain'))
        msg.attach(MIMEText(_build_html(username, code, purpose), 'html'))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        print(f'📧 [SMTP] Email sent ({purpose}) → {to_email}')

    except smtplib.SMTPAuthenticationError:
        print('❌ Gmail auth failed — check GMAIL_USER and GMAIL_APP_PASSWORD')
        print(f'   [DEV] OTP for {to_email}: {code}')
    except Exception as exc:
        print(f'❌ SMTP error: {exc}')
        print(f'   [DEV] OTP for {to_email}: {code}')


# ── Vercel function (production) ───────────────────────────────────────────────

def _send_vercel(to_email: str, username: str, code: str, purpose: str) -> None:
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
            print(f'📧 [Vercel] Email sent ({purpose}) → {to_email}')
        else:
            print(f'❌ Email function error {resp.status_code}: {resp.text}')
            print(f'   [DEV fallback] OTP for {to_email}: {code}')
    except Exception as exc:
        print(f'❌ Vercel email request failed: {exc}')
        print(f'   [DEV fallback] OTP for {to_email}: {code}')


# ── Public API ─────────────────────────────────────────────────────────────────

def send_otp_email(to_email: str, username: str, code: str, purpose: str = 'verify') -> None:
    """
    Automatically picks the right transport:
      - No VERCEL_EMAIL_URL set → local dev → Gmail SMTP directly
      - VERCEL_EMAIL_URL set    → production → call Vercel function over HTTPS
    Always fires in a background thread so the Flask endpoint returns instantly.
    """
    target = _send_vercel if VERCEL_EMAIL_URL else _send_smtp
    threading.Thread(
        target=target,
        args=(to_email, username, code, purpose),
        daemon=True,
    ).start()