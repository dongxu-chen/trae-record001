import React, { useState } from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import ScanPage from './components/ScanPage';
import ResultsPage from './components/ResultsPage';
import PayloadsPage from './components/PayloadsPage';

function App() {
  const [scanResult, setScanResult] = useState(null);

  return (
    <div className="app-container">
      <nav className="navbar">
        <h1>🔒 API安全漏洞扫描器</h1>
        <nav>
          <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
            扫描
          </NavLink>
          <NavLink to="/results" className={({ isActive }) => isActive ? 'active' : ''}>
            结果
          </NavLink>
          <NavLink to="/payloads" className={({ isActive }) => isActive ? 'active' : ''}>
            载荷库
          </NavLink>
        </nav>
      </nav>
      
      <main className="main-content">
        <Routes>
          <Route path="/" element={
            <ScanPage 
              onScanComplete={(result) => {
                setScanResult(result);
              }} 
            />
          } />
          <Route path="/results" element={
            <ResultsPage result={scanResult} />
          } />
          <Route path="/payloads" element={<PayloadsPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
