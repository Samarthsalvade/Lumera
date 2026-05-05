import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link, useSearchParams } from 'react-router-dom';
import { LogIn, Mail, Info } from 'lucide-react';
import api from '../api/axios';
import PageShell from '../components/PageShell';
import { useAuth } from '../context/AuthContext';

type Tab = 'password' | 'otp';

const Login = () => {
  const navigate      = useNavigate();
  const location      = useLocation();
  const [searchParams] = useSearchParams();
  const { login }     = useAuth();

  const [tab, setTab]           = useState<Tab>('password');
  const [form, setForm]         = useState({ email: '', password: '' });
  const [otpEmail, setOtpEmail] = useState('');
  const [error, setError]       = useState('');
  const [info, setInfo]         = useState('');
  const [loading, setLoading]   = useState(false);

  // Message passed via router state (e.g. from signup redirect)
  useEffect(() => {
    const msg = (location.state as any)?.message;
    if (msg) setInfo(msg);
  }, [location.state]);

  // Reason passed via query param when AuthContext auto-logs out
  const logoutReason = searchParams.get('reason');

  const switchTab = (t: Tab) => { setTab(t); setError(''); setInfo(''); };

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setInfo(''); setLoading(true);
    try {
      const res  = await api.post('/auth/login', form);
      const data = res.data;
      // Use AuthContext.login() — it sets localStorage + React state in one shot.
      // No window.location.reload() needed; AuthContext triggers a re-render.
      login(data.access_token, data.user);
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      const data = err.response?.data || {};
      if (data.requires_verify) {
        navigate('/verify-otp', { state: { email: form.email, purpose: 'verify' } });
      } else {
        setError(data.error || 'Login failed');
      }
    } finally { setLoading(false); }
  };

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      await api.post('/auth/send-login-otp', { email: otpEmail });
      navigate('/verify-otp', { state: { email: otpEmail, purpose: 'login' } });
    } catch (err: any) {
      if ((err.response?.status ?? 0) >= 500) {
        setError('Something went wrong. Please try again.');
      } else {
        navigate('/verify-otp', { state: { email: otpEmail, purpose: 'login' } });
      }
    } finally { setLoading(false); }
  };

  return (
    <PageShell>
      <div className="flex items-center justify-center py-8">
        <div className="w-full max-w-md bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-white/60 p-8">

          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-14 h-14 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <LogIn className="w-7 h-7 text-white" strokeWidth={2} />
            </div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
              Welcome Back
            </h2>
            <p className="text-gray-500 mt-1 text-base">Sign in to your Luméra account</p>
          </div>

          {/* Auto-logout reason banners */}
          {logoutReason === 'inactivity' && (
            <div className="flex items-start gap-2.5 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mb-5">
              <Info className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
              <p className="text-amber-700 text-sm leading-snug">
                You were signed out due to inactivity. Please log in again.
              </p>
            </div>
          )}
          {logoutReason === 'expired' && (
            <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-5">
              <Info className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
              <p className="text-red-600 text-sm leading-snug">
                Your session expired. Please log in again.
              </p>
            </div>
          )}

          {/* Cold start notice — only shown when no logout reason */}
          {!logoutReason && (
            <div className="flex items-start gap-2.5 bg-purple-50 border border-purple-100 rounded-xl px-4 py-3 mb-6">
              <Info className="w-4 h-4 text-purple-400 mt-0.5 shrink-0" />
              <p className="text-purple-700 text-sm leading-snug">
                First attempt may fail while the server wakes up — just try again if it does.
              </p>
            </div>
          )}

          {/* Tab switcher */}
          <div className="flex rounded-xl bg-gray-100 p-1 mb-6 gap-1">
            <button onClick={() => switchTab('password')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-base font-semibold transition-all
                ${tab === 'password'
                  ? 'bg-white text-purple-700 shadow-sm'
                  : 'text-gray-500 hover:text-purple-600'}`}>
              <LogIn className="w-4 h-4" />
              Password
            </button>
            <button onClick={() => switchTab('otp')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-base font-semibold transition-all
                ${tab === 'otp'
                  ? 'bg-white text-purple-700 shadow-sm'
                  : 'text-gray-500 hover:text-purple-600'}`}>
              <Mail className="w-4 h-4" />
              Email Code
            </button>
          </div>

          {/* Password tab */}
          {tab === 'password' && (
            <form onSubmit={handlePasswordLogin} className="space-y-5">
              <div>
                <label className="block text-gray-700 font-semibold mb-2 text-base">Email</label>
                <input type="email" required value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                  placeholder="you@example.com"
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base
                             focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white" />
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-gray-700 font-semibold text-base">Password</label>
                  <Link to="/forgot-password" className="text-sm text-purple-600 hover:underline font-medium">
                    Forgot password?
                  </Link>
                </div>
                <input type="password" required value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base
                             focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white" />
              </div>

              {info  && <div className="bg-green-50 text-green-700 border border-green-200 p-3 rounded-xl text-base">{info}</div>}
              {error && <div className="bg-red-50 text-red-600 border border-red-200 p-3 rounded-xl text-base">{error}</div>}

              <button type="submit" disabled={loading}
                className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white
                           py-3.5 rounded-xl hover:from-purple-700 hover:to-indigo-700
                           transition font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed">
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>
          )}

          {/* OTP tab */}
          {tab === 'otp' && (
            <form onSubmit={handleSendOtp} className="space-y-5">
              <p className="text-gray-500 text-base">
                Enter your email and we'll send a 6-digit code — no password needed.
              </p>
              <div>
                <label className="block text-gray-700 font-semibold mb-2 text-base">Email</label>
                <input type="email" required value={otpEmail}
                  onChange={e => setOtpEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base
                             focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white" />
              </div>

              {error && <div className="bg-red-50 text-red-600 border border-red-200 p-3 rounded-xl text-base">{error}</div>}

              <button type="submit" disabled={loading}
                className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white
                           py-3.5 rounded-xl hover:from-purple-700 hover:to-indigo-700
                           transition font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed">
                {loading ? 'Sending code...' : 'Send Login Code'}
              </button>
            </form>
          )}

          <p className="text-center mt-6 text-gray-600 text-base">
            No account?{' '}
            <Link to="/signup" className="text-purple-600 hover:underline font-semibold">Create one</Link>
          </p>
        </div>
      </div>
    </PageShell>
  );
};

export default Login;