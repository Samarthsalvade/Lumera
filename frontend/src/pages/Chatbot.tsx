import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import PageShell from '../components/PageShell';

interface Message { id: number; role: 'user' | 'assistant'; content: string; timestamp: Date; }

const QUICK_QUESTIONS = [
  "What routine should I follow for my skin type?",
  "What ingredients should I avoid?",
  "How do I build a morning skincare routine?",
  "What products help with oily skin?",
];

const BotAvatar = () => (
  <div className="w-9 h-9 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-full flex items-center justify-center flex-shrink-0">
    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"/>
    </svg>
  </div>
);

const Chatbot = () => {
  const [messages, setMessages] = useState<Message[]>([{
    id: 1, role: 'assistant', timestamp: new Date(),
    content: "Hi! I'm Lume, your AI skincare consultant.\n\nI can help you with personalised advice based on your skin scans, routine building, ingredient education, and product recommendations.\n\nWhat would you like to know today?",
  }]);
  const [input, setInput]       = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError]       = useState('');
  const messagesEndRef           = useRef<HTMLDivElement>(null);
  const inputRef                 = useRef<HTMLInputElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isTyping]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isTyping) return;
    setError('');
    const userMsg: Message = { id: Date.now(), role: 'user', content: text.trim(), timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);
    const history = messages.slice(1).map(m => ({ role: m.role, content: m.content }));
    try {
      const res = await api.post('/chatbot/chat', { message: text.trim(), history });
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'assistant', content: res.data.reply, timestamp: new Date() }]);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Something went wrong. Please try again.');
      setMessages(prev => prev.filter(m => m.id !== userMsg.id));
    } finally { setIsTyping(false); inputRef.current?.focus(); }
  };

  const renderContent = (text: string) =>
    text.split('\n').map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g);
      return (
        <span key={i}>
          {parts.map((part, j) =>
            part.startsWith('**') && part.endsWith('**')
              ? <strong key={j}>{part.slice(2, -2)}</strong>
              : part
          )}
          {i < text.split('\n').length - 1 && <br />}
        </span>
      );
    });

  return (
    <PageShell>
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-purple-600 hover:underline mb-4 text-base font-medium">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><polyline points="15 18 9 12 15 6"/></svg>
            Back to Dashboard
          </Link>
          <div className="flex items-center gap-3">
            <BotAvatar />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">AI Skincare Consultant</h1>
              <p className="text-gray-500 text-base">Powered by Llama 3 · Personalised to your skin scans</p>
            </div>
          </div>
        </div>

        <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border border-white/60 overflow-hidden flex flex-col" style={{ height: '620px' }}>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && <div className="mr-2 mt-1"><BotAvatar /></div>}
                <div className={`max-w-xs md:max-w-md lg:max-w-lg px-4 py-3 rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-purple-600 to-indigo-600 text-white rounded-br-none'
                    : 'bg-gray-100 text-gray-800 rounded-bl-none'
                }`}>
                  <p className="text-base leading-relaxed">{renderContent(msg.content)}</p>
                  <p className={`text-xs mt-1.5 ${msg.role === 'user' ? 'text-purple-200' : 'text-gray-400'}`}>
                    {msg.timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex justify-start">
                <div className="mr-2"><BotAvatar /></div>
                <div className="bg-gray-100 px-4 py-3 rounded-2xl rounded-bl-none">
                  <div className="flex space-x-1.5 items-center h-5">
                    {[0, 0.15, 0.3].map((d, i) => (
                      <div key={i} className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: `${d}s` }}/>
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick questions */}
          {messages.length <= 1 && (
            <div className="px-6 py-4 bg-purple-50 border-t border-purple-100">
              <p className="text-sm font-semibold text-purple-700 uppercase tracking-wide mb-2">Suggested Questions</p>
              <div className="flex flex-wrap gap-2">
                {QUICK_QUESTIONS.map((q, i) => (
                  <button key={i} onClick={() => sendMessage(q)} disabled={isTyping}
                    className="text-sm bg-white text-purple-600 border border-purple-200 px-3 py-1.5 rounded-full hover:bg-purple-100 transition disabled:opacity-50">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {error && <div className="px-6 py-2 bg-red-50 border-t border-red-100"><p className="text-base text-red-600">{error}</p></div>}

          {/* Input */}
          <form onSubmit={e => { e.preventDefault(); sendMessage(input); }} className="p-4 bg-gray-50 border-t border-gray-100">
            <div className="flex gap-2">
              <input ref={inputRef} type="text" value={input} onChange={e => setInput(e.target.value)}
                placeholder="Ask about your skin, routines, ingredients..."
                disabled={isTyping}
                className="flex-1 px-4 py-3 border border-gray-200 rounded-full text-base focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-60 bg-white"
              />
              <button type="submit" disabled={!input.trim() || isTyping}
                className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-5 py-3 rounded-full hover:from-purple-700 hover:to-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
              </button>
            </div>
          </form>
        </div>

        <div className="mt-4 p-4 bg-blue-50/80 rounded-xl border border-blue-100">
          <p className="text-base text-blue-800">
            <strong>Note:</strong> Lume provides general skincare education and is not a substitute for professional medical advice. For persistent skin concerns, consult a dermatologist.
          </p>
        </div>
      </div>
    </PageShell>
  );
};

export default Chatbot;