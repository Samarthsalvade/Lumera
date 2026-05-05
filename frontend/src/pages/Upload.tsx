import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { AnalysisResponse } from '../types';
import PageShell from '../components/PageShell';

type InputMode = 'upload' | 'camera';

// ── Inline face guide SVG shown in the tips panel ─────────────────────────────
const FaceGuideIllustration = () => (
  <svg viewBox="0 0 200 160" className="w-full max-w-xs mx-auto" fill="none" xmlns="http://www.w3.org/2000/svg">
    {/* Frame border */}
    <rect x="2" y="2" width="196" height="156" rx="10" stroke="#e9d5ff" strokeWidth="1.5" strokeDasharray="6 3"/>
    {/* Good example — left */}
    <g>
      <rect x="12" y="12" width="82" height="136" rx="8" fill="#f5f3ff" stroke="#a78bfa" strokeWidth="1"/>
      {/* Face oval */}
      <ellipse cx="53" cy="72" rx="26" ry="34" fill="#fde68a" stroke="#d97706" strokeWidth="1"/>
      {/* Eyes */}
      <ellipse cx="44" cy="62" rx="5" ry="3.5" fill="white" stroke="#374151" strokeWidth="0.8"/>
      <ellipse cx="62" cy="62" rx="5" ry="3.5" fill="white" stroke="#374151" strokeWidth="0.8"/>
      <circle cx="44" cy="62" r="2" fill="#1f2937"/>
      <circle cx="62" cy="62" r="2" fill="#1f2937"/>
      {/* Under-eye area visible */}
      <path d="M39 68 Q44 71 49 68" stroke="#9ca3af" strokeWidth="0.8" strokeLinecap="round"/>
      <path d="M57 68 Q62 71 67 68" stroke="#9ca3af" strokeWidth="0.8" strokeLinecap="round"/>
      {/* Nose */}
      <path d="M53 65 L50 78 Q53 80 56 78 L53 65" stroke="#d97706" strokeWidth="0.8" fill="none"/>
      {/* Mouth */}
      <path d="M44 88 Q53 94 62 88" stroke="#374151" strokeWidth="1" strokeLinecap="round" fill="none"/>
      {/* Neck visible */}
      <rect x="47" y="106" width="12" height="18" rx="4" fill="#fde68a" stroke="#d97706" strokeWidth="0.8"/>
      {/* Shoulders */}
      <path d="M20 136 Q30 120 47 118 Q53 116 59 118 Q76 120 86 136" fill="#ddd6fe" stroke="#7c3aed" strokeWidth="0.8"/>
      {/* Check mark */}
      <circle cx="68" cy="22" r="8" fill="#22c55e"/>
      <path d="M64 22 L67 25 L73 19" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <text x="53" y="150" textAnchor="middle" fontSize="8" fill="#7c3aed" fontWeight="600">Full face</text>
    </g>
    {/* Bad example — right */}
    <g>
      <rect x="106" y="12" width="82" height="136" rx="8" fill="#fff1f2" stroke="#fca5a5" strokeWidth="1"/>
      {/* Cropped — only shows eyes zoomed in */}
      <ellipse cx="130" cy="75" rx="14" ry="10" fill="white" stroke="#374151" strokeWidth="1"/>
      <ellipse cx="160" cy="75" rx="14" ry="10" fill="white" stroke="#374151" strokeWidth="1"/>
      <circle cx="130" cy="75" r="6" fill="#1f2937"/>
      <circle cx="160" cy="75" r="6" fill="#1f2937"/>
      <circle cx="132" cy="73" r="2" fill="white"/>
      <circle cx="162" cy="73" r="2" fill="white"/>
      {/* Crop lines */}
      <line x1="106" y1="55" x2="188" y2="55" stroke="#fca5a5" strokeWidth="1" strokeDasharray="3 2"/>
      <line x1="106" y1="98" x2="188" y2="98" stroke="#fca5a5" strokeWidth="1" strokeDasharray="3 2"/>
      {/* X mark */}
      <circle cx="162" cy="22" r="8" fill="#ef4444"/>
      <path d="M158 18 L166 26 M166 18 L158 26" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
      <text x="147" y="150" textAnchor="middle" fontSize="8" fill="#dc2626" fontWeight="600">Too zoomed</text>
    </g>
  </svg>
);

const Upload = () => {
  const navigate = useNavigate();
  const [mode, setMode]                 = useState<InputMode>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview]           = useState<string | null>(null);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState('');
  const videoRef    = useRef<HTMLVideoElement>(null);
  const canvasRef   = useRef<HTMLCanvasElement>(null);
  const [_stream, setStream]           = useState<MediaStream | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [facingMode, setFacingMode]   = useState<'user' | 'environment'>('user');
  const [captured, setCaptured]       = useState(false);

  const stopStream = useCallback(() => {
    setStream(prev => { prev?.getTracks().forEach(t => t.stop()); return null; });
    setCameraReady(false);
  }, []);

  const startCamera = useCallback(async (facing: 'user' | 'environment') => {
    stopStream();
    setCameraError(''); setCameraReady(false); setCaptured(false);
    setPreview(null); setSelectedFile(null);
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 960 } },
        audio: false,
      });
      setStream(s);
      if (videoRef.current) {
        videoRef.current.srcObject = s;
        videoRef.current.onloadedmetadata = () => setCameraReady(true);
      }
    } catch {
      setCameraError('Camera access denied or unavailable. Please allow camera access or use the Upload tab.');
    }
  }, [stopStream]);

  useEffect(() => {
    if (mode === 'camera') startCamera(facingMode);
    else stopStream();
    return () => stopStream();
  }, [mode]); // eslint-disable-line

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current; const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 640; canvas.height = video.videoHeight || 480;
    canvas.getContext('2d')!.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    setPreview(dataUrl); setCaptured(true); stopStream();
    canvas.toBlob(blob => {
      if (blob) setSelectedFile(new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' }));
    }, 'image/jpeg', 0.92);
  };

  const retake = () => { setCaptured(false); setPreview(null); setSelectedFile(null); startCamera(facingMode); };
  const flipCamera = () => {
    const next = facingMode === 'user' ? 'environment' : 'user';
    setFacingMode(next); startCamera(next);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    if (!file.type.startsWith('image/')) { setError('Please select an image file'); return; }
    if (file.size > 16 * 1024 * 1024) { setError('File size must be less than 16MB'); return; }
    setSelectedFile(file); setPreview(URL.createObjectURL(file)); setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) { setError('Please select or capture an image'); return; }
    setLoading(true); setError('');
    const formData = new FormData(); formData.append('image', selectedFile);
    try {
      const response = await api.post<AnalysisResponse>('/analysis/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      if (response.data.success === false) {
        setError(response.data.message || 'No face detected. Please try another photo.');
        return;
      }
      navigate(`/results/${response.data.analysis.id}`);
    } catch (err: any) {
      const status = err.response?.status;
      const msg    = err.response?.data?.error || err.response?.data?.message || '';
      if (status === 401) {
        sessionStorage.removeItem('token'); sessionStorage.removeItem('user'); navigate('/login'); return;
      }
      if (status === 422) {
        const isJwt = msg.toLowerCase().includes('token') || msg.toLowerCase().includes('signature') || msg.toLowerCase().includes('expired');
        if (isJwt) { sessionStorage.removeItem('token'); sessionStorage.removeItem('user'); navigate('/login'); return; }
        setError(msg || 'Upload failed. Please try again.'); return;
      }
      setError(msg || 'Upload failed. Please try again.');
    } finally { setLoading(false); }
  };

  const switchMode = (m: InputMode) => { setError(''); setPreview(null); setSelectedFile(null); setMode(m); };

  return (
    <PageShell>
      <div className="max-w-3xl mx-auto">

        {/* Page title */}
        <div className="mb-6 text-center">
          <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
            Analyse Your Skin
          </h2>
          <p className="text-gray-500 text-base mt-1">Upload a clear photo for the most accurate results</p>
        </div>

        {/* ── Critical guidance banner ──────────────────────────────────────── */}
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 mb-6">
          <div className="flex gap-3 items-start">
            <div className="w-9 h-9 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
              </svg>
            </div>
            <div>
              <p className="font-bold text-amber-800 text-base mb-1">Full face photo required for accurate analysis</p>
              <p className="text-amber-700 text-sm leading-relaxed">
                The AI needs to see your <strong>entire face including forehead, eyes, cheeks, nose, lips and chin</strong>.
                Close-up or zoomed-in photos prevent the model from detecting concerns in their correct zones
                and will cause misclassification. Aim for a photo where your face fills about 60–70% of the frame.
              </p>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-5 gap-6">

          {/* ── Main upload panel (3/5 width) ─────────────────────────────── */}
          <div className="md:col-span-3 bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-white/60 p-7">

            {/* Mode tabs */}
            <div className="flex rounded-xl border border-gray-200 overflow-hidden mb-6">
              {(['upload', 'camera'] as const).map(m => (
                <button key={m} type="button" onClick={() => switchMode(m)}
                  className={`flex-1 py-3.5 text-base font-semibold flex items-center justify-center gap-2 transition
                    ${mode === m ? 'bg-purple-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
                  {m === 'upload'
                    ? <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                    : <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                  }
                  {m === 'upload' ? 'Upload Photo' : 'Live Camera'}
                </button>
              ))}
            </div>

            {error && (
              <div className="bg-red-50 text-red-600 border border-red-200 p-3 rounded-xl mb-5 text-base">{error}</div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">

              {/* Upload mode */}
              {mode === 'upload' && (
                <div>
                  <label className="block text-gray-700 font-semibold mb-3 text-base">
                    Select a full-face photo
                  </label>
                  <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-purple-500 transition cursor-pointer">
                    <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" id="file-upload"/>
                    <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                      {preview ? (
                        <>
                          <img src={preview} alt="Preview" className="max-h-56 rounded-xl mb-3 object-contain"/>
                          <span className="text-base text-purple-600 hover:underline font-medium">Click to choose a different photo</span>
                        </>
                      ) : (
                        <>
                          <div className="w-16 h-16 bg-purple-50 rounded-2xl flex items-center justify-center mb-4">
                            <svg className="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                            </svg>
                          </div>
                          <p className="text-gray-600 mb-1 text-base font-medium">Click to upload or drag and drop</p>
                          <p className="text-sm text-gray-400">PNG, JPG or JPEG · max 16MB</p>
                        </>
                      )}
                    </label>
                  </div>
                </div>
              )}

              {/* Camera mode */}
              {mode === 'camera' && (
                <div>
                  <label className="block text-gray-700 font-semibold mb-3 text-base">
                    Position your <span className="text-purple-600">full face</span> inside the oval
                  </label>
                  {cameraError ? (
                    <div className="bg-red-50 text-red-600 p-4 rounded-xl text-base text-center border border-red-200">{cameraError}</div>
                  ) : !captured ? (
                    <div>
                      <div className="relative rounded-xl overflow-hidden bg-black" style={{ aspectRatio: '4/3' }}>
                        <video ref={videoRef} autoPlay playsInline muted
                          className="w-full h-full object-cover"
                          style={{ transform: facingMode === 'user' ? 'scaleX(-1)' : 'none' }}
                        />
                        {/* Oval guide with shoulder clearance — taller than before */}
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                          <div className="border-2 border-white/80 rounded-full"
                            style={{
                              width: '52%',
                              aspectRatio: '3/4.2',
                              boxShadow: '0 0 0 9999px rgba(0,0,0,0.32)',
                            }}
                          />
                        </div>
                        {/* Guide text */}
                        <div className="absolute bottom-3 inset-x-0 text-center pointer-events-none">
                          <p className="text-white/90 text-sm font-medium bg-black/30 inline-block px-3 py-1 rounded-full">
                            Full face + neck should be visible
                          </p>
                        </div>
                        {!cameraReady && (
                          <div className="absolute inset-0 flex items-center justify-center bg-black/60">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white"/>
                          </div>
                        )}
                      </div>
                      <div className="flex gap-3 mt-4">
                        <button type="button" onClick={capturePhoto} disabled={!cameraReady}
                          className="flex-1 bg-purple-600 text-white py-3.5 rounded-xl hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-semibold text-base">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <circle cx="12" cy="12" r="3" strokeWidth={1.5}/>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
                          </svg>
                          Capture Photo
                        </button>
                        <button type="button" onClick={flipCamera}
                          className="w-12 h-12 flex-shrink-0 bg-gray-100 rounded-xl hover:bg-gray-200 flex items-center justify-center transition"
                          title="Flip camera">
                          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                          </svg>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <img src={preview!} alt="Captured"
                        className="w-full rounded-xl mb-3 max-h-72 object-contain"
                        style={{ transform: facingMode === 'user' ? 'scaleX(-1)' : 'none' }}
                      />
                      <button type="button" onClick={retake} className="text-base text-purple-600 hover:underline font-medium">
                        ↩ Retake photo
                      </button>
                    </div>
                  )}
                </div>
              )}

              <canvas ref={canvasRef} className="hidden"/>

              <button type="submit" disabled={!selectedFile || loading}
                className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-3.5 rounded-xl hover:from-purple-700 hover:to-indigo-700 transition font-bold text-base disabled:opacity-50 disabled:cursor-not-allowed">
                {loading
                  ? <span className="flex items-center justify-center gap-2">
                      <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>
                      Analysing your skin...
                    </span>
                  : 'Analyse My Skin'}
              </button>
            </form>
          </div>

          {/* ── Right panel: visual guide + checklist (2/5 width) ─────────── */}
          <div className="md:col-span-2 flex flex-col gap-5">

            {/* Face guide illustration */}
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-sm border border-white/60 p-5">
              <p className="text-sm font-bold text-gray-700 uppercase tracking-wide mb-3">Photo guide</p>
              <FaceGuideIllustration />
            </div>

            {/* Checklist */}
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-sm border border-white/60 p-5 flex-1">
              <p className="text-sm font-bold text-gray-700 uppercase tracking-wide mb-4">Before you shoot</p>
              <ul className="space-y-3">
                {[
                  { ok: true,  text: 'Entire face visible — forehead to chin' },
                  { ok: true,  text: 'Neutral, even lighting — no harsh shadows' },
                  { ok: true,  text: 'Looking straight at the camera' },
                  { ok: true,  text: 'Bare skin — no heavy filters or makeup' },
                  { ok: false, text: 'Zoomed in on one feature only' },
                  { ok: false, text: 'Face turned to the side' },
                  { ok: false, text: 'Dark, backlit, or blurry photo' },
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5
                      ${item.ok ? 'bg-green-100' : 'bg-red-100'}`}>
                      {item.ok
                        ? <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>
                        : <svg className="w-3 h-3 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                      }
                    </span>
                    <span className={`text-sm leading-relaxed ${item.ok ? 'text-gray-700' : 'text-gray-400'}`}>
                      {item.text}
                    </span>
                  </li>
                ))}
              </ul>

              {/* Why it matters note */}
              <div className="mt-5 pt-4 border-t border-gray-100">
                <p className="text-xs text-gray-400 leading-relaxed">
                  The AI maps concerns to specific face zones (forehead, cheeks, under-eyes, nose). 
                  A cropped image means the zone coordinates point to the wrong areas, causing missed or incorrect detections.
                </p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </PageShell>
  );
};

export default Upload;