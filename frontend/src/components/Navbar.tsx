import { Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';

const Icons = {
  dashboard: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>,
  chat:      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>,
  progress:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
  routines:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>,
  scan:      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  logout:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  menu:      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>,
  close:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  report:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>,
};

const Navbar = () => {
  const location = useLocation();
  const { isAuthenticated, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // ignore — always clear local state regardless
    } finally {
      setIsMobileMenuOpen(false);
      logout('manual');   // AuthContext clears localStorage + state + redirects
    }
  };

  const isActive = (path: string) => location.pathname === path;

  const navLink = (to: string, icon: JSX.Element, label: string) => (
    <Link
      to={to}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-base font-medium transition-all duration-150
        ${isActive(to) ? 'bg-purple-50 text-purple-700' : 'text-gray-600 hover:text-purple-700 hover:bg-purple-50'}`}
    >
      {icon}<span>{label}</span>
    </Link>
  );

  const logoTo = isAuthenticated ? '/dashboard' : '/';

  return (
    <nav className="bg-white border-b border-gray-100 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">

          {/* Logo */}
          <Link to={logoTo} className="flex items-center gap-2.5" onClick={() => setIsMobileMenuOpen(false)}>
            <div className="w-9 h-9 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-md">
              <span className="text-white font-bold text-lg leading-none">L</span>
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent tracking-tight">
              Luméra
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {isAuthenticated ? (
              <>
                {navLink('/dashboard', Icons.dashboard, 'Dashboard')}
                {navLink('/chatbot',   Icons.chat,      'AI Chat')}
                {navLink('/progress',  Icons.progress,  'Progress')}
                {navLink('/routines',  Icons.routines,  'Routines')}
                {navLink('/report',    Icons.report,    'Report')}
                <Link to="/upload"
                  className="flex items-center gap-2 ml-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-xl hover:from-purple-700 hover:to-indigo-700 transition font-medium text-base shadow-sm">
                  {Icons.scan}<span>New Scan</span>
                </Link>
                <button onClick={handleLogout}
                  className="flex items-center gap-2 ml-1 px-3 py-2 rounded-lg text-base font-medium text-gray-500 hover:text-red-600 hover:bg-red-50 transition">
                  {Icons.logout}<span>Logout</span>
                </button>
              </>
            ) : (
              <>
                <Link to="/login"  className="px-4 py-2 text-base font-medium text-gray-600 hover:text-purple-700 transition">Login</Link>
                <Link to="/signup" className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-5 py-2 rounded-xl hover:from-purple-700 hover:to-indigo-700 transition font-medium text-base shadow-sm">Sign Up</Link>
              </>
            )}
          </div>

          <button className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-purple-50" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
            {isMobileMenuOpen ? Icons.close : Icons.menu}
          </button>
        </div>

        {isMobileMenuOpen && (
          <div className="md:hidden py-3 border-t border-gray-100 space-y-1">
            {isAuthenticated ? (
              <>
                {[
                  ['/dashboard', Icons.dashboard, 'Dashboard'],
                  ['/chatbot',   Icons.chat,      'AI Chat'],
                  ['/progress',  Icons.progress,  'Progress'],
                  ['/routines',  Icons.routines,  'Routines'],
                  ['/report',    Icons.report,    'Report'],
                ].map(([to, icon, label]) => (
                  <Link key={to as string} to={to as string} onClick={() => setIsMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-base font-medium transition
                      ${isActive(to as string) ? 'bg-purple-50 text-purple-700' : 'text-gray-600 hover:bg-purple-50 hover:text-purple-700'}`}>
                    {icon as JSX.Element}<span>{label as string}</span>
                  </Link>
                ))}
                <Link to="/upload" onClick={() => setIsMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-medium text-base">
                  {Icons.scan}<span>New Scan</span>
                </Link>
                <button onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-base font-medium text-red-600 hover:bg-red-50 transition text-left">
                  {Icons.logout}<span>Logout</span>
                </button>
              </>
            ) : (
              <>
                <Link to="/login"  onClick={() => setIsMobileMenuOpen(false)} className="block px-4 py-2.5 text-base font-medium text-gray-600 hover:bg-purple-50 hover:text-purple-700 rounded-xl">Login</Link>
                <Link to="/signup" onClick={() => setIsMobileMenuOpen(false)} className="block px-4 py-2.5 text-base font-medium bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-center">Sign Up</Link>
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;