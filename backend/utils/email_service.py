"""
utils/email_service.py
──────────────────────
Sends OTP emails via Gmail SMTP — 100% free, no domain needed.

Setup (one-time):
  1. Create / use a Gmail account  e.g. noreplylumera@gmail.com
  2. Enable 2-Step Verification on that account
       myaccount.google.com → Security → 2-Step Verification → Turn On
  3. Generate an App Password
       myaccount.google.com → Security → 2-Step Verification → App passwords
       → name it "Lumera" → copy the 16-character code (spaces don't matter)
  4. Add to backend/.env:
       GMAIL_USER=noreplylumera@gmail.com
       GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
  5. Add the same two vars to HF Spaces Secrets dashboard.

No domain, no paid service, no DNS records.
Gmail free tier: 500 emails/day (plenty for personal/indie use).
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_USER     = os.environ.get('GMAIL_USER', '')
GMAIL_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', '')   # App Password, NOT your Gmail password
APP_NAME       = 'Luméra'

# Gmail SMTP constants — never change these
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 465   # SSL port (simpler than STARTTLS on 587)


# ── HTML template ─────────────────────────────────────────────────────────────

def _build_html(username: str, code: str, purpose: str) -> str:
    if purpose == 'reset':
        headline    = 'Reset your password'
        subline     = ('Use the code below to reset your Luméra password. '
                       'It expires in <strong>10 minutes</strong>.')
        footer_note = "If you didn't request a password reset, you can safely ignore this email."
    elif purpose == 'login':
        headline    = 'Your login code'
        subline     = ('Use the code below to sign in to Luméra. '
                       'It expires in <strong>10 minutes</strong>.')
        footer_note = "If you didn't try to log in, you can safely ignore this email."
    else:
        headline    = 'Verify your email'
        subline     = ('Welcome to Luméra! Enter the code below to activate your account. '
                       'It expires in <strong>10 minutes</strong>.')
        footer_note = "If you didn't create a Luméra account, you can safely ignore this email."

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{headline} — {APP_NAME}</title>
</head>
<body style="margin:0;padding:0;background:#f5f3ff;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f3ff;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:16px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(109,40,217,.10);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#7c3aed,#a855f7);
                       padding:32px 40px;text-align:center;">
              <div style="font-size:28px;font-weight:800;color:#ffffff;
                          letter-spacing:-0.5px;">✦ {APP_NAME}</div>
              <div style="color:#e9d5ff;font-size:13px;margin-top:4px;">
                AI Skincare Analysis
              </div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">
              <p style="margin:0 0 8px;font-size:22px;font-weight:700;
                        color:#1e1b4b;">{headline}</p>
              <p style="margin:0 0 28px;font-size:15px;color:#64748b;
                        line-height:1.6;">
                Hi <strong>{username}</strong>, {subline}
              </p>

              <!-- OTP box -->
              <div style="background:#f5f3ff;border:2px dashed #a78bfa;
                          border-radius:12px;padding:24px;text-align:center;
                          margin-bottom:28px;">
                <div style="font-size:42px;font-weight:800;letter-spacing:10px;
                            color:#7c3aed;font-variant-numeric:tabular-nums;">
                  {code}
                </div>
                <div style="font-size:12px;color:#a78bfa;margin-top:8px;">
                  Expires in 10 minutes
                </div>
              </div>

              <p style="margin:0;font-size:13px;color:#94a3b8;line-height:1.6;">
                {footer_note}
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#faf9ff;padding:20px 40px;
                       border-top:1px solid #ede9fe;text-align:center;">
              <p style="margin:0;font-size:12px;color:#c4b5fd;">
                © {APP_NAME} · Built with care for your skin
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _subject(purpose: str) -> str:
    if purpose == 'reset':
        return f'Your {APP_NAME} password reset code'
    elif purpose == 'login':
        return f'Your {APP_NAME} login code'
    return f'Verify your {APP_NAME} account'


# ── Public API ─────────────────────────────────────────────────────────────────

def send_otp_email(to_email: str, username: str, code: str, purpose: str = 'verify') -> bool:
    """
    Send an OTP email via Gmail SMTP.
    Returns True on success, False on failure — never raises.
    """
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print('⚠️  GMAIL_USER / GMAIL_APP_PASSWORD not set — skipping email send')
        print(f'   [DEV] OTP for {to_email}: {code}')
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = _subject(purpose)
        msg['From']    = f'{APP_NAME} <{GMAIL_USER}>'
        msg['To']      = to_email

        # Plain-text fallback (shown in clients that block HTML)
        plain = (
            f"Hi {username},\n\n"
            f"Your "
            f"{'password reset' if purpose == 'reset' else 'login' if purpose == 'login' else 'verification'}"
            f" code is: {code}\n\n"
            f"It expires in 10 minutes.\n\n"
            f"— The {APP_NAME} team"
        )
        msg.attach(MIMEText(plain, 'plain'))
        msg.attach(MIMEText(_build_html(username, code, purpose), 'html'))

        # SSL connection on port 465 — simpler than STARTTLS
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())

        print(f'📧 Email sent ({purpose}) → {to_email}')
        return True

    except smtplib.SMTPAuthenticationError:
        print('❌ Gmail SMTP auth failed — check GMAIL_USER and GMAIL_APP_PASSWORD')
        print('   Make sure you are using an App Password, not your regular Gmail password.')
        print(f'   [DEV fallback] OTP for {to_email}: {code}')
        return False

    except Exception as exc:
        print(f'❌ Gmail SMTP error: {exc}')
        print(f'   [DEV fallback] OTP for {to_email}: {code}')
        return False