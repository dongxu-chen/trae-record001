import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import WorkflowList from './pages/WorkflowList.jsx';
import WorkflowEditor from './pages/WorkflowEditor.jsx';
import ExecutionList from './pages/ExecutionList.jsx';
import ExecutionDetail from './pages/ExecutionDetail.jsx';
import TriggerList from './pages/TriggerList.jsx';
import TriggerForm from './pages/TriggerForm.jsx';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<WorkflowList />} />
        <Route path="/workflows" element={<WorkflowList />} />
        <Route path="/workflows/new" element={<WorkflowEditor />} />
        <Route path="/workflows/:id/edit" element={<WorkflowEditor />} />
        <Route path="/executions" element={<ExecutionList />} />
        <Route path="/executions/:id" element={<ExecutionDetail />} />
        <Route path="/triggers" element={<TriggerList />} />
        <Route path="/triggers/new" element={<TriggerForm />} />
        <Route path="/triggers/:id/edit" element={<TriggerForm />} />
      </Routes>
    </Layout>
  );
}

export default App;
