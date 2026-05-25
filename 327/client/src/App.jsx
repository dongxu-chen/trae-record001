import React from 'react';
import { Routes, Route } from 'react-router-dom';
import LobbyPage from './pages/LobbyPage';
import MeetingPage from './pages/MeetingPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<LobbyPage />} />
      <Route path="/meeting/:roomId" element={<MeetingPage />} />
      <Route path="/join/:roomId" element={<LobbyPage />} />
    </Routes>
  );
}

export default App;
