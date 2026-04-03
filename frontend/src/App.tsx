import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home           from './pages/Home';
import Login          from './pages/Login';
import Signup         from './pages/Signup';
import Dashboard      from './pages/Dashboard';
import Upload         from './pages/Upload';
import Results        from './pages/Results';
import Chatbot        from './pages/Chatbot';
import Progress       from './pages/Progress';
import Routines       from './pages/Routines';
import WeeklyReport   from './pages/WeeklyReport';
import VerifyOtp      from './pages/VerifyOtp';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword  from './pages/ResetPassword';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar         from './components/Navbar';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-indigo-50">
        <Navbar />
        <Routes>
          {/* Public */}
          <Route path="/"                element={<Home />} />
          <Route path="/login"           element={<Login />} />
          <Route path="/signup"          element={<Signup />} />
          <Route path="/verify-otp"      element={<VerifyOtp />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password"  element={<ResetPassword />} />

          {/* Protected */}
          <Route path="/dashboard"    element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/upload"       element={<ProtectedRoute><Upload /></ProtectedRoute>} />
          <Route path="/results/:id"  element={<ProtectedRoute><Results /></ProtectedRoute>} />
          <Route path="/chatbot"      element={<ProtectedRoute><Chatbot /></ProtectedRoute>} />
          <Route path="/progress"     element={<ProtectedRoute><Progress /></ProtectedRoute>} />
          <Route path="/routines"     element={<ProtectedRoute><Routines /></ProtectedRoute>} />
          <Route path="/report"       element={<ProtectedRoute><WeeklyReport /></ProtectedRoute>} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;