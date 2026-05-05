import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';

interface InactivityWarningProps {
  visible: boolean;
  onStayLoggedIn: () => void;
}

export default function InactivityWarning({ visible, onStayLoggedIn }: InactivityWarningProps) {
  const { logout } = useAuth();
  const [secondsLeft, setSecondsLeft] = useState(60);

  // Countdown timer — resets every time the modal becomes visible
  useEffect(() => {
    if (!visible) {
      setSecondsLeft(60);
      return;
    }

    setSecondsLeft(60);
    const interval = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(interval);
          return 0;
        }
        return s - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [visible]);

  if (!visible) return null;

  return (
    // Backdrop
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Blurred overlay */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onStayLoggedIn}
      />

      {/* Modal card */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-7 flex flex-col items-center gap-5 animate-fade-in">

        {/* Icon */}
        <div className="w-16 h-16 rounded-full bg-amber-50 border-2 border-amber-200 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-amber-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.8}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
        </div>

        {/* Text */}
        <div className="text-center">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">
            Still there?
          </h2>
          <p className="text-sm text-gray-500 leading-relaxed">
            You've been inactive for a while. For your security, you'll be
            logged out in
          </p>
          {/* Countdown */}
          <p className="mt-3 text-4xl font-bold tabular-nums bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
            {secondsLeft}s
          </p>
        </div>

        {/* Progress bar */}
        <div className="w-full h-1.5 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-1000 ease-linear"
            style={{ width: `${(secondsLeft / 60) * 100}%` }}
          />
        </div>

        {/* Buttons */}
        <div className="flex gap-3 w-full">
          <button
            onClick={() => logout('manual')}
            className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Log out
          </button>
          <button
            onClick={onStayLoggedIn}
            className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-sm font-semibold text-white hover:opacity-90 transition-opacity shadow-sm"
          >
            Stay logged in
          </button>
        </div>
      </div>
    </div>
  );
}