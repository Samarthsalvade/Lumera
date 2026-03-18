import { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { Analysis } from '../types';
import PageShell from '../components/PageShell';

interface Concern {
  concern_type: string; confidence: number; severity: string;
  notes: string; annotated_image_b64: string;
}
interface DynamicProduct {
  product_name: string; brand: string; description: string;
  key_ingredients: string[]; price_range: string; concern_tags: string[];
  amazon_url: string; amazon_image_url: string;
}

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
    <div className={`${className} bg-gradient-to-br from-purple-50 to-indigo-100 flex items-center justify-center`}>
      <svg className="w-12 h-12 text-purple-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
      </svg>
    </div>
  );
  return <img src={src} alt={alt} className={className} />;
};

// Product image — shows real image if available, nothing if not (no blank box)
const ProductImageTile = ({ imageUrl, productName, brand }: { imageUrl: string; productName: string; brand: string }) => {
  const [imgFailed, setImgFailed] = useState(false);
  const isRealImage = imageUrl?.startsWith('https://') && !imgFailed;

  const initial = (brand || productName || 'P')[0].toUpperCase();
  const colors = ['from-purple-100 to-indigo-100', 'from-blue-100 to-cyan-100', 'from-green-100 to-teal-100', 'from-orange-100 to-amber-100', 'from-pink-100 to-rose-100'];
  const idx = (brand.charCodeAt(0) || 0) % colors.length;

  if (isRealImage) {
    return (
      <div className="w-full h-36 rounded-xl overflow-hidden bg-gray-50 flex items-center justify-center">
        <img
          src={imageUrl}
          alt={productName}
          onError={() => setImgFailed(true)}
          className="w-full h-full object-contain p-2"
        />
      </div>
    );
  }

  // No real image — show a compact brand initial strip instead of a tall blank box
  return (
    <div className={`w-full h-14 rounded-xl bg-gradient-to-r ${colors[idx]} flex items-center gap-3 px-4`}>
      <span className="text-2xl font-bold text-gray-400">{initial}</span>
      <span className="text-sm text-gray-500 font-medium truncate">{brand}</span>
    </div>
  );
};

const SKIN_COLORS: Record<string, string> = {
  Normal: 'bg-green-100 text-green-800', Oily: 'bg-blue-100 text-blue-800',
  Dry: 'bg-orange-100 text-orange-800', Combination: 'bg-purple-100 text-purple-800',
  Sensitive: 'bg-red-100 text-red-800',
};

const CONCERN_META: Record<string, { label: string; color: string; icon: JSX.Element }> = {
  acne: { label: 'Acne', color: 'bg-red-50 border-red-200 text-red-800', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/></svg> },
  redness: { label: 'Redness', color: 'bg-pink-50 border-pink-200 text-pink-800', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> },
  dark_circles: { label: 'Dark Circles', color: 'bg-indigo-50 border-indigo-200 text-indigo-800', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><circle cx="12" cy="12" r="10"/><path d="M8 12a4 4 0 008 0"/></svg> },
  eye_bags: { label: 'Eye Bags', color: 'bg-slate-50 border-slate-200 text-slate-800', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg> },
  blackheads: { label: 'Blackheads', color: 'bg-gray-50 border-gray-300 text-gray-800', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><circle cx="12" cy="12" r="1"/><circle cx="6" cy="8" r="1"/><circle cx="18" cy="8" r="1"/><circle cx="6" cy="16" r="1"/><circle cx="18" cy="16" r="1"/><circle cx="12" cy="4" r="1"/><circle cx="12" cy="20" r="1"/></svg> },
  lip_hyperpigmentation: { label: 'Lip Hyperpigmentation', color: 'bg-rose-50 border-rose-200 text-rose-800', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path d="M12 6c-4 0-7 2.5-7 5 0 3 3.5 7 7 7s7-4 7-7c0-2.5-3-5-7-5z"/></svg> },
  texture: { label: 'Texture Issues', color: 'bg-amber-50 border-amber-200 text-amber-800', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path d="M3 6h18M3 12h18M3 18h18"/></svg> },
  hyperpigmentation: { label: 'Hyperpigmentation', color: 'bg-yellow-50 border-yellow-200 text-yellow-800', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg> },
  dryness: { label: 'Dryness', color: 'bg-sky-50 border-sky-200 text-sky-800', icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path d="M12 2.69l5.66 5.66a8 8 0 11-11.31 0z"/></svg> },
};

const PRICE_BADGE: Record<string, string> = {
  budget: 'bg-green-100 text-green-700', mid: 'bg-blue-100 text-blue-700', premium: 'bg-purple-100 text-purple-700',
};

