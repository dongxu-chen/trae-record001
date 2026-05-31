import React from 'react';
import { useNavigate } from 'react-router-dom';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'service-graph', label: 'Service Graph', icon: '🔗' },
  { id: 'policies', label: 'Policies', icon: '📜' },
  { id: 'conflicts', label: 'Conflicts', icon: '⚠️' },
  { id: 'simulator', label: 'Simulator', icon: '🔬' },
  { id: 'compliance', label: 'Compliance', icon: '✅' },
  { id: 'deployment', label: 'Deployment', icon: '🚀' },
  { id: 'effectiveness', label: 'Effectiveness', icon: '📈' },
  { id: 'visualization', label: 'Visualization', icon: '🎯' },
];

function Sidebar({ activePage, setActivePage }) {
  const navigate = useNavigate();

  const handleNavClick = (id) => {
    setActivePage(id);
    navigate(`/${id}`);
  };

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <h1>🔒 AuthZ Policy Recommender</h1>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <div
            key={item.id}
            className={`nav-item ${activePage === item.id ? 'active' : ''}`}
            onClick={() => handleNavClick(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </nav>
    </div>
  );
}

export default Sidebar;
