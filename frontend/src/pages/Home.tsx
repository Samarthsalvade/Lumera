// ─── Home.tsx ────────────────────────────────────────────────────────────────
import { Link } from 'react-router-dom';
import PageShell from '../components/PageShell';

const FeatureIcons = [
  <svg className="w-10 h-10 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"/><path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z"/></svg>,
  <svg className="w-10 h-10 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"/></svg>,
  <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z"/></svg>,
];

const FEATURES = [
  { title: 'Upload or Capture', desc: 'Take a clear photo of your face or upload one from your device.' },
  { title: 'AI Analysis',       desc: 'Our model analyses skin type, concerns like acne, dark circles and more.' },
  { title: 'Get Recommendations', desc: 'Receive personalised routines and product suggestions tailored to you.' },
];

export const Home = () => (
  <PageShell>
    <div className="flex items-center justify-center pt-12 pb-16">
      <div className="max-w-4xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 bg-purple-100 text-purple-700 px-4 py-2 rounded-full text-sm font-semibold mb-8">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"/></svg>
          AI-powered skincare analysis
        </div>
        <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent leading-tight">
          Welcome to Luméra
        </h1>
        <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
          Discover your skin type with AI-powered analysis. Get personalised skincare recommendations tailored just for you.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/signup" className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-10 py-4 rounded-xl text-lg font-semibold hover:from-purple-700 hover:to-indigo-700 transition shadow-lg shadow-purple-200">
            Get Started
          </Link>
          <Link to="/login" className="bg-white/80 text-purple-600 px-10 py-4 rounded-xl text-lg font-semibold hover:bg-white transition border-2 border-purple-200 shadow-sm">
            Login
          </Link>
        </div>
      </div>
    </div>

    <div className="max-w-5xl mx-auto pb-20">
      <p className="text-center text-gray-400 text-sm font-semibold uppercase tracking-widest mb-10">How it works</p>
      <div className="grid md:grid-cols-3 gap-8">
        {FEATURES.map((f, i) => (
          <div key={i} className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 shadow-sm border border-white/60 hover:shadow-md hover:border-purple-200 transition-all duration-300 text-center">
            <div className="flex justify-center mb-5">
              <div className="w-16 h-16 bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl flex items-center justify-center">
                {FeatureIcons[i]}
              </div>
            </div>
            <h3 className="text-xl font-bold mb-3 text-gray-900">{f.title}</h3>
            <p className="text-gray-500 text-base leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
      <div className="mt-16 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-8 text-white shadow-xl">
        <div className="grid grid-cols-3 gap-6 text-center">
          {[{ value: '95%', label: 'Skin type accuracy' }, { value: '9', label: 'Concerns detected' }, { value: 'AI', label: 'Powered routines' }].map((s, i) => (
            <div key={i}>
              <p className="text-4xl font-bold mb-1">{s.value}</p>
              <p className="text-purple-200 text-base">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  </PageShell>
);

export default Home;