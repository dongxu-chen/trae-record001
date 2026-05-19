import React from 'react';
import { ConfigProvider, theme } from 'antd';
import Dashboard from './components/Dashboard';

const { defaultAlgorithm, darkAlgorithm } = theme;

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
        },
      }}
    >
      <Dashboard />
    </ConfigProvider>
  );
}

export default App;
