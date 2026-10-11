import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ProtocolReview from './pages/ProtocolReview';
import { Activity, Bell, Settings, User, Sun, Moon } from 'lucide-react';

function App() {
  const [dark, setDark] = useState(() => {
    try { const saved = localStorage.getItem('sg.darkMode'); return saved === '1' || (saved !== '0' && matchMedia('(prefers-color-scheme: dark)').matches); }
    catch { return false; }
  });
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
  }, [dark]);
  useEffect(() => {
    const sync = (event: StorageEvent) => { if (event.key === 'sg.darkMode') setDark(event.newValue === '1'); };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);
  const toggle = () => {
    const next = !dark; setDark(next);
    try { localStorage.setItem('sg.darkMode', next ? '1' : '0'); } catch {}
  };
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-50 text-gray-900 font-sans">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-gray-200 flex flex-col transition-all shadow-sm">
          <div className="p-6">
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 tracking-tight">
              SurgiGuard AI
            </h1>
            <p className="text-xs text-gray-500 font-medium mt-1 uppercase tracking-wider">Clinician Portal</p>
          </div>
          
          <nav className="flex-1 px-4 space-y-2 mt-4">
            <Link to="/" className="flex items-center px-4 py-3 bg-blue-50 text-blue-700 rounded-xl font-medium transition-colors hover:bg-blue-100 group">
              <Activity className="w-5 h-5 mr-3 text-blue-500 group-hover:scale-110 transition-transform" />
              Patients
            </Link>
            <a href="#" className="flex items-center px-4 py-3 text-gray-600 rounded-xl font-medium transition-colors hover:bg-gray-100 group">
              <Bell className="w-5 h-5 mr-3 text-gray-400 group-hover:text-gray-600 transition-colors" />
              Alerts
              <span className="ml-auto bg-red-100 text-red-600 py-0.5 px-2 rounded-full text-xs font-bold shadow-sm">2</span>
            </a>
            <a href="#" className="flex items-center px-4 py-3 text-gray-600 rounded-xl font-medium transition-colors hover:bg-gray-100 group">
              <Settings className="w-5 h-5 mr-3 text-gray-400 group-hover:text-gray-600 transition-colors" />
              Settings
            </a>
          </nav>

          <div className="p-4 border-t border-gray-100">
            <div className="flex items-center p-3 bg-gray-50 rounded-xl hover:bg-gray-100 cursor-pointer transition-colors">
              <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-700 font-bold shadow-sm">
                ER
              </div>
              <div className="ml-3">
                <p className="text-sm font-semibold text-gray-800">Dr. Elena Ruiz</p>
                <p className="text-xs text-gray-500">Orthopedic Surgeon</p>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-auto bg-gray-50/50">
          <header className="h-16 bg-white/80 backdrop-blur-md border-b border-gray-200 flex items-center justify-between px-8 sticky top-0 z-10">
            <h2 className="text-lg font-semibold text-gray-800">Department Overview</h2>
            <div className="flex items-center space-x-4">
              <button onClick={toggle} aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
                className="flex items-center gap-2 px-3 py-2 text-sm font-semibold border border-gray-200 rounded-full text-gray-700 bg-white">
                {dark ? <Sun size={16} /> : <Moon size={16} />}{dark ? 'Light mode' : 'Dark mode'}
              </button>
              <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors rounded-full hover:bg-gray-100">
                <Bell className="w-5 h-5" />
              </button>
              <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors rounded-full hover:bg-gray-100">
                <User className="w-5 h-5" />
              </button>
            </div>
          </header>
          
          <div className="p-8 max-w-7xl mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/protocol/:patientId" element={<ProtocolReview />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
