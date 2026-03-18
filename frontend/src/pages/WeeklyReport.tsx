import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import PageShell from '../components/PageShell';

/* ─── Types ─────────────────────────────────────────────── */
interface ConcernDetail {
  concern_type: string;
  label: string;
  confidence: number;
  severity: string;
  notes: string;
  annotated_image_b64: string | null;
}
interface ScanDetail {
  id: number;
  date: string;           // "Mar 17, 2026 06:10"
  skin_type: string;
  confidence: number;
  normalized_image_b64: string | null;
  concerns: ConcernDetail[];
}
interface ConcernSummary { label: string; avg: number; count: number; }
interface Summary {
  user: string; period: string; total_scans: number;
  avg_confidence: number; dominant_type: string;
  trend: number | null;
  concerns: Record<string, ConcernSummary>;
  analyses: ScanDetail[];
  skin_narrative: string;
}

/* ─── Constants ─────────────────────────────────────────── */
const SKIN_COLORS: Record<string, string> = {
  Normal: '#22c55e', Oily: '#3b82f6', Dry: '#f97316',
  Combination: '#a855f7', Sensitive: '#ef4444',
};
const SKIN_BADGE: Record<string, string> = {
  Normal: 'bg-green-100 text-green-800', Oily: 'bg-blue-100 text-blue-800',
  Dry: 'bg-orange-100 text-orange-800', Combination: 'bg-purple-100 text-purple-800',
  Sensitive: 'bg-red-100 text-red-800',
};
const SEV_COLORS: Record<string, string> = {
  severe: '#ef4444', moderate: '#f59e0b', mild: '#22c55e',
};

/* ─── Icons ─────────────────────────────────────────────── */
const DownloadIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
  </svg>
);
const CloseIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
  </svg>
);

/* ─── Scan Detail Modal ─────────────────────────────────── */
const ScanModal = ({ scan, onClose }: { scan: ScanDetail; onClose: () => void }) => {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const col = SKIN_COLORS[scan.skin_type] ?? '#a855f7';
  const activeConcerns = scan.concerns.filter(c => c.confidence > 0.15);

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(4px)' }}
      onClick={e => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-[fadeUp_0.2s_ease]">
        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 sticky top-0 bg-white z-10">
          <div>
            <h3 className="font-bold text-lg text-gray-900">{scan.date}</h3>
            <span className={`text-sm px-2.5 py-0.5 rounded-full font-medium ${SKIN_BADGE[scan.skin_type] ?? 'bg-gray-100 text-gray-700'}`}>
              {scan.skin_type}
            </span>
          </div>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-100 transition text-gray-500">
            <CloseIcon />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Face photo + confidence */}
          <div className="flex gap-4 items-start">
            {scan.normalized_image_b64 ? (
              <img
                src={`data:image/png;base64,${scan.normalized_image_b64}`}
                alt="Face scan"
                className="w-32 h-32 rounded-xl object-cover border-2 shadow"
                style={{ borderColor: col }}
              />
            ) : (
              <div className="w-32 h-32 rounded-xl bg-gray-100 flex items-center justify-center text-gray-400 text-sm border">
                No photo
              </div>
            )}
            <div className="flex-1">
              <p className="text-sm text-gray-500 mb-1">Skin type confidence</p>
              <div className="flex items-center gap-3 mb-3">
                <div className="flex-1 bg-gray-100 rounded-full h-3">
                  <div
                    className="h-3 rounded-full transition-all duration-700"
                    style={{ width: `${scan.confidence}%`, background: col }}
                  />
                </div>
                <span className="font-bold text-lg" style={{ color: col }}>{scan.confidence}%</span>
              </div>
              <Link
                to={`/results/${scan.id}`}
                className="inline-block text-sm text-purple-600 hover:text-purple-800 font-medium underline"
              >
                View full results →
              </Link>
            </div>
          </div>

          {/* Concerns with annotated images */}
          {activeConcerns.length > 0 ? (
            <div>
              <h4 className="font-semibold text-gray-800 mb-3">Detected Concerns</h4>
              <div className="space-y-4">
                {activeConcerns.map(c => {
                  const sevColor = SEV_COLORS[c.severity] ?? '#a855f7';
                  return (
                    <div key={c.concern_type} className="flex gap-3 p-3 bg-gray-50 rounded-xl border border-gray-100">
                      {/* Annotated zone image */}
                      {c.annotated_image_b64 ? (
                        <img
                          src={`data:image/png;base64,${c.annotated_image_b64}`}
                          alt={c.label}
                          className="w-20 h-20 rounded-lg object-cover flex-shrink-0 border"
                          style={{ borderColor: sevColor }}
                        />
                      ) : (
                        <div className="w-20 h-20 rounded-lg bg-gray-200 flex-shrink-0 flex items-center justify-center text-xs text-gray-400">
                          Zone
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-gray-900 text-sm">{c.label}</span>
                          <span
                            className="text-xs px-2 py-0.5 rounded-full font-semibold text-white"
                            style={{ background: sevColor }}
                          >
                            {c.severity}
                          </span>
                          <span className="text-xs text-gray-500 ml-auto">{Math.round(c.confidence * 100)}%</span>
                        </div>
                        {/* Confidence bar */}
                        <div className="w-full bg-gray-200 rounded-full h-1.5 mb-2">
                          <div
                            className="h-1.5 rounded-full"
                            style={{ width: `${Math.min(c.confidence * 100, 100)}%`, background: sevColor }}
                          />
                        </div>
                        {c.notes && (
                          <p className="text-xs text-gray-600 leading-relaxed line-clamp-2">{c.notes}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="text-center py-4 text-gray-400 text-sm bg-gray-50 rounded-xl">
              No significant concerns detected in this scan.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─── Animated Number ───────────────────────────────────── */
const AnimatedNumber = ({ value, suffix = '' }: { value: number; suffix?: string }) => {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = 0;
    const end = value;
    const duration = 800;
    const step = (end / duration) * 16;
    const timer = setInterval(() => {
      start = Math.min(start + step, end);
      setDisplay(Math.round(start * 10) / 10);
      if (start >= end) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [value]);
  return <>{display}{suffix}</>;
};

/* ─── Main Component ─────────────────────────────────────── */
const WeeklyReport = () => {
  const [summary, setSummary]         = useState<Summary | null>(null);
  const [loading, setLoading]         = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError]             = useState('');
  const [selectedScan, setSelectedScan] = useState<ScanDetail | null>(null);
  const [hoveredBar, setHoveredBar]   = useState<number | null>(null);

  useEffect(() => {
    api.get('/report/summary')
      .then(res => setSummary(res.data.summary))
      .catch(() => setError('Could not load report data.'))
      .finally(() => setLoading(false));
  }, []);

  const downloadPDF = async () => {
    setDownloading(true);
    try {
      const res  = await api.get('/report/weekly', { responseType: 'blob' });
      const url  = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href  = url;
      link.download = `lumera_report_${new Date().toISOString().slice(0, 10)}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('Failed to generate PDF. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  if (loading) return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"/>
    </div>
  );

  /* Sort analyses oldest → newest for the chart */
  const chartScans = summary ? [...summary.analyses].reverse() : [];

  return (
    <PageShell>
      <div className="min-h-[calc(100vh-4rem)] py-8 px-4 bg-gradient-to-br from-purple-50 via-white to-indigo-50">
        <div className="max-w-4xl mx-auto">

          {/* Header */}
          <div className="mb-7 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-purple-600 hover:underline mb-3 text-base">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><polyline points="15 18 9 12 15 6"/></svg>
                Back to Dashboard
              </Link>
              <h1 className="text-3xl font-bold">Weekly Report</h1>
              <p className="text-gray-500 text-base mt-1">
                {summary ? `Your skin health summary for ${summary.period}` : 'Your skin health summary for the past 7 days'}
              </p>
            </div>
            {summary && (
              <button onClick={downloadPDF} disabled={downloading}
                className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-5 py-3 rounded-xl hover:from-purple-700 hover:to-indigo-700 transition font-medium text-base shadow-sm disabled:opacity-50 self-start">
                <DownloadIcon/>
                {downloading ? 'Generating...' : 'Download PDF'}
              </button>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-base mb-5">{error}</div>
          )}

          {!summary ? (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-14 text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">No scans this week</h3>
              <p className="text-gray-500 mb-6 text-base">Take at least one scan to generate your weekly report.</p>
              <Link to="/upload" className="inline-block bg-purple-600 text-white px-8 py-3 rounded-xl hover:bg-purple-700 transition font-medium text-base">New Scan</Link>
            </div>
          ) : (
            <>
              {/* ── Stats tiles ───────────────────────────────── */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-7">
                {[
                  { label: 'Total Scans',    value: summary.total_scans,       suffix: '',  color: 'text-purple-600' },
                  { label: 'Avg Confidence', value: summary.avg_confidence,    suffix: '%', color: 'text-green-600' },
                  { label: 'Primary Type',   value: null,                       suffix: '',  color: 'text-indigo-600', text: summary.dominant_type },
                  {
                    label: 'Trend vs Earlier',
                    value: null, suffix: '',
                    color: summary.trend !== null ? (summary.trend >= 0 ? 'text-green-600' : 'text-red-500') : 'text-gray-400',
                    text: summary.trend !== null ? `${summary.trend >= 0 ? '+' : ''}${summary.trend}%` : '—',
                  },
                ].map((s, i) => (
                  <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 text-center hover:shadow-md transition-shadow duration-200">
                    <p className="text-sm text-gray-500 mb-1">{s.label}</p>
                    <p className={`text-2xl font-bold ${s.color}`}>
                      {s.text ?? <AnimatedNumber value={s.value as number} suffix={s.suffix}/>}
                    </p>
                  </div>
                ))}
              </div>

              {/* ── AI Narrative Summary ──────────────────────── */}
              {summary.skin_narrative && (
                <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-100 rounded-2xl p-6 mb-7">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-xl bg-purple-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                      </svg>
                    </div>
                    <div>
                      <h2 className="font-bold text-gray-900 mb-2 text-base">Skin Health Summary</h2>
                      <p className="text-gray-700 text-sm leading-relaxed">{summary.skin_narrative}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Interactive Confidence Chart ──────────────── */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-7">
                <h2 className="text-xl font-bold mb-1">Scans of This Week</h2>
                <p className="text-sm text-gray-400 mb-5">
                  Every scan shown individually · coloured by skin type · <span className="text-purple-500 font-medium">click any bar</span> to see photos &amp; concerns
                </p>

                {chartScans.length < 1 ? (
                  <p className="text-gray-400 text-base text-center py-8">No scan data available.</p>
                ) : (
                  <>
                    <div className="relative">
                      {/* Grid lines */}
                      <div className="absolute inset-0 pointer-events-none" style={{ left: '36px' }}>
                        {[75, 50, 25].map(pct => (
                          <div key={pct} className="absolute w-full border-t border-dashed border-gray-100"
                            style={{ bottom: `${pct}%` }}>
                            <span className="absolute -left-9 -top-2.5 text-xs text-gray-300">{pct}%</span>
                          </div>
                        ))}
                      </div>

                      <div className="flex items-end gap-1.5 overflow-x-auto pb-1" style={{ height: '220px', paddingLeft: '36px' }}>
                        {/* Y axis label */}
                        <div className="absolute left-0 flex flex-col justify-between text-xs text-gray-300 pointer-events-none"
                          style={{ height: '220px', top: 0 }}>
                          <span>100%</span>
                          <span>0%</span>
                        </div>

                        {chartScans.map((scan, i) => {
                          const col     = SKIN_COLORS[scan.skin_type] ?? '#a855f7';
                          const pct     = Math.max(scan.confidence, 5);
                          const isHover = hoveredBar === i;
                          const hasImg  = !!scan.normalized_image_b64;

                          return (
                            <div
                              key={scan.id}
                              className="flex flex-col items-center group relative cursor-pointer flex-shrink-0"
                              style={{ minWidth: '36px', flex: '1 1 36px', maxWidth: '64px', height: '100%' }}
                              onMouseEnter={() => setHoveredBar(i)}
                              onMouseLeave={() => setHoveredBar(null)}
                              onClick={() => setSelectedScan(scan)}
                            >
                              {/* Tooltip */}
                              <div className={`absolute bottom-full mb-2 left-1/2 -translate-x-1/2
                                bg-gray-900 text-white text-xs rounded-xl py-2.5 px-3.5
                                transition-all duration-150 whitespace-nowrap z-20 pointer-events-none shadow-2xl
                                ${isHover ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'}`}>
                                <div className="font-semibold text-sm mb-0.5">{scan.date}</div>
                                <div style={{ color: col }} className="font-medium">{scan.skin_type}</div>
                                <div className="text-gray-300">{scan.confidence}% confidence</div>
                                {scan.concerns.filter(c => c.confidence > 0.15).length > 0 && (
                                  <div className="text-gray-400 mt-1 border-t border-gray-700 pt-1">
                                    {scan.concerns.filter(c => c.confidence > 0.15).map(c => c.label).join(', ')}
                                  </div>
                                )}
                                <div className="text-purple-300 mt-1 text-xs">Click to view photos</div>
                                {/* Arrow */}
                                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"/>
                              </div>

                              {/* Face thumbnail on hover */}
                              {hasImg && isHover && (
                                <div className="absolute z-10 pointer-events-none"
                                  style={{ bottom: `calc(${pct}% + 8px)`, left: '50%', transform: 'translateX(-50%)' }}>
                                  <img
                                    src={`data:image/png;base64,${scan.normalized_image_b64}`}
                                    alt=""
                                    className="w-10 h-10 rounded-full border-2 shadow-lg object-cover"
                                    style={{ borderColor: col }}
                                  />
                                </div>
                              )}

                              {/* Bar */}
                              <div className="absolute bottom-0 left-0 right-0 flex items-end justify-center" style={{ height: '100%' }}>
                                <div
                                  className="w-full rounded-t-lg relative overflow-hidden"
                                  style={{
                                    height: `${pct}%`,
                                    background: col,
                                    minHeight: '6px',
                                    transform: isHover ? 'scaleY(1.04) scaleX(1.06)' : 'scaleY(1) scaleX(1)',
                                    transformOrigin: 'bottom',
                                    transition: 'transform 0.15s ease, filter 0.15s ease, box-shadow 0.15s ease',
                                    filter: isHover ? 'brightness(1.12)' : 'brightness(1)',
                                    boxShadow: isHover ? `0 0 12px ${col}66` : 'none',
                                  }}
                                >
                                  {/* Shine */}
                                  <div className="absolute inset-0 bg-gradient-to-b from-white/25 to-transparent rounded-t-lg"/>
                                </div>
                              </div>

                              {/* Confidence label above bar */}
                              <div
                                className={`absolute text-xs font-semibold transition-opacity duration-150 ${isHover ? 'opacity-100' : 'opacity-0'}`}
                                style={{ bottom: `calc(${pct}% + 4px)`, left: '50%', transform: 'translateX(-50%)', whiteSpace: 'nowrap', color: col }}
                              >
                                {scan.confidence}%
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* X-axis date labels — show only every nth to avoid clutter */}
                    <div className="flex gap-1.5 mt-2 overflow-x-auto" style={{ paddingLeft: '36px' }}>
                      {chartScans.map((scan, i) => {
                        const showLabel = chartScans.length <= 10 || i % Math.ceil(chartScans.length / 10) === 0;
                        const dayPart   = scan.date.split(',')[0]; // "Mar 17"
                        const timePart  = scan.date.split(' ').pop(); // "06:10"
                        return (
                          <div key={i} className="text-center flex-shrink-0 cursor-pointer"
                            style={{ minWidth: '36px', flex: '1 1 36px', maxWidth: '64px' }}
                            onClick={() => setSelectedScan(scan)}>
                            {showLabel ? (
                              <>
                                <div className="text-xs text-gray-500 font-medium leading-tight">{dayPart}</div>
                                <div className="text-xs text-gray-400 leading-tight">{timePart}</div>
                              </>
                            ) : (
                              <div className="w-full h-1 mt-2 rounded-full bg-gray-100"/>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Skin type legend */}
                    <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t border-gray-100">
                      {Object.entries(SKIN_COLORS).map(([type, col]) => (
                        <span key={type} className="flex items-center gap-1.5 text-sm text-gray-600">
                          <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: col }}/>
                          {type}
                        </span>
                      ))}
                      <span className="text-sm text-gray-400 ml-auto hidden sm:block">← scroll if many scans</span>
                    </div>
                  </>
                )}
              </div>

              {/* ── Concerns with photos ─────────────────────── */}
              {Object.keys(summary.concerns).length > 0 && (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-7">
                  <h2 className="text-xl font-bold mb-2">Recurring Concerns</h2>
                  <p className="text-sm text-gray-400 mb-5">Aggregated across all scans this week</p>
                  <div className="space-y-5">
                    {Object.entries(summary.concerns).map(([key, c]) => {
                      const sev    = c.avg > 0.55 ? 'severe' : c.avg > 0.25 ? 'moderate' : 'mild';
                      const sevCol = SEV_COLORS[sev];
                      const sevLabel = sev.charAt(0).toUpperCase() + sev.slice(1);

                      /* Collect annotated images for this concern from all scans */
                      const concernImages = summary.analyses
                        .flatMap(a => a.concerns)
                        .filter(cn => cn.concern_type === key && cn.annotated_image_b64 && cn.confidence > 0.15)
                        .slice(0, 3);

                      return (
                        <div key={key} className="group">
                          <div className="flex justify-between items-center mb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-base font-semibold text-gray-900">{c.label}</span>
                              <span
                                className="text-xs px-2.5 py-0.5 rounded-full font-semibold text-white"
                                style={{ background: sevCol }}
                              >
                                {sevLabel}
                              </span>
                            </div>
                            <span className="text-sm text-gray-500">{c.count} scan{c.count > 1 ? 's' : ''} · {Math.round(c.avg * 100)}% avg</span>
                          </div>

                          {/* Progress bar — animates on mount */}
                          <div className="w-full bg-gray-100 rounded-full h-2.5 mb-3 overflow-hidden">
                            <div
                              className="h-2.5 rounded-full transition-all duration-1000 ease-out"
                              style={{ width: `${Math.min(c.avg * 100, 100)}%`, background: sevCol }}
                            />
                          </div>

                          {/* Zone annotation thumbnails */}
                          {concernImages.length > 0 && (
                            <div className="flex gap-2">
                              {concernImages.map((cn, idx) => (
                                <button
                                  key={idx}
                                  className="relative group/img focus:outline-none"
                                  onClick={() => {
                                    const parentScan = summary.analyses.find(a =>
                                      a.concerns.some(ac => ac.concern_type === key && ac.annotated_image_b64 === cn.annotated_image_b64)
                                    );
                                    if (parentScan) setSelectedScan(parentScan);
                                  }}
                                >
                                  <img
                                    src={`data:image/png;base64,${cn.annotated_image_b64}`}
                                    alt={cn.label}
                                    className="w-14 h-14 rounded-lg object-cover border-2 transition-all duration-150 hover:scale-110 hover:shadow-md"
                                    style={{ borderColor: sevCol }}
                                  />
                                  <div className="absolute inset-0 rounded-lg bg-black/0 group-hover/img:bg-black/10 transition-all"/>
                                </button>
                              ))}
                              <span className="text-xs text-gray-400 self-end ml-1">
                                Tap image to open scan
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ── Scan Log ─────────────────────────────────── */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-7">
                <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                  <h2 className="text-xl font-bold">Scan Log</h2>
                  <span className="text-sm text-gray-400">{summary.total_scans} total scan{summary.total_scans !== 1 ? 's' : ''} this week</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        {['Face', 'Date', 'Skin Type', 'Confidence', ''].map(h => (
                          <th key={h} className="px-4 py-3.5 text-left text-sm font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {summary.analyses.map(a => {
                        const col = SKIN_COLORS[a.skin_type] ?? '#a855f7';
                        return (
                          <tr key={a.id} className="hover:bg-purple-50/40 transition cursor-pointer" onClick={() => setSelectedScan(a)}>
                            <td className="px-4 py-3">
                              {a.normalized_image_b64 ? (
                                <img
                                  src={`data:image/png;base64,${a.normalized_image_b64}`}
                                  alt=""
                                  className="w-10 h-10 rounded-full object-cover border-2 shadow-sm"
                                  style={{ borderColor: col }}
                                />
                              ) : (
                                <div className="w-10 h-10 rounded-full bg-gray-100 border flex items-center justify-center text-xs text-gray-400">?</div>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">{a.date}</td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <span className={`px-2.5 py-1 rounded-full text-sm font-medium ${SKIN_BADGE[a.skin_type] ?? 'bg-gray-100 text-gray-700'}`}>
                                {a.skin_type}
                              </span>
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <div className="flex items-center gap-2">
                                <div className="w-16 bg-gray-100 rounded-full h-2">
                                  <div className="h-2 rounded-full" style={{ width: `${a.confidence}%`, background: col }}/>
                                </div>
                                <span className="text-sm text-gray-700 font-medium">{a.confidence}%</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap" onClick={e => e.stopPropagation()}>
                              <Link to={`/results/${a.id}`} className="text-purple-600 hover:text-purple-800 font-medium text-sm">View →</Link>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* ── Download CTA ─────────────────────────────── */}
              <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-7 text-white text-center">
                <h3 className="text-xl font-bold mb-2">Save your full report</h3>
                <p className="text-purple-200 text-base mb-5">Download a formatted PDF with your scan data, concerns, and trends.</p>
                <button onClick={downloadPDF} disabled={downloading}
                  className="inline-flex items-center gap-2 bg-white text-purple-700 px-8 py-3 rounded-xl font-semibold text-base hover:bg-purple-50 transition disabled:opacity-50">
                  <DownloadIcon/>
                  {downloading ? 'Generating PDF...' : 'Download PDF Report'}
                </button>
              </div>
            </>
          )}
        </div>

        {/* ── Scan Detail Modal ─────────────────────────────── */}
        {selectedScan && (
          <ScanModal scan={selectedScan} onClose={() => setSelectedScan(null)}/>
        )}

        {/* Keyframe for modal animation */}
        <style>{`
          @keyframes fadeUp {
            from { opacity: 0; transform: translateY(16px); }
            to   { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </div>
    </PageShell>
    );
};

export default WeeklyReport;