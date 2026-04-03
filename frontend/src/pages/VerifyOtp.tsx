import { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, KeyRound, Mail } from 'lucide-react';
import api from '../api/axios';
import PageShell from '../components/PageShell';

const VerifyOtp = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { email = '', purpose = 'verify' } = (location.state as any) || {};

  const [digits, setDigits]       = useState<string[]>(Array(6).fill(''));
  const [error, setError]         = useState('');
  const [info, setInfo]           = useState('');
  const [loading, setLoading]     = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => { inputRefs.current[0]?.focus(); }, []);

  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  if (!email) {
    return (
      <PageShell>
        <div className="flex items-center justify-center py-8">
          <div className="w-full max-w-md bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-white/60 p-8 text-center">
            <p className="text-gray-600 text-base mb-4">No email provided.</p>
            <Link to="/signup" className="text-purple-600 hover:underline font-semibold text-base">Go to Signup</Link>
          </div>
        </div>
      </PageShell>
    );
  }

  const handleChange = (idx: number, val: string) => {
    const ch = val.replace(/\D/g, '').slice(-1);
    const next = [...digits]; next[idx] = ch; setDigits(next);
    if (ch && idx < 5) inputRefs.current[idx + 1]?.focus();
  };

  const handleKeyDown = (idx: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !digits[idx] && idx > 0)
      inputRefs.current[idx - 1]?.focus();
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) { setDigits(pasted.split('')); inputRefs.current[5]?.focus(); }
    e.preventDefault();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const otp = digits.join('');
    if (otp.length < 6) { setError('Please enter all 6 digits'); return; }
    setError(''); setLoading(true);
    try {
      const res  = await api.post('/auth/verify-otp', { email, otp, purpose });
      const data = res.data;
      if (purpose === 'verify' || purpose === 'login') {
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        navigate('/dashboard');
        window.location.reload();
      } else {
        navigate('/reset-password', { state: { resetToken: data.reset_token } });
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Invalid OTP. Please try again.');
      setDigits(Array(6).fill(''));
      inputRefs.current[0]?.focus();
    } finally { setLoading(false); }
  };

  const handleResend = async () => {
    if (countdown > 0 || resending) return;
    setResending(true); setError('');
    try {
      await api.post('/auth/resend-otp', { email, purpose });
      setInfo('A new code has been sent to your email.');
      setCountdown(60);
      setDigits(Array(6).fill(''));
      inputRefs.current[0]?.focus();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Could not resend. Try again.');
    } finally { setResending(false); }
  };

  const icon = purpose === 'reset'
    ? <KeyRound className="w-7 h-7 text-white" strokeWidth={2} />
    : purpose === 'login'
    ? <Mail className="w-7 h-7 text-white" strokeWidth={2} />
    : <ShieldCheck className="w-7 h-7 text-white" strokeWidth={2} />;

  const title = purpose === 'reset'
    ? 'Reset Password'
    : purpose === 'login'
    ? 'Check Your Email'
    : 'Verify Your Email';

  const subtitle = purpose === 'reset'
    ? 'Enter the 6-digit reset code sent to'
    : purpose === 'login'
    ? 'Enter the 6-digit login code sent to'
    : 'Enter the 6-digit code sent to';

  const backLink = purpose === 'reset' || purpose === 'login'
    ? <Link to="/login" className="text-purple-600 hover:underline font-semibold">Back to Login</Link>
    : <Link to="/signup" className="text-purple-600 hover:underline font-semibold">Back to Signup</Link>;

  return (
    <PageShell>
      <div className="flex items-center justify-center py-8">
        <div className="w-full max-w-md bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-white/60 p-8">

          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-14 h-14 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              {icon}
            </div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
              {title}
            </h2>
            <p className="text-gray-500 mt-1 text-base">
              {subtitle}{' '}
              <span className="text-purple-700 font-semibold">{email}</span>
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            {/* 6-digit boxes */}
            <div className="flex gap-3 justify-center mb-6" onPaste={handlePaste}>
              {digits.map((d, i) => (
                <input key={i}
                  ref={el => { inputRefs.current[i] = el; }}
                  type="text" inputMode="numeric" maxLength={1} value={d}
                  onChange={e => handleChange(i, e.target.value)}
                  onKeyDown={e => handleKeyDown(i, e)}
                  className={`w-12 h-14 text-center text-xl font-bold rounded-xl border-2 transition
                    focus:outline-none focus:ring-2 focus:ring-purple-300
                    ${d ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 bg-white text-gray-700'}`}
                />
              ))}
            </div>

            {error && <div className="bg-red-50 text-red-600 border border-red-200 p-3 rounded-xl mb-4 text-base text-center">{error}</div>}
            {info && !error && <div className="bg-green-50 text-green-700 border border-green-200 p-3 rounded-xl mb-4 text-base text-center">{info}</div>}

            <button type="submit" disabled={loading || digits.join('').length < 6}
              className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white
                         py-3.5 rounded-xl hover:from-purple-700 hover:to-indigo-700
                         transition font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? 'Verifying...' : purpose === 'reset' ? 'Verify & Continue' : purpose === 'login' ? 'Sign In' : 'Verify Email'}
            </button>
          </form>

          {/* Resend */}
          <div className="mt-5 text-center">
            <span className="text-gray-500 text-base">Didn't get a code? </span>
            {countdown > 0
              ? <span className="text-base text-purple-400 font-medium">Resend in {countdown}s</span>
              : <button onClick={handleResend} disabled={resending}
                  className="text-base text-purple-600 font-semibold hover:underline disabled:opacity-50">
                  {resending ? 'Sending...' : 'Resend Code'}
                </button>
            }
          </div>

          <p className="text-center mt-4 text-gray-500 text-base">{backLink}</p>
        </div>
      </div>
    </PageShell>
  );
};

export default VerifyOtp;