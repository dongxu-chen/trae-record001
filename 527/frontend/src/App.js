import React from 'react';
import { Routes, Route } from 'react-router-dom';
import styled from 'styled-components';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import TaskList from './pages/TaskList';
import AnnotationPage from './pages/AnnotationPage';
import ExportPage from './pages/ExportPage';
import ConsistencyPage from './pages/ConsistencyPage';
import TemplatesPage from './pages/TemplatesPage';
import QualityPage from './pages/QualityPage';
import AchievementsPage from './pages/AchievementsPage';

const AppContainer = styled.div`
  display: flex;
  min-height: 100vh;
`;

const MainContent = styled.main`
  flex: 1;
  margin-left: 250px;
  padding: 24px;
  background-color: var(--bg-primary);
`;

function App() {
  return (
    <AppContainer>
      <Sidebar />
      <MainContent>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tasks" element={<TaskList />} />
          <Route path="/annotate/:taskId" element={<AnnotationPage />} />
          <Route path="/export/:taskId" element={<ExportPage />} />
          <Route path="/consistency/:taskId" element={<ConsistencyPage />} />
          <Route path="/templates/:taskId?" element={<TemplatesPage />} />
          <Route path="/quality/:taskId" element={<QualityPage />} />
          <Route path="/achievements/:taskId" element={<AchievementsPage />} />
        </Routes>
      </MainContent>
    </AppContainer>
  );
}

export default App;