const ConcernImage = ({ annotatedB64, fallbackB64, alt }: { annotatedB64: string; fallbackB64: string; alt: string }) => {
  const src = annotatedB64 ? `data:image/png;base64,${annotatedB64}` : fallbackB64 ? `data:image/png;base64,${fallbackB64}` : null;
  if (!src) return <div className="w-full aspect-square bg-gray-100 rounded-xl flex items-center justify-center"><span className="text-gray-400 text-sm">No image</span></div>;
  return <img src={src} alt={alt} className="w-full aspect-square object-cover rounded-xl border border-gray-200" />;
};

// Horizontal slider with prev/next arrows
const HorizontalSlider = ({ children, itemWidth = 260 }: { children: React.ReactNode[]; itemWidth?: number }) => {
  const trackRef = useRef<HTMLDivElement>(null);
  const [canLeft, setCanLeft]   = useState(false);
  const [canRight, setCanRight] = useState(true);

  const updateArrows = () => {
    const t = trackRef.current;
    if (!t) return;
    setCanLeft(t.scrollLeft > 4);
    setCanRight(t.scrollLeft < t.scrollWidth - t.clientWidth - 4);
  };

  const scroll = (dir: 'left' | 'right') => {
    trackRef.current?.scrollBy({ left: dir === 'left' ? -itemWidth : itemWidth, behavior: 'smooth' });
  };

  useEffect(() => {
    const t = trackRef.current;
    if (!t) return;
    t.addEventListener('scroll', updateArrows, { passive: true });
    updateArrows();
    return () => t.removeEventListener('scroll', updateArrows);
  }, [children]);

  return (
    <div className="relative">
      {canLeft && (
        <button onClick={() => scroll('left')}
          className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-3 z-10 w-8 h-8 bg-white border border-gray-200 rounded-full shadow flex items-center justify-center hover:bg-gray-50 transition">
          <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><polyline points="15 18 9 12 15 6"/></svg>
        </button>
      )}
      <div ref={trackRef}
        className="flex gap-4 overflow-x-auto pb-2 scroll-smooth"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
        <style>{`.no-scrollbar::-webkit-scrollbar{display:none}`}</style>
        {children}
      </div>
      {canRight && (
        <button onClick={() => scroll('right')}
          className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-3 z-10 w-8 h-8 bg-white border border-gray-200 rounded-full shadow flex items-center justify-center hover:bg-gray-50 transition">
          <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><polyline points="9 18 15 12 9 6"/></svg>
        </button>
      )}
    </div>
  );
};

