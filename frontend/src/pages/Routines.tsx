import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import PageShell from '../components/PageShell';

interface RoutineStep {
  id: number; order: number; product_type: string;
  instruction: string; duration_seconds?: number; key_ingredient?: string;
}
interface Routine {
  id: number; routine_type: 'morning' | 'night'; name: string;
  description?: string; is_active: boolean; steps: RoutineStep[]; created_at: string;
}
interface Analysis { id: number; skin_type: string; created_at: string; }

const SunIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
    <circle cx="12" cy="12" r="4"/>
    <path strokeLinecap="round" d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
  </svg>
);
const MoonIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
  </svg>
);

const Routines = () => {
  const [routines, setRoutines]   = useState<Routine[]>([]);
  const [analyses, setAnalyses]   = useState<Analysis[]>([]);
  const [expanded, setExpanded]   = useState<number | null>(null);
  const [showGen, setShowGen]     = useState(false);
  const [genType, setGenType]     = useState<'morning' | 'night'>('morning');
  const [selectedScan, setSelectedScan] = useState<number | null>(null);
  const [generating, setGenerating]     = useState(false);
  const [error, setError]               = useState('');
  const [loading, setLoading]           = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/routines').then(r => setRoutines(r.data.routines || [])),
      api.get('/analysis/history').then(r => setAnalyses(r.data.analyses || [])),
    ]).finally(() => setLoading(false));
  }, []);

  const generate = async () => {
    setGenerating(true); setError('');
    try {
      const res = await api.post('/routines/generate', {
        routine_type: genType, analysis_id: selectedScan ?? undefined,
      });
      setRoutines(prev => [res.data.routine, ...prev]);
      setShowGen(false); setSelectedScan(null); setExpanded(res.data.routine.id);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Generation failed. Check your GROQ_API_KEY.');
    } finally { setGenerating(false); }
  };

  const remove = async (id: number) => {
    if (!confirm('Delete this routine?')) return;
    try {
      await api.delete(`/routines/${id}`);
      setRoutines(prev => prev.filter(r => r.id !== id));
      if (expanded === id) setExpanded(null);
    } catch { setError('Failed to delete.'); }
  };

  const activate = async (id: number, type: string) => {
    try {
      await api.post(`/routines/${id}/activate`);
      setRoutines(prev => prev.map(r =>
        r.routine_type === type ? { ...r, is_active: r.id === id } : r
      ));
    } catch { setError('Failed to activate.'); }
  };

  const fmtDuration = (s?: number) =>
    !s ? '' : s < 60 ? `${s}s` : `${Math.floor(s / 60)}m${s % 60 ? ` ${s % 60}s` : ''}`;

  const morning = routines.filter(r => r.routine_type === 'morning');
  const night   = routines.filter(r => r.routine_type === 'night');

  if (loading) return (
    <PageShell>
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"/>
      </div>
    </PageShell>
  );

  return (
    <PageShell>
      <div className="max-w-4xl mx-auto">

        {/* Header */}
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-purple-600 hover:underline text-base font-medium mb-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><polyline points="15 18 9 12 15 6"/></svg>
              Dashboard
            </Link>
            <h1 className="text-3xl font-bold text-gray-900 mt-1">My Routines</h1>
            <p className="text-gray-500 text-lg mt-1">AI-generated morning and night skincare routines</p>
          </div>
          <button
            onClick={() => { setShowGen(true); setError(''); }}
            className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-3 rounded-xl hover:from-purple-700 hover:to-indigo-700 transition font-semibold shadow-md flex items-center gap-2 self-start text-base"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>
            Generate Routine
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-base mb-5">{error}</div>
        )}

        {/* Generator panel */}
        {showGen && (
          <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border border-white/60 p-7 mb-7">
            <h2 className="font-bold text-xl text-gray-900 mb-6">Generate AI Routine</h2>
            <div className="mb-5">
              <p className="text-base font-semibold text-gray-700 mb-3">Routine Type</p>
              <div className="flex gap-3">
                {(['morning', 'night'] as const).map(t => (
                  <button key={t} onClick={() => setGenType(t)}
                    className={`flex-1 py-3.5 rounded-xl border-2 text-base font-semibold transition flex items-center justify-center gap-2 capitalize
                      ${genType === t
                        ? 'border-purple-600 bg-purple-50 text-purple-700'
                        : 'border-gray-200 text-gray-600 hover:border-purple-200 bg-white'}`}>
                    {t === 'morning' ? <SunIcon /> : <MoonIcon />}
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div className="mb-6">
              <p className="text-base font-semibold text-gray-700 mb-3">Based on scan (optional)</p>
              <select
                value={selectedScan ?? ''}
                onChange={e => setSelectedScan(e.target.value ? +e.target.value : null)}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white text-gray-700"
              >
                <option value="">— Use general skin advice —</option>
                {analyses.map(a => (
                  <option key={a.id} value={a.id}>
                    {a.skin_type} · {new Date(a.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-3">
              <button onClick={generate} disabled={generating}
                className="flex-1 bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-3.5 rounded-xl hover:from-purple-700 hover:to-indigo-700 transition font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed">
                {generating
                  ? <span className="flex items-center justify-center gap-2">
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>Generating...
                    </span>
                  : 'Generate'}
              </button>
              <button onClick={() => setShowGen(false)}
                className="flex-1 border border-gray-200 text-gray-600 py-3.5 rounded-xl hover:bg-gray-50 transition font-semibold text-base bg-white">
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Empty state */}
        {routines.length === 0 && !showGen && (
          <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border border-white/60 p-16 text-center">
            <div className="w-16 h-16 bg-purple-100 rounded-2xl flex items-center justify-center mx-auto mb-5">
              <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
              </svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">No routines yet</h3>
            <p className="text-gray-500 mb-6 text-base">Generate a personalised AI routine based on your skin scans.</p>
            <button onClick={() => setShowGen(true)}
              className="bg-purple-600 text-white px-8 py-3 rounded-xl hover:bg-purple-700 transition font-semibold text-base">
              Generate Your First Routine
            </button>
          </div>
        )}

        {/* Routine groups */}
        {[
          { label: 'Morning Routines', icon: <SunIcon />, list: morning, accent: 'text-amber-500' },
          { label: 'Night Routines',   icon: <MoonIcon />, list: night,  accent: 'text-indigo-500' },
        ].map(({ label, icon, list, accent }) =>
          list.length > 0 && (
            <div key={label} className="mb-8">
              <div className="flex items-center gap-2.5 mb-4">
                <span className={accent}>{icon}</span>
                <h2 className="text-lg font-bold text-gray-700">{label}</h2>
                <span className="text-sm text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{list.length}</span>
              </div>
              <div className="space-y-3">
                {list.map(r => (
                  <div key={r.id}
                    className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-sm border border-white/60 overflow-hidden hover:shadow-md hover:border-purple-200 transition-all duration-200">
                    <button
                      onClick={() => setExpanded(expanded === r.id ? null : r.id)}
                      className="w-full px-6 py-5 flex items-center justify-between text-left"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2.5 flex-wrap">
                          <h3 className="font-semibold text-gray-900 text-base">{r.name}</h3>
                          {r.is_active && (
                            <span className="text-sm bg-green-100 text-green-700 px-2.5 py-0.5 rounded-full font-semibold flex-shrink-0">
                              Active
                            </span>
                          )}
                        </div>
                        {r.description && (
                          <p className="text-sm text-gray-500 mt-1 truncate">{r.description}</p>
                        )}
                        <p className="text-xs text-gray-400 mt-1">{r.steps.length} steps</p>
                      </div>
                      <svg
                        className={`w-5 h-5 text-gray-400 flex-shrink-0 ml-4 transition-transform duration-200 ${expanded === r.id ? 'rotate-180' : ''}`}
                        fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
                      </svg>
                    </button>

                    {expanded === r.id && (
                      <div className="border-t border-gray-100 px-6 py-5">
                        <div className="space-y-3 mb-5">
                          {r.steps.map(step => (
                            <div key={step.id} className="flex gap-4 bg-purple-50/70 rounded-xl p-4">
                              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                                {step.order}
                              </div>
                              <div className="flex-1">
                                <p className="font-semibold text-gray-900 text-base">{step.product_type}</p>
                                <p className="text-sm text-gray-600 mt-1 leading-relaxed">{step.instruction}</p>
                                <div className="flex gap-3 mt-2 flex-wrap">
                                  {step.duration_seconds && (
                                    <span className="text-sm text-purple-600 font-medium">{fmtDuration(step.duration_seconds)}</span>
                                  )}
                                  {step.key_ingredient && (
                                    <span className="text-sm text-indigo-600 font-medium">{step.key_ingredient}</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="flex gap-3">
                          {!r.is_active && (
                            <button onClick={() => activate(r.id, r.routine_type)}
                              className="flex-1 bg-green-600 text-white py-3 rounded-xl text-base hover:bg-green-700 transition font-semibold">
                              Set Active
                            </button>
                          )}
                          <button onClick={() => remove(r.id)}
                            className="flex-1 bg-red-50 text-red-600 border border-red-200 py-3 rounded-xl text-base hover:bg-red-100 transition font-semibold">
                            Delete
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        )}
      </div>
    </PageShell>
  );
};

export default Routines;