import { ConfigProvider, Layout, Spin, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { Outlet } from 'react-router-dom';
import { useAppStore } from '@/store/useAppStore';
import Sidebar from './Sidebar';
import Header from './Header';

const { Content } = Layout;

export default function MainLayout() {
  const { theme: themeMode, loading } = useAppStore();
  const isDark = themeMode === 'dark';

  const themeConfig = {
    algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: {
      colorPrimary: '#165DFF',
      borderRadius: 8,
    },
    components: {
      Layout: {
        headerBg: isDark ? '#001529' : '#ffffff',
        siderBg: isDark ? '#001529' : '#ffffff',
        bodyBg: isDark ? '#141414' : '#f5f7fa',
      },
      Menu: {
        itemColor: isDark ? 'rgba(255, 255, 255, 0.65)' : '#595959',
        itemSelectedColor: '#165DFF',
        itemSelectedBg: isDark ? 'rgba(22, 93, 255, 0.1)' : '#e6f0ff',
        itemHoverBg: isDark ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.04)',
        itemHoverColor: isDark ? '#ffffff' : '#262626',
      },
    },
  };

  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      <Spin
        spinning={loading}
        tip="加载中..."
        style={{ maxHeight: 'none' }}
      >
        <Layout style={{ minHeight: '100vh' }}>
          <Sidebar />
          <Layout>
            <Header />
            <Content
              style={{
                margin: '24px',
                padding: '24px',
                borderRadius: 8,
                minHeight: 'calc(100vh - 112px)',
              }}
            >
              <Outlet />
            </Content>
          </Layout>
        </Layout>
      </Spin>
    </ConfigProvider>
  );
}