const Results = () => {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [analysis, setAnalysis]     = useState<Analysis | null>(null);
  const [concerns, setConcerns]     = useState<Concern[]>([]);
  const [loading, setLoading]       = useState(true);
  const [activeTab, setActiveTab]   = useState<'concerns' | 'products' | 'routine'>('concerns');

  const [dynProducts, setDynProducts]           = useState<DynamicProduct[]>([]);
  const [productsLoading, setProductsLoading]   = useState(false);
  const [productsLoaded, setProductsLoaded]     = useState(false);

  const [routineType, setRoutineType]   = useState<'morning' | 'night'>('morning');
  const [generating, setGenerating]     = useState(false);
  const [generatedRoutine, setGenerated] = useState<any>(null);
  const [routineError, setRoutineError] = useState('');

  useEffect(() => {
    api.get(`/analysis/result/${id}`)
      .then(res => { setAnalysis(res.data.analysis); setConcerns(res.data.concerns || []); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  const loadProducts = async () => {
    if (productsLoaded || !analysis) return;
    setProductsLoading(true);
    try {
      const activeConcerns = concerns.filter(c => c.confidence > 0.15).map(c => ({
        concern_type: c.concern_type, severity: c.severity,
      }));
      const res = await api.post('/products/recommend', {
        skin_type: analysis.skin_type,
        concerns:  activeConcerns,
        count:     5,
      });
      setDynProducts(res.data.products || []);
      setProductsLoaded(true);
    } catch {
      setDynProducts([]);
      setProductsLoaded(true);
    } finally {
      setProductsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'products' && analysis && !productsLoaded) loadProducts();
  }, [activeTab, analysis]);

  const generateRoutine = async () => {
    setGenerating(true); setRoutineError(''); setGenerated(null);
    try {
      const res = await api.post('/routines/generate', { routine_type: routineType, analysis_id: Number(id) });
      setGenerated(res.data.routine);
    } catch (err: any) {
      setRoutineError(err.response?.data?.error || 'Generation failed. Check your GROQ_API_KEY in .env');
    } finally { setGenerating(false); }
  };

  const fmtDuration = (s?: number) => !s ? '' : s < 60 ? `${s}s` : `${Math.floor(s/60)}m${s%60 ? ` ${s%60}s` : ''}`;
  const formatDate  = (d: string) => new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });

  if (loading) return <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"/></div>;
  if (!analysis) return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
      <div className="text-center"><h2 className="text-2xl font-bold mb-4">Analysis not found</h2>
        <Link to="/dashboard" className="text-purple-600 hover:underline text-base">Back to Dashboard</Link></div>
    </div>
  );

  let recommendations: string[] = [];
  try { recommendations = typeof analysis.recommendations === 'string' ? JSON.parse(analysis.recommendations) : analysis.recommendations; } catch {}

  const badgeColor     = SKIN_COLORS[analysis.skin_type] ?? 'bg-gray-100 text-gray-700';
  const activeConcerns = concerns.filter(c => c.confidence > 0.15);

  const tabs = [
    ...(activeConcerns.length > 0 ? [{ key: 'concerns', label: `Concerns (${activeConcerns.length})` }] : []),
    { key: 'products', label: 'Products' },
    { key: 'routine',  label: 'Build Routine' },
  ] as { key: 'concerns' | 'products' | 'routine'; label: string }[];

  return (
  <PageShell>
    <div className="min-h-[calc(100vh-4rem)] py-8 px-4 bg-gradient-to-br from-purple-50 via-white to-indigo-50">
      <div className="max-w-5xl mx-auto">

        <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-purple-600 hover:underline mb-6 text-base">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><polyline points="15 18 9 12 15 6"/></svg>
          Back to Dashboard
        </Link>

        {/* Image + result card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-6">
          <div className="md:flex">
            <div className="md:w-2/5 bg-gradient-to-br from-purple-50 to-indigo-50">
              {analysis.normalized_image_b64 ? (
                <div className="p-5 space-y-3">
                  <p className="text-sm font-semibold text-purple-500 uppercase tracking-widest text-center">Normalised Face</p>
                  <img src={`data:image/png;base64,${analysis.normalized_image_b64}`} alt="Normalised" className="w-full rounded-xl border-2 border-purple-200 shadow-sm"/>
                  {analysis.face_detection_confidence && <p className="text-sm text-center text-green-600">Face detected · {analysis.face_detection_confidence}% confidence</p>}
                  <p className="text-sm font-semibold text-gray-400 uppercase tracking-widest text-center mt-2">Original</p>
                  <AuthImage path={analysis.image_path} alt="Original" className="w-full rounded-xl border border-gray-200 opacity-75"/>
                </div>
              ) : (
                <AuthImage path={analysis.image_path} alt="Analysis" className="w-full h-full object-cover min-h-64"/>
              )}
            </div>

            <div className="md:w-3/5 p-8">
              <h2 className="text-3xl font-bold mb-1 bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">Analysis Results</h2>
              <p className="text-gray-400 text-base mb-5">{formatDate(analysis.created_at)}</p>
              <div className="flex items-center gap-3 mb-4">
                <span className="text-4xl font-bold text-purple-600">{analysis.skin_type}</span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${badgeColor}`}>{analysis.skin_type}</span>
              </div>
              <div className="mb-5">
                <div className="flex justify-between text-base mb-1"><span className="text-gray-500">Confidence</span><span className="font-semibold text-purple-600">{analysis.confidence}%</span></div>
                <div className="w-full bg-gray-100 rounded-full h-3"><div className="bg-gradient-to-r from-purple-600 to-indigo-500 h-3 rounded-full transition-all duration-700" style={{ width: `${analysis.confidence}%` }}/></div>
                {analysis.confidence < 60 && <p className="text-sm text-amber-600 mt-1.5">Low confidence — try a clearer, well-lit front-facing photo.</p>}
              </div>
              {activeConcerns.length > 0 && (
                <div className="mb-5">
                  <p className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-2">Detected Concerns</p>
                  <div className="flex flex-wrap gap-2">
                    {activeConcerns.map(c => {
                      const meta = CONCERN_META[c.concern_type];
                      if (!meta) return null;
                      const dotCls = c.severity === 'severe' ? 'bg-red-500' : c.severity === 'moderate' ? 'bg-yellow-400' : 'bg-green-400';
                      return (
                        <span key={c.concern_type} className={`text-sm px-2.5 py-1 rounded-full border font-medium flex items-center gap-1.5 ${meta.color}`}>
                          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotCls}`}/>{meta.label} · {c.severity}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
              <p className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-2">Recommendations</p>
              <ul className="space-y-2">
                {recommendations.map((r, i) => (
                  <li key={i} className="flex gap-2 bg-purple-50 p-3 rounded-lg text-base text-gray-700">
                    <span className="text-purple-500 font-bold flex-shrink-0">{i + 1}.</span>{r}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-6">
          <div className="flex border-b border-gray-100 overflow-x-auto">
            {tabs.map(tab => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`flex-1 py-4 px-4 text-base font-medium whitespace-nowrap transition
                  ${activeTab === tab.key ? 'border-b-2 border-purple-600 text-purple-600 bg-purple-50/50' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'}`}>
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-6">

            {/* Concerns */}
            {activeTab === 'concerns' && (
              <div className="space-y-5">
                {activeConcerns.length === 0 ? (
                  <p className="text-gray-500 text-base text-center py-6">No significant concerns detected.</p>
                ) : activeConcerns.map(c => {
                  const meta = CONCERN_META[c.concern_type] ?? { label: c.concern_type, color: 'bg-gray-50 border-gray-200 text-gray-700', icon: <span/> };
                  const dotCls = c.severity === 'severe' ? 'bg-red-500' : c.severity === 'moderate' ? 'bg-yellow-400' : 'bg-green-400';
                  const sevBg  = c.severity === 'severe' ? 'bg-red-100 text-red-700' : c.severity === 'moderate' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700';
                  return (
                    <div key={c.concern_type} className={`rounded-xl border p-4 ${meta.color}`}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2.5">
                          {meta.icon}
                          <span className="font-semibold text-lg">{meta.label}</span>
                          <span className={`text-sm px-2 py-0.5 rounded-full font-medium flex items-center gap-1 ${sevBg}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${dotCls}`}/>{c.severity}
                          </span>
                        </div>
                        <span className="text-base font-semibold tabular-nums">{Math.round(c.confidence * 100)}%</span>
                      </div>
                      <div className="w-full bg-white/60 rounded-full h-2 mb-3">
                        <div className="h-2 rounded-full bg-current opacity-60 transition-all duration-700" style={{ width: `${c.confidence * 100}%` }}/>
                      </div>
                      <div className="flex gap-4 mt-1">
                        <div className="flex-shrink-0 w-32">
                          <ConcernImage annotatedB64={c.annotated_image_b64} fallbackB64={analysis.normalized_image_b64 ?? ''} alt={`${meta.label} zone`}/>
                          <p className="text-sm text-center mt-1 opacity-60">Analyzed zone</p>
                        </div>
                        <div className="flex-1 flex items-start"><p className="text-sm leading-relaxed opacity-90">{c.notes}</p></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Products — horizontal sliding cards */}
            {activeTab === 'products' && (
              <div>
                {productsLoading ? (
                  <div className="flex flex-col items-center justify-center py-12 gap-3">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600"/>
                    <p className="text-gray-500 text-base">Finding the best products for your skin...</p>
                  </div>
                ) : dynProducts.length === 0 && productsLoaded ? (
                  <div className="text-center py-10">
                    <p className="text-gray-500 text-base mb-4">Could not load products. Check your GROQ_API_KEY.</p>
                    <button onClick={() => { setProductsLoaded(false); loadProducts(); }} className="text-purple-600 hover:underline text-base">Try again</button>
                  </div>
                ) : (
                  <div className="px-2">
                    <HorizontalSlider itemWidth={272}>
                      {dynProducts.map((p, i) => (
                        <div key={i} className="flex-shrink-0 w-64 border border-gray-100 rounded-xl overflow-hidden hover:border-purple-200 hover:shadow-md transition flex flex-col">
                          <div className="p-3 pb-0">
                            <ProductImageTile imageUrl={p.amazon_image_url} productName={p.product_name} brand={p.brand} />
                          </div>
                          <div className="p-4 flex flex-col flex-1">
                            <div className="flex justify-between items-start mb-1">
                              <div className="flex-1 min-w-0">
                                <p className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2">{p.product_name}</p>
                                <p className="text-xs text-purple-600 font-medium mt-0.5">{p.brand}</p>
                              </div>
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize flex-shrink-0 ml-2 ${PRICE_BADGE[p.price_range] ?? 'bg-gray-100 text-gray-600'}`}>
                                {p.price_range}
                              </span>
                            </div>
                            <p className="text-xs text-gray-600 mb-3 leading-relaxed line-clamp-3 mt-1">{p.description}</p>
                            <div className="flex flex-wrap gap-1 mb-3">
                              {p.key_ingredients.slice(0, 3).map(ing => (
                                <span key={ing} className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full">{ing}</span>
                              ))}
                            </div>
                            <a href={p.amazon_url} target="_blank" rel="noopener noreferrer"
                              className="mt-auto flex items-center justify-center gap-2 w-full bg-amber-400 hover:bg-amber-500 text-gray-900 font-semibold py-2 rounded-xl transition text-xs">
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"/></svg>
                              View on Amazon
                            </a>
                          </div>
                        </div>
                      ))}
                    </HorizontalSlider>
                    {/* Dot indicators */}
                    <div className="flex justify-center gap-1.5 mt-4">
                      {dynProducts.map((_, i) => (
                        <div key={i} className={`w-1.5 h-1.5 rounded-full ${i === 0 ? 'bg-purple-600' : 'bg-gray-200'}`}/>
                      ))}
                    </div>
                  </div>
                )}
                <p className="text-xs text-gray-400 mt-4 text-center">Products are AI-recommended based on your skin profile. Links open Amazon search results.</p>
              </div>
            )}

            {/* Routine */}
            {activeTab === 'routine' && (
              <div>
                {!generatedRoutine ? (
                  <div>
                    <p className="text-gray-600 text-base mb-5">
                      Generate a personalised routine based on this scan's skin type
                      {activeConcerns.length > 0 && ` and ${activeConcerns.length} detected concern${activeConcerns.length > 1 ? 's' : ''}`}.
                    </p>
                    <div className="flex gap-3 mb-5">
                      {(['morning', 'night'] as const).map(t => (
                        <button key={t} onClick={() => setRoutineType(t)}
                          className={`flex-1 py-3 rounded-xl border-2 text-base font-medium transition capitalize
                            ${routineType === t ? 'border-purple-600 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600 hover:border-purple-200'}`}>
                          {t === 'morning' ? 'Morning' : 'Night'} Routine
                        </button>
                      ))}
                    </div>
                    {routineError && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-base mb-4">{routineError}</div>}
                    <button onClick={generateRoutine} disabled={generating}
                      className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-3.5 rounded-xl hover:from-purple-700 hover:to-indigo-700 transition font-medium text-base disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                      {generating ? <><svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Generating with AI</> : `Generate ${routineType === 'morning' ? 'Morning' : 'Night'} Routine`}
                    </button>
                  </div>
                ) : (
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="font-bold text-gray-900 text-lg">{generatedRoutine.name}</h3>
                        {generatedRoutine.description && <p className="text-base text-gray-500 mt-0.5">{generatedRoutine.description}</p>}
                      </div>
                      <span className="text-sm bg-green-100 text-green-700 px-2.5 py-1 rounded-full font-medium">Saved</span>
                    </div>
                    <div className="space-y-3 mb-5">
                      {generatedRoutine.steps?.map((step: any) => (
                        <div key={step.id} className="flex gap-3 bg-purple-50 rounded-xl p-3">
                          <div className="w-8 h-8 rounded-full bg-purple-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">{step.order}</div>
                          <div className="flex-1">
                            <p className="font-medium text-gray-900 text-base">{step.product_type}</p>
                            <p className="text-sm text-gray-600 mt-0.5 leading-relaxed">{step.instruction}</p>
                            <div className="flex gap-3 mt-1.5 flex-wrap">
                              {step.duration_seconds && <span className="text-sm text-purple-600">{fmtDuration(step.duration_seconds)}</span>}
                              {step.key_ingredient   && <span className="text-sm text-indigo-600">{step.key_ingredient}</span>}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-3">
                      <button onClick={() => navigate('/routines')} className="flex-1 bg-purple-600 text-white py-3 rounded-xl hover:bg-purple-700 transition font-medium text-base">View All Routines</button>
                      <button onClick={() => { setGenerated(null); setRoutineError(''); }} className="flex-1 border border-gray-200 text-gray-600 py-3 rounded-xl hover:bg-gray-50 transition font-medium text-base">Generate Another</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/upload" className="bg-purple-600 text-white px-8 py-3 rounded-xl hover:bg-purple-700 transition text-center font-medium text-base">New Analysis</Link>
          <Link to="/progress" className="bg-white text-purple-600 border-2 border-purple-200 px-8 py-3 rounded-xl hover:bg-purple-50 transition text-center font-medium text-base">View Progress</Link>
          <Link to="/chatbot" className="bg-white text-indigo-600 border-2 border-indigo-200 px-8 py-3 rounded-xl hover:bg-indigo-50 transition text-center font-medium text-base">Ask Lume</Link>
        </div>
      </div>
    </div>
  </PageShell>
  );
};

export default Results;