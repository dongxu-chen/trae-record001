import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useSelector } from 'react-redux';
import { RootState } from './store';

import MainLayout from './layouts/MainLayout';
import HomePage from './pages/HomePage';
import TemplateListPage from './pages/TemplateListPage';
import TemplateDetailPage from './pages/TemplateDetailPage';
import PreviewPage from './pages/PreviewPage';
import AdminPage from './pages/AdminPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import UploadPage from './pages/UploadPage';
import EditorPage from './pages/EditorPage';

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, user } = useSelector((state: RootState) => state.auth);
  return isAuthenticated && user?.role === 'admin' ? <>{children}</> : <Navigate to="/" />;
};

function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#3B82F6',
          borderRadius: 8,
          colorBgBase: '#0F172A',
          colorBgElevated: '#1E293B',
          colorBgContainer: '#1E293B',
          colorBorder: '#334155',
          colorText: '#F1F5F9',
          colorTextSecondary: '#94A3B8',
        },
        components: {
          Button: {
            colorPrimary: '#3B82F6',
            algorithm: true,
          },
          Card: {
            colorBgContainer: '#1E293B',
            colorBorder: '#334155',
          },
          Input: {
            colorBgContainer: '#0F172A',
            colorBorder: '#334155',
          },
          Select: {
            colorBgContainer: '#0F172A',
            colorBgElevated: '#1E293B',
            colorBorder: '#334155',
          },
        },
      }}
    >
      <Router>
        <Routes>
          <Route path="/editor/:id" element={<EditorPage />} />
          <Route path="/preview/:id" element={<PreviewPage />} />
          
          <Route element={<MainLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/templates" element={<TemplateListPage />} />
            <Route path="/templates/:id" element={<TemplateDetailPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/profile"
              element={
                <PrivateRoute>
                  <ProfilePage />
                </PrivateRoute>
              }
            />
            <Route
              path="/upload"
              element={
                <PrivateRoute>
                  <UploadPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <AdminRoute>
                  <AdminPage />
                </AdminRoute>
              }
            />
          </Route>
        </Routes>
      </Router>
    </ConfigProvider>
  );
}

export default App;
