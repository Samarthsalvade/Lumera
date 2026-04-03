import { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, Eye, EyeOff } from 'lucide-react';
import api from '../api/axios';
import PageShell from '../components/PageShell';

const ResetPassword = () => {
  const location   = useLocation();
  const navigate   = useNavigate();
  const { resetToken } = (location.state as any) || {};

  const [password, setPassword] = useState('');
  const [confirm, setConfirm]   = useState('');
  const [showPass, setShowPass] = useState(false);
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  if (!resetToken) {
    return (
      <PageShell>
        <div className="flex items-center justify-center py-8">
          <div className="w-full max-w-md bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-white/60 p-8 text-center">
            <p className="text-gray-600 text-base mb-4">
              Invalid session. Please restart the reset flow.
            </p>
            <Link to="/forgot-password" className="text-purple-600 hover:underline font-semibold text-base">
              Forgot Password
            </Link>
          </div>
        </div>
      </PageShell>
    );
  }

  const strength = Math.min(
    (password.length >= 6 ? 1 : 0) +
    (/[A-Z]/.test(password) ? 1 : 0) +
    (/[0-9]/.test(password) ? 1 : 0) +
    (/[^A-Za-z0-9]/.test(password) ? 1 : 0), 4
  );
  const strengthColor = strength >= 3 ? 'bg-green-500' : strength === 2 ? 'bg-yellow-400' : 'bg-red-400';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 6) { setError('Password must be at least 6 characters'); return; }
    if (password !== confirm)  { setError('Passwords do not match'); return; }
    setLoading(true);
    try {
      await api.post(
        '/auth/reset-password',
        { new_password: password },
        { headers: { Authorization: `Bearer ${resetToken}` } }
      );
      navigate('/login', { state: { message: 'Password updated! Please log in.' } });
    } catch (err: any) {
      setError(err.response?.data?.error || 'Could not reset password. Try again.');
    } finally { setLoading(false); }
  };

  return (
    <PageShell>
      <div className="flex items-center justify-center py-8">
        <div className="w-full max-w-md bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-white/60 p-8">

          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-14 h-14 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <ShieldCheck className="w-7 h-7 text-white" strokeWidth={2} />
            </div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
              New Password
            </h2>
            <p className="text-gray-500 mt-1 text-base">Choose a strong password for your account.</p>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 border border-red-200 p-3 rounded-xl mb-5 text-base">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-gray-700 font-semibold mb-2 text-base">New Password</label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'} required minLength={6}
                  value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="min. 6 characters"
                  className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-xl text-base
                             focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white" />
                <button type="button" onClick={() => setShowPass(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-purple-600">
                  {showPass
                    ? <EyeOff className="w-5 h-5" />
                    : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {/* Strength bar */}
              {password.length > 0 && (
                <div className="flex gap-1 mt-2">
                  {[1,2,3,4].map(n => (
                    <div key={n}
                      className={`flex-1 h-1.5 rounded-full transition-colors
                        ${strength >= n ? strengthColor : 'bg-gray-200'}`} />
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="block text-gray-700 font-semibold mb-2 text-base">Confirm Password</label>
              <input
                type={showPass ? 'text' : 'password'} required
                value={confirm} onChange={e => setConfirm(e.target.value)}
                placeholder="repeat your password"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base
                           focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white" />
            </div>

            <button type="submit" disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white
                         py-3.5 rounded-xl hover:from-purple-700 hover:to-indigo-700
                         transition font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>
    </PageShell>
  );
};

export default ResetPassword;