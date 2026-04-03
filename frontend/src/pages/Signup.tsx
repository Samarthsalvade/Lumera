import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import api from '../api/axios';
import PageShell from '../components/PageShell';

const Signup = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '', email: '', password: '', confirmPassword: '',
  });
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setFormData({ ...formData, [e.target.name]: e.target.value });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match'); return;
    }
    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters'); return;
    }
    setLoading(true);
    try {
      await api.post('/auth/register', {
        username: formData.username,
        email:    formData.email,
        password: formData.password,
      });
      navigate('/verify-otp', { state: { email: formData.email, purpose: 'verify' } });
    } catch (err: any) {
      const msg = err.response?.data?.error || 'Signup failed. Please try again.';
      if (err.response?.status === 200) {
        navigate('/verify-otp', { state: { email: formData.email, purpose: 'verify' } });
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const field = (label: string, name: string, type: string, placeholder: string) => (
    <div>
      <label className="block text-gray-700 font-semibold mb-2 text-base">{label}</label>
      <input
        type={type} name={name}
        value={(formData as any)[name]}
        onChange={handleChange}
        required
        placeholder={placeholder}
        className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base
                   focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
      />
    </div>
  );

  return (
    <PageShell>
      <div className="flex items-center justify-center py-8">
        <div className="w-full max-w-md bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-white/60 p-8">
          <div className="text-center mb-8">
            <div className="w-14 h-14 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <UserPlus className="w-7 h-7 text-white" strokeWidth={2} />
            </div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
              Create Account
            </h2>
            <p className="text-gray-500 mt-1 text-base">Start your Luméra skin journey</p>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 border border-red-200 p-3 rounded-xl mb-5 text-base">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {field('Username',         'username',        'text',     'johndoe')}
            {field('Email',            'email',           'email',    'you@example.com')}
            {field('Password',         'password',        'password', '••••••••')}
            {field('Confirm Password', 'confirmPassword', 'password', '••••••••')}
            <button type="submit" disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white
                         py-3.5 rounded-xl hover:from-purple-700 hover:to-indigo-700
                         transition font-semibold text-base disabled:opacity-50
                         disabled:cursor-not-allowed mt-2">
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <p className="text-center mt-6 text-gray-600 text-base">
            Already have an account?{' '}
            <Link to="/login" className="text-purple-600 hover:underline font-semibold">Login</Link>
          </p>
        </div>
      </div>
    </PageShell>
  );
};

export default Signup;