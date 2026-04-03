import random
import string
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from models import db, User
from utils.email_service import send_otp_email   # ← we create this next

auth_bp = Blueprint('auth', __name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _generate_otp() -> str:
    """Return a random 6-digit numeric string."""
    return ''.join(random.choices(string.digits, k=6))


def _set_otp(user: User, purpose: str) -> str:
    """Attach a fresh OTP to the user row and return the code."""
    code = _generate_otp()
    user.otp_code       = code
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    user.otp_purpose    = purpose   # 'verify' | 'reset' | 'login'
    return code


def _clear_otp(user: User) -> None:
    user.otp_code       = None
    user.otp_expires_at = None
    user.otp_purpose    = None


def _otp_valid(user: User, code: str, purpose: str) -> bool:
    return (
        user.otp_code == code
        and user.otp_purpose == purpose
        and user.otp_expires_at is not None
        and datetime.utcnow() < user.otp_expires_at
    )


# ── /register ─────────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        print(f"📝 Registration attempt: {data.get('email')}")

        if not data or not data.get('email') or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400

        # If an unverified account with this email already exists, let the
        # user re-request an OTP rather than blocking them forever.
        existing = User.query.filter_by(email=data['email']).first()
        if existing:
            if existing.is_verified:
                return jsonify({'error': 'Email already registered'}), 400
            # Overwrite the stale unverified row with fresh credentials
            existing.username = data['username']
            existing.set_password(data['password'])
            code = _set_otp(existing, 'verify')
            db.session.commit()
            send_otp_email(existing.email, existing.username, code, purpose='verify')
            print(f"♻️  Re-sent OTP to unverified account: {existing.email}")
            return jsonify({
                'message': 'OTP resent. Please check your email.',
                'email':   existing.email,
            }), 200

        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400

        user = User(
            email       = data['email'],
            username    = data['username'],
            is_verified = False,
        )
        user.set_password(data['password'])
        code = _set_otp(user, 'verify')

        db.session.add(user)
        db.session.commit()

        send_otp_email(user.email, user.username, code, purpose='verify')
        print(f"✅ User created (unverified): {user.email}")

        return jsonify({
            'message': 'Account created. Check your email for the verification code.',
            'email':   user.email,
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Registration error: {e}")
        return jsonify({'error': str(e)}), 500


# ── /verify-otp ───────────────────────────────────────────────────────────────

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """
    Body: { "email": "...", "otp": "123456", "purpose": "verify|reset|login" }
    - verify : activates account + returns JWT
    - reset  : returns short-lived reset_token
    - login  : returns JWT (passwordless login)
    """
    try:
        data = request.get_json()
        email   = (data or {}).get('email', '').strip().lower()
        otp     = (data or {}).get('otp', '').strip()
        purpose = (data or {}).get('purpose', 'verify')

        if not email or not otp:
            return jsonify({'error': 'Email and OTP are required'}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'Invalid OTP or email'}), 400

        if not _otp_valid(user, otp, purpose):
            return jsonify({'error': 'Invalid or expired OTP'}), 400

        _clear_otp(user)

        if purpose == 'verify':
            user.is_verified = True
            db.session.commit()
            access_token = create_access_token(identity=str(user.id))
            print(f"✅ Email verified: {user.email}")
            return jsonify({
                'message':      'Email verified successfully!',
                'access_token': access_token,
                'user':         user.to_dict(),
            }), 200

        elif purpose == 'login':
            db.session.commit()
            access_token = create_access_token(identity=str(user.id))
            print(f"✅ OTP login: {user.email}")
            return jsonify({
                'message':      'Login successful',
                'access_token': access_token,
                'user':         user.to_dict(),
            }), 200

        elif purpose == 'reset':
            db.session.commit()
            reset_token = create_access_token(
                identity=str(user.id),
                expires_delta=timedelta(minutes=15),
                additional_claims={'reset': True},
            )
            print(f"✅ Reset OTP verified: {user.email}")
            return jsonify({
                'message':     'OTP verified. You may now reset your password.',
                'reset_token': reset_token,
            }), 200

        return jsonify({'error': 'Unknown purpose'}), 400

    except Exception as e:
        db.session.rollback()
        print(f"❌ verify-otp error: {e}")
        return jsonify({'error': str(e)}), 500


# ── /resend-otp ───────────────────────────────────────────────────────────────

@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Body: { "email": "...", "purpose": "verify" | "reset" }"""
    try:
        data    = request.get_json()
        email   = (data or {}).get('email', '').strip().lower()
        purpose = (data or {}).get('purpose', 'verify')

        user = User.query.filter_by(email=email).first()
        if not user:
            # Don't leak whether the email exists
            return jsonify({'message': 'If that email is registered, a new code has been sent.'}), 200

        if purpose == 'verify' and user.is_verified:
            return jsonify({'error': 'Account is already verified'}), 400

        if purpose not in ('verify', 'reset', 'login'):
            return jsonify({'error': 'Invalid purpose'}), 400

        code = _set_otp(user, purpose)
        db.session.commit()
        send_otp_email(user.email, user.username, code, purpose=purpose)
        print(f"📧 OTP resent ({purpose}): {user.email}")
        return jsonify({'message': 'A new code has been sent to your email.'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ resend-otp error: {e}")
        return jsonify({'error': str(e)}), 500


# ── /send-login-otp ───────────────────────────────────────────────────────────

@auth_bp.route('/send-login-otp', methods=['POST'])
def send_login_otp():
    """
    Passwordless login — step 1.
    Body: { "email": "..." }
    Sends a 6-digit OTP if the email belongs to a verified account.
    Always returns 200 to avoid leaking whether an email is registered.
    """
    try:
        data  = request.get_json()
        email = (data or {}).get('email', '').strip().lower()

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = User.query.filter_by(email=email).first()

        if not user or not user.is_verified:
            # Silent 200 — don't reveal account existence
            return jsonify({'message': 'If that email is registered, a login code has been sent.'}), 200

        code = _set_otp(user, 'login')
        db.session.commit()
        send_otp_email(user.email, user.username, code, purpose='login')
        print(f"📧 Login OTP sent: {user.email}")
        return jsonify({'message': 'Login code sent. Check your email.'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ send-login-otp error: {e}")
        return jsonify({'error': str(e)}), 500


# ── /login ────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        print(f"🔑 Login attempt: {data.get('email')}")

        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing email or password'}), 400

        user = User.query.filter_by(email=data['email']).first()
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user.is_verified:
            # Silently refresh OTP so they can verify immediately
            code = _set_otp(user, 'verify')
            db.session.commit()
            send_otp_email(user.email, user.username, code, purpose='verify')
            return jsonify({
                'error':            'Email not verified. A new code has been sent.',
                'requires_verify':  True,
                'email':            user.email,
            }), 403

        access_token = create_access_token(identity=str(user.id))
        print(f"✅ Login successful: {user.email}")
        return jsonify({
            'message':      'Login successful',
            'access_token': access_token,
            'user':         user.to_dict(),
        }), 200

    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({'error': str(e)}), 500


# ── /forgot-password ──────────────────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Body: { "email": "..." }"""
    try:
        data  = request.get_json()
        email = (data or {}).get('email', '').strip().lower()

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = User.query.filter_by(email=email).first()
        # Always return 200 — never confirm whether an email is registered
        if not user or not user.is_verified:
            return jsonify({'message': 'If that email is registered, a reset code has been sent.'}), 200

        code = _set_otp(user, 'reset')
        db.session.commit()
        send_otp_email(user.email, user.username, code, purpose='reset')
        print(f"📧 Password-reset OTP sent: {user.email}")
        return jsonify({'message': 'Reset code sent. Check your email.'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ forgot-password error: {e}")
        return jsonify({'error': str(e)}), 500


# ── /reset-password ───────────────────────────────────────────────────────────

@auth_bp.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password():
    """
    Protected by the short-lived reset_token returned from /verify-otp.
    Body: { "new_password": "..." }
    """
    try:
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        if not claims.get('reset'):
            return jsonify({'error': 'Invalid token for password reset'}), 403

        data         = request.get_json()
        new_password = (data or {}).get('new_password', '').strip()

        if not new_password or len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        user_id = int(get_jwt_identity())
        user    = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.set_password(new_password)
        db.session.commit()
        print(f"✅ Password reset: {user.email}")
        return jsonify({'message': 'Password updated successfully.'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ reset-password error: {e}")
        return jsonify({'error': str(e)}), 500


# ── /me ───────────────────────────────────────────────────────────────────────

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        user_id = int(get_jwt_identity())
        user    = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': user.to_dict()}), 200
    except Exception as e:
        print(f"❌ Get user error: {e}")
        return jsonify({'error': str(e)}), 500


# ── /logout ───────────────────────────────────────────────────────────────────

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    user_id = int(get_jwt_identity())
    print(f"✅ User {user_id} logged out")
    return jsonify({'message': 'Logged out successfully'}), 200