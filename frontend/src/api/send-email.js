/**
 * Vercel Serverless Function: /api/send-email
 * 
 * Called by HF Spaces backend to send OTP emails via Gmail SMTP.
 * Vercel's network allows outbound SMTP — HF Spaces does not.
 * 
 * Environment variables to set in Vercel dashboard:
 *   GMAIL_USER          = noreplylumera@gmail.com
 *   GMAIL_APP_PASSWORD  = xxxx xxxx xxxx xxxx
 *   EMAIL_SECRET        = any_long_random_string (shared with HF backend)
 */

const nodemailer = require('nodemailer');

const APP_NAME = 'Luméra';

function buildHtml(username, code, purpose) {
  const configs = {
    reset: {
      headline: 'Reset your password',
      subline:  'Use the code below to reset your Luméra password. It expires in <strong>10 minutes</strong>.',
      footer:   "If you didn't request a password reset, you can safely ignore this email.",
    },
    login: {
      headline: 'Your login code',
      subline:  'Use the code below to sign in to Luméra. It expires in <strong>10 minutes</strong>.',
      footer:   "If you didn't try to log in, you can safely ignore this email.",
    },
    verify: {
      headline: 'Verify your email',
      subline:  'Welcome to Luméra! Enter the code below to activate your account. It expires in <strong>10 minutes</strong>.',
      footer:   "If you didn't create a Luméra account, you can safely ignore this email.",
    },
  };
  const { headline, subline, footer } = configs[purpose] || configs.verify;

  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#f5f3ff;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f3ff;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(109,40,217,.10);">
        <tr>
          <td style="background:linear-gradient(135deg,#7c3aed,#a855f7);padding:32px 40px;text-align:center;">
            <div style="font-size:26px;font-weight:800;color:#fff;">✦ ${APP_NAME}</div>
            <div style="color:#e9d5ff;font-size:13px;margin-top:4px;">AI Skincare Analysis</div>
          </td>
        </tr>
        <tr>
          <td style="padding:40px 40px 32px;">
            <p style="margin:0 0 8px;font-size:22px;font-weight:700;color:#1e1b4b;">${headline}</p>
            <p style="margin:0 0 28px;font-size:15px;color:#64748b;line-height:1.6;">
              Hi <strong>${username}</strong>, ${subline}
            </p>
            <div style="background:#f5f3ff;border:2px dashed #a78bfa;border-radius:12px;padding:24px;text-align:center;margin-bottom:28px;">
              <div style="font-size:42px;font-weight:800;letter-spacing:10px;color:#7c3aed;">${code}</div>
              <div style="font-size:12px;color:#a78bfa;margin-top:8px;">Expires in 10 minutes</div>
            </div>
            <p style="margin:0;font-size:13px;color:#94a3b8;">${footer}</p>
          </td>
        </tr>
        <tr>
          <td style="background:#faf9ff;padding:20px 40px;border-top:1px solid #ede9fe;text-align:center;">
            <p style="margin:0;font-size:12px;color:#c4b5fd;">© ${APP_NAME} · Built with care for your skin</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`;
}

module.exports = async function handler(req, res) {
  // Only POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Shared secret check — prevents anyone else calling this endpoint
  const { to, username, code, purpose, secret } = req.body || {};
  if (secret !== process.env.EMAIL_SECRET) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  if (!to || !username || !code || !purpose) {
    return res.status(400).json({ error: 'Missing fields' });
  }

  if (!process.env.GMAIL_USER || !process.env.GMAIL_APP_PASSWORD) {
    console.error('Gmail credentials not set');
    return res.status(500).json({ error: 'Email service not configured' });
  }

  try {
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.GMAIL_USER,
        pass: process.env.GMAIL_APP_PASSWORD,
      },
    });

    const subjects = {
      reset:  `Your ${APP_NAME} password reset code`,
      login:  `Your ${APP_NAME} login code`,
      verify: `Verify your ${APP_NAME} account`,
    };

    await transporter.sendMail({
      from:    `${APP_NAME} <${process.env.GMAIL_USER}>`,
      to,
      subject: subjects[purpose] || subjects.verify,
      html:    buildHtml(username, code, purpose),
      text:    `Hi ${username},\n\nYour code is: ${code}\n\nExpires in 10 minutes.\n\n— The ${APP_NAME} team`,
    });

    console.log(`Email sent (${purpose}) → ${to}`);
    return res.status(200).json({ ok: true });

  } catch (err) {
    console.error('Gmail send error:', err.message);
    return res.status(500).json({ error: 'Failed to send email' });
  }
};