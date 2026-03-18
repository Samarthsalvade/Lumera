import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import { Analysis } from '../types';
import PageShell from '../components/PageShell';

const SKIN_COLORS: Record<string, { bg: string; text: string; bar: string; light: string }> = {
  Normal:      { bg: 'bg-green-100',  text: 'text-green-800',  bar: '#22c55e', light: '#dcfce7' },
  Oily:        { bg: 'bg-blue-100',   text: 'text-blue-800',   bar: '#3b82f6', light: '#dbeafe' },
  Dry:         { bg: 'bg-orange-100', text: 'text-orange-800', bar: '#f97316', light: '#ffedd5' },
  Combination: { bg: 'bg-purple-100', text: 'text-purple-800', bar: '#a855f7', light: '#f3e8ff' },
  Sensitive:   { bg: 'bg-red-100',    text: 'text-red-800',    bar: '#ef4444', light: '#fee2e2' },
};

const DEFAULT_COLOR = { bg: 'bg-gray-100', text: 'text-gray-700', bar: '#9ca3af', light: '#f3f4f6' };

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}
function getFirstDayOfWeek(year: number, month: number) {
  return new Date(year, month, 1).getDay();
}
function isoDate(d: string) {
  return d.slice(0, 10);
}

const Progress = () => {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading]   = useState(true);
  const [calYear,  setCalYear]  = useState(new Date().getFullYear());
  const [calMonth, setCalMonth] = useState(new Date().getMonth());
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  useEffect(() => {
    api.get('/analysis/history')
      .then(res => setAnalyses(res.data.analyses))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const formatDate  = (d: string) => new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  const formatTime  = (d: string) => new Date(d).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  const avgConf    = analyses.length ? (analyses.reduce((s, a) => s + a.confidence, 0) / analyses.length).toFixed(1) : '0';
  const latestConf = analyses[0]?.confidence ?? 0;
  const prevConf   = analyses[1]?.confidence ?? null;
  const confTrend  = prevConf !== null ? latestConf - prevConf : null;
  const primaryType = (() => {
    if (!analyses.length) return 'N/A';
    const counts: Record<string, number> = {};
    analyses.forEach(a => { counts[a.skin_type] = (counts[a.skin_type] || 0) + 1; });
    return Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);
  })();

  const scansByDate: Record<string, Analysis[]> = {};
  analyses.forEach(a => {
    const d = isoDate(a.created_at);
    if (!scansByDate[d]) scansByDate[d] = [];
    scansByDate[d].push(a);
  });

  const daysInMonth    = getDaysInMonth(calYear, calMonth);
  const firstDayOfWeek = getFirstDayOfWeek(calYear, calMonth);
  const MONTH_NAMES  = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  const DAY_NAMES    = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

  const prevMonth = () => { if (calMonth === 0) { setCalYear(y => y-1); setCalMonth(11); } else setCalMonth(m => m-1); setSelectedDay(null); };
  const nextMonth = () => { if (calMonth === 11) { setCalYear(y => y+1); setCalMonth(0); } else setCalMonth(m => m+1); setSelectedDay(null); };

  const selectedScans = selectedDay ? (scansByDate[selectedDay] ?? []) : [];

  if (loading) return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600" />
    </div>
  );

  return (
    <PageShell>
      <div className="min-h-[calc(100vh-4rem)] py-8 px-4 bg-gradient-to-br from-purple-50 via-white to-indigo-50">
        <div className="max-w-6xl mx-auto">

          <div className="mb-7">
            <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-purple-600 hover:underline mb-4 text-base">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><polyline points="15 18 9 12 15 6"/></svg>
              Back to Dashboard
            </Link>
            <h1 className="text-3xl font-bold mb-1">Progress Tracker</h1>
            <p className="text-gray-500 text-lg">Monitor your skin health journey over time</p>
          </div>

          {analyses.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-sm p-14 text-center">
              <div className="bg-purple-100 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-10 h-10 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                </svg>
              </div>
              <p className="text-gray-600 text-lg mb-4">No analysis data yet. Start tracking!</p>
              <Link to="/upload" className="inline-block bg-purple-600 text-white px-6 py-3 rounded-xl hover:bg-purple-700 transition font-medium text-base">
                Create First Analysis
              </Link>
            </div>
          ) : (
            <>
              {/* Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-7">
                {[
                  { label: 'Total Scans',    value: analyses.length, color: 'text-purple-600' },
                  { label: 'Avg Confidence', value: `${avgConf}%`,   color: 'text-green-600' },
                  { label: 'Primary Type',   value: primaryType,     color: 'text-indigo-600' },
                  {
                    label: 'Confidence Trend',
                    value: confTrend !== null ? `${confTrend >= 0 ? '+' : ''}${confTrend.toFixed(1)}%` : '—',
                    color: confTrend !== null ? (confTrend >= 0 ? 'text-green-600' : 'text-red-500') : 'text-gray-400',
                    sub: 'vs previous scan',
                  },
                ].map((s, i) => (
                  <div key={i} className="bg-white rounded-xl shadow-sm p-5">
                    <p className="text-gray-500 text-sm mb-1">{s.label}</p>
                    <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
                    {s.sub && <p className="text-xs text-gray-400 mt-1">{s.sub}</p>}
                  </div>
                ))}
              </div>

              {/* Calendar + Scan details — fixed height side panel with internal scroll */}
              <div className="grid lg:grid-cols-3 gap-6 mb-7">

                {/* Calendar */}
                <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm p-6">
                  <div className="flex items-center justify-between mb-5">
                    <h2 className="text-xl font-bold">{MONTH_NAMES[calMonth]} {calYear}</h2>
                    <div className="flex gap-2">
                      <button onClick={prevMonth} className="p-2 rounded-lg hover:bg-gray-100 transition">
                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><polyline points="15 18 9 12 15 6"/></svg>
                      </button>
                      <button onClick={nextMonth} className="p-2 rounded-lg hover:bg-gray-100 transition">
                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><polyline points="9 18 15 12 9 6"/></svg>
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-7 mb-2">
                    {DAY_NAMES.map(d => (
                      <div key={d} className="text-center text-sm font-medium text-gray-400 py-1">{d}</div>
                    ))}
                  </div>

                  <div className="grid grid-cols-7 gap-1">
                    {Array.from({ length: firstDayOfWeek }).map((_, i) => <div key={`e${i}`} />)}
                    {Array.from({ length: daysInMonth }).map((_, i) => {
                      const day     = i + 1;
                      const dateStr = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                      const scans   = scansByDate[dateStr] ?? [];
                      const isToday = dateStr === isoDate(new Date().toISOString());
                      const isSelected = selectedDay === dateStr;
                      const mainType = scans[0]?.skin_type;
                      const dotColor = mainType ? (SKIN_COLORS[mainType] ?? DEFAULT_COLOR).bar : null;

                      return (
                        <button key={day}
                          onClick={() => setSelectedDay(isSelected ? null : dateStr)}
                          className={`relative aspect-square rounded-xl flex flex-col items-center justify-center transition-all text-sm font-medium
                            ${isSelected ? 'ring-2 ring-purple-500 bg-purple-50' : ''}
                            ${isToday && !isSelected ? 'ring-2 ring-purple-300' : ''}
                            ${scans.length > 0 ? 'cursor-pointer hover:bg-purple-50' : 'cursor-default'}
                            ${!scans.length && !isToday ? 'text-gray-400' : 'text-gray-900'}
                          `}
                          style={scans.length > 0 && !isSelected ? { background: dotColor ? `${dotColor}18` : undefined } : {}}
                        >
                          <span>{day}</span>
                          {scans.length > 0 && (
                            <span className="w-1.5 h-1.5 rounded-full mt-0.5" style={{ background: dotColor ?? '#a855f7' }} />
                          )}
                          {scans.length > 1 && (
                            <span className="absolute top-1 right-1 text-xs font-bold text-purple-600">{scans.length}</span>
                          )}
                        </button>
                      );
                    })}
                  </div>

                  <div className="mt-4 pt-4 border-t border-gray-100 flex items-center gap-4 flex-wrap">
                    <span className="text-sm text-gray-500">Scan days are highlighted by skin type:</span>
                    {Object.entries(SKIN_COLORS).slice(0, 3).map(([type, col]) => (
                      <span key={type} className="flex items-center gap-1.5 text-sm text-gray-600">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ background: col.bar }} />
                        {type}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Selected day panel — fixed height, scans scroll internally */}
                <div className="bg-white rounded-2xl shadow-sm p-6 flex flex-col" style={{ minHeight: '420px' }}>
                  {!selectedDay ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-center">
                      <svg className="w-12 h-12 text-purple-200 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                        <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                      </svg>
                      <p className="text-gray-400 text-base">Select a highlighted day to see scans</p>
                    </div>
                  ) : selectedScans.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-center">
                      <p className="text-gray-400 text-base">No scans on {new Date(selectedDay + 'T12:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}</p>
                    </div>
                  ) : (
                    <div className="flex flex-col h-full">
                      {/* Fixed header */}
                      <div className="mb-3 flex-shrink-0">
                        <h3 className="text-lg font-bold text-gray-900">
                          {new Date(selectedDay + 'T12:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                        </h3>
                        <p className="text-sm text-gray-500">{selectedScans.length} scan{selectedScans.length > 1 ? 's' : ''}</p>
                      </div>

                      {/* Scrollable scan list — max 3 cards visible, rest scroll */}
                      <div className="flex-1 overflow-y-auto space-y-3 pr-1" style={{ maxHeight: '340px', scrollbarWidth: 'thin' }}>
                        {selectedScans.map(scan => {
                          const col = SKIN_COLORS[scan.skin_type] ?? DEFAULT_COLOR;
                          return (
                            <Link key={scan.id} to={`/results/${scan.id}`}
                              className="block rounded-xl p-3 border border-gray-100 hover:border-purple-200 hover:shadow-sm transition"
                              style={{ background: col.light }}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className={`text-sm font-semibold px-2 py-0.5 rounded-full ${col.bg} ${col.text}`}>
                                  {scan.skin_type}
                                </span>
                                <span className="text-sm text-gray-500">{formatTime(scan.created_at)}</span>
                              </div>
                              <div className="flex items-center gap-2 mt-2">
                                <div className="flex-1 bg-white/60 rounded-full h-1.5">
                                  <div className="h-1.5 rounded-full" style={{ width: `${scan.confidence}%`, background: col.bar }} />
                                </div>
                                <span className="text-sm font-medium text-gray-700">{scan.confidence}%</span>
                              </div>
                              <p className="text-sm text-purple-600 mt-2 font-medium">View results →</p>
                            </Link>
                          );
                        })}
                      </div>

                      {/* Scroll hint if more than 3 scans */}
                      {selectedScans.length > 3 && (
                        <p className="text-xs text-gray-400 text-center mt-2 flex-shrink-0">
                          Scroll to see all {selectedScans.length} scans
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Skin type distribution */}
              <div className="bg-white rounded-2xl shadow-sm p-6 mb-7">
                <h2 className="text-xl font-bold mb-5">Skin Type Distribution</h2>
                <div className="space-y-4">
                  {Object.entries(
                    analyses.reduce((acc, a) => {
                      acc[a.skin_type] = (acc[a.skin_type] || 0) + 1;
                      return acc;
                    }, {} as Record<string, number>)
                  ).sort((a, b) => b[1] - a[1]).map(([type, count]) => {
                    const pct = Math.round((count / analyses.length) * 100);
                    const col = SKIN_COLORS[type] ?? DEFAULT_COLOR;
                    return (
                      <div key={type}>
                        <div className="flex justify-between text-base mb-1.5">
                          <span className={`font-medium ${col.text}`}>{type}</span>
                          <span className="text-gray-500">{count} scan{count > 1 ? 's' : ''} · {pct}%</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2.5">
                          <div className="h-2.5 rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: col.bar }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* History table */}
              <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
                <div className="p-6 border-b border-gray-100">
                  <h2 className="text-xl font-bold">Scan History</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        {['Date', 'Skin Type', 'Confidence', 'Action'].map(h => (
                          <th key={h} className="px-6 py-3.5 text-left text-sm font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {analyses.map(a => {
                        const col = SKIN_COLORS[a.skin_type] ?? DEFAULT_COLOR;
                        return (
                          <tr key={a.id} className="hover:bg-gray-50 transition">
                            <td className="px-6 py-4 text-base text-gray-900 whitespace-nowrap">{formatDate(a.created_at)}</td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-full text-sm font-medium ${col.bg} ${col.text}`}>{a.skin_type}</span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center gap-2">
                                <div className="w-24 bg-gray-100 rounded-full h-2">
                                  <div className="h-2 rounded-full" style={{ width: `${a.confidence}%`, background: col.bar }} />
                                </div>
                                <span className="text-base text-gray-700">{a.confidence}%</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-base">
                              <Link to={`/results/${a.id}`} className="text-purple-600 hover:text-purple-800 font-medium">View</Link>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </PageShell>
    );
};

export default Progress;