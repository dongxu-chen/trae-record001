import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import ExamineePage from './pages/ExamineePage';
import ProctorPage from './pages/ProctorPage';
import RecordingsPage from './pages/RecordingsPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/examinee" element={<ExamineePage />} />
          <Route path="/proctor" element={<ProctorPage />} />
          <Route path="/recordings" element={<RecordingsPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
