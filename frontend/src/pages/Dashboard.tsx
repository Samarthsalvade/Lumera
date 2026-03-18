// ─── Dashboard.tsx ────────────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import { Analysis } from '../types';
import PageShell from '../components/PageShell';

const AuthImage = ({ path, alt, className }: { path: string; alt: string; className?: string }) => {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let url: string | null = null;
    api.get(`/analysis/uploads/${path}`, { responseType: 'blob' })
      .then(res => { url = URL.createObjectURL(res.data); setSrc(url); })
      .catch(() => setSrc(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [path]);
  if (!src) return (
    <div className={`${className} bg-gradient-to-br from-purple-100 to-indigo-100 flex items-center justify-center`}>
      <svg className="w-10 h-10 text-purple-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
      </svg>
    </div>
  );
  return <img src={src} alt={alt} className={className} />;
};

const SKIN_COLORS: Record<string, { badge: string; bar: string; solid: string }> = {
  Normal:      { badge: 'bg-green-100 text-green-800',   bar: 'from-green-500 to-green-400',   solid: '#22c55e' },
  Oily:        { badge: 'bg-blue-100 text-blue-800',     bar: 'from-blue-500 to-blue-400',     solid: '#3b82f6' },
  Dry:         { badge: 'bg-orange-100 text-orange-800', bar: 'from-orange-500 to-orange-400', solid: '#f97316' },
  Combination: { badge: 'bg-purple-100 text-purple-800', bar: 'from-purple-500 to-purple-400', solid: '#a855f7' },
  Sensitive:   { badge: 'bg-red-100 text-red-800',       bar: 'from-red-500 to-red-400',       solid: '#ef4444' },
};

const QuickActions = [
  { to: '/upload', label: 'New Scan', sub: 'Analyse your skin now', bg: 'bg-purple-100 group-hover:bg-purple-200', ic: 'text-purple-600', border: 'hover:border-purple-300', icon: <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> },
  { to: '/chatbot', label: 'AI Consultant', sub: 'Chat about skincare', bg: 'bg-blue-100 group-hover:bg-blue-200', ic: 'text-blue-600', border: 'hover:border-blue-300', icon: <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg> },
  { to: '/progress', label: 'Track Progress', sub: 'View your journey', bg: 'bg-green-100 group-hover:bg-green-200', ic: 'text-green-600', border: 'hover:border-green-300', icon: <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> },
];

export const Dashboard = () => {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading]   = useState(true);
  const [user, setUser]         = useState<any>(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) setUser(JSON.parse(userData));
    api.get('/analysis/history').then(res => setAnalyses(res.data.analyses)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const formatDate = (d: string) => new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  const latestSkinType = analyses[0]?.skin_type ?? null;
  const avgConf = analyses.length ? (analyses.reduce((s, a) => s + a.confidence, 0) / analyses.length).toFixed(0) : '0';

  return (
    <PageShell>
      <div className="max-w-7xl mx-auto">
        {/* Welcome banner */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl shadow-xl p-8 mb-8 text-white">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold mb-1">Welcome back, {user?.username}</h1>
              <p className="text-purple-100 text-lg">Track your skin health journey and get personalised insights</p>
              {latestSkinType && (
                <div className="mt-3 flex items-center gap-2">
                  <span className="text-purple-200 text-base">Latest scan:</span>
                  <span className="bg-white/20 px-3 py-1 rounded-full text-base font-semibold">{latestSkinType} skin</span>
                </div>
              )}
            </div>
            <div className="flex gap-4">
              <div className="bg-white/20 backdrop-blur-sm rounded-xl px-6 py-4 text-center">
                <p className="text-sm text-purple-200 mb-1">Total Scans</p>
                <p className="text-4xl font-bold">{analyses.length}</p>
              </div>
              {analyses.length > 0 && (
                <div className="bg-white/20 backdrop-blur-sm rounded-xl px-6 py-4 text-center">
                  <p className="text-sm text-purple-200 mb-1">Avg Confidence</p>
                  <p className="text-4xl font-bold">{avgConf}%</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Quick actions */}
        <div className="grid md:grid-cols-3 gap-5 mb-8">
          {QuickActions.map(item => (
            <Link key={item.to} to={item.to}
              className={`bg-white/85 backdrop-blur-sm p-6 rounded-xl shadow-sm hover:shadow-lg transition-all duration-300 group border-2 border-transparent ${item.border}`}>
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl transition-colors ${item.bg}`}>
                  <span className={item.ic}>{item.icon}</span>
                </div>
                <div>
                  <p className="font-bold text-gray-900 text-lg">{item.label}</p>
                  <p className="text-base text-gray-500">{item.sub}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Recent analyses */}
        <div className="flex justify-between items-center mb-5">
          <h2 className="text-2xl font-bold text-gray-900">Recent Analyses</h2>
          <Link to="/upload" className="bg-purple-600 text-white px-5 py-2.5 rounded-xl hover:bg-purple-700 transition shadow font-semibold text-base">+ New Analysis</Link>
        </div>

        {loading ? (
          <div className="text-center py-16"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"/><p className="text-gray-500 mt-4 text-base">Loading your analyses...</p></div>
        ) : analyses.length === 0 ? (
          <div className="bg-white/85 backdrop-blur-sm rounded-2xl shadow-sm p-14 text-center border border-white/60">
            <div className="bg-purple-100 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-10 h-10 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">No analyses yet</h3>
            <p className="text-gray-500 mb-6 text-base">Start your skincare journey by creating your first scan.</p>
            <Link to="/upload" className="inline-block bg-purple-600 text-white px-8 py-3 rounded-xl hover:bg-purple-700 transition font-semibold text-base">Create Your First Analysis</Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {analyses.map(analysis => {
              const col = SKIN_COLORS[analysis.skin_type] ?? SKIN_COLORS['Normal'];
              return (
                <Link key={analysis.id} to={`/results/${analysis.id}`}
                  className="bg-white/85 backdrop-blur-sm rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden group border border-white/60 hover:border-purple-200">
                  <div className="relative h-48 overflow-hidden">
                    <AuthImage path={analysis.image_path} alt="Skin analysis" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"/>
                    <div className="absolute top-3 right-3 bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-full text-sm font-bold text-purple-700 shadow">{analysis.confidence}%</div>
                    <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/50 to-transparent p-3">
                      <span className={`text-sm font-semibold px-2.5 py-1 rounded-full ${col.badge}`}>{analysis.skin_type}</span>
                    </div>
                  </div>
                  <div className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-bold text-gray-900 text-base">{analysis.skin_type} Skin</h3>
                      <p className="text-sm text-gray-400">{formatDate(analysis.created_at)}</p>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div className={`bg-gradient-to-r ${col.bar} h-2 rounded-full`} style={{ width: `${analysis.confidence}%` }}/>
                    </div>
                    <p className="text-sm text-gray-400 mt-1.5">{analysis.confidence}% confidence</p>
                  </div>
                </Link>
              );
            })}
          </div>
        )}

        {analyses.length > 0 && (
          <div className="mt-10 bg-white/70 backdrop-blur-sm rounded-2xl p-7 border border-white/60">
            <h3 className="text-xl font-bold text-gray-900 mb-5">Quick Tips</h3>
            <div className="grid md:grid-cols-2 gap-5">
              {[{ title: 'Regular Scans', sub: 'Scan weekly to track changes in your skin condition' }, { title: 'Ask AI', sub: 'Chat with Lume for personalised skincare advice' }, { title: 'Track Progress', sub: 'Monitor confidence trends over time in Progress' }, { title: 'Consistency', sub: 'Stick to your routine for at least 4-6 weeks to see results' }].map((tip, i) => (
                <div key={i} className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center flex-shrink-0">
                    <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 text-base">{tip.title}</p>
                    <p className="text-sm text-gray-500 mt-0.5">{tip.sub}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </PageShell>
  );
};

export default Dashboard;