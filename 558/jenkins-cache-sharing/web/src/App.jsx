import { Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Caches from './pages/Caches';
import Versions from './pages/Versions';
import Warmup from './pages/Warmup';
import Cleanup from './pages/Cleanup';
import Jenkins from './pages/Jenkins';

function Sidebar() {
  const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/caches', label: 'Cache Manager', icon: '📦' },
    { path: '/versions', label: 'Version Control', icon: '🏷️' },
    { path: '/warmup', label: 'Cache Warmup', icon: '🔥' },
    { path: '/cleanup', label: 'Cleanup Policies', icon: '🧹' },
    { path: '/jenkins', label: 'Jenkins', icon: '⚙️' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">JC</div>
        <div>
          <h1>Cache Share</h1>
          <p>Jenkins Build Cache</p>
        </div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

export default function App() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/caches" element={<Caches />} />
          <Route path="/versions" element={<Versions />} />
          <Route path="/warmup" element={<Warmup />} />
          <Route path="/cleanup" element={<Cleanup />} />
          <Route path="/jenkins" element={<Jenkins />} />
        </Routes>
      </main>
    </div>
  );
}
