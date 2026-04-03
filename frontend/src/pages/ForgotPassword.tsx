import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { KeyRound } from 'lucide-react';
import api from '../api/axios';
import PageShell from '../components/PageShell';

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [email, setEmail]     = useState('');
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      await api.post('/auth/forgot-password', { email });
      navigate('/verify-otp', { state: { email, purpose: 'reset' } });
    } catch (err: any) {
      if ((err.response?.status ?? 0) >= 500) {
        setError('Something went wrong. Please try again.');
      } else {
        navigate('/verify-otp', { state: { email, purpose: 'reset' } });
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
              <KeyRound className="w-7 h-7 text-white" strokeWidth={2} />
            </div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
              Forgot Password
            </h2>
            <p className="text-gray-500 mt-1 text-base">
              Enter your email and we'll send you a reset code.
            </p>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 border border-red-200 p-3 rounded-xl mb-5 text-base">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-gray-700 font-semibold mb-2 text-base">Email address</label>
              <input type="email" required value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base
                           focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white" />
            </div>

            <button type="submit" disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white
                         py-3.5 rounded-xl hover:from-purple-700 hover:to-indigo-700
                         transition font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? 'Sending code...' : 'Send Reset Code'}
            </button>
          </form>

          <p className="text-center mt-6 text-gray-600 text-base">
            Remembered it?{' '}
            <Link to="/login" className="text-purple-600 hover:underline font-semibold">Back to Login</Link>
          </p>
        </div>
      </div>
    </PageShell>
  );
};

export default ForgotPassword;