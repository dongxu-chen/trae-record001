import { Layout, Menu } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  GitBranch,
  Route,
  GitCompare,
  FileText,
  Rocket,
} from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';

const { Sider } = Layout;

interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  path: string;
}

const menuItems: MenuItem[] = [
  {
    key: 'dashboard',
    icon: <LayoutDashboard size={18} />,
    label: '仪表盘',
    path: '/dashboard',
  },
  {
    key: 'versions',
    icon: <GitBranch size={18} />,
    label: '版本管理',
    path: '/versions',
  },
  {
    key: 'route',
    icon: <Route size={18} />,
    label: '路由配置',
    path: '/route',
  },
  {
    key: 'compare',
    icon: <GitCompare size={18} />,
    label: '版本对比',
    path: '/compare',
  },
  {
    key: 'swagger',
    icon: <FileText size={18} />,
    label: 'Swagger文档',
    path: '/swagger',
  },
  {
    key: 'guide',
    icon: <Rocket size={18} />,
    label: '客户端引导',
    path: '/guide',
  },
];

export default function Sidebar() {
  const { collapsed, setCollapsed, theme } = useAppStore();
  const location = useLocation();
  const navigate = useNavigate();

  const selectedKey = menuItems.find((item) => location.pathname.startsWith(item.path))?.key || 'dashboard';

  const handleMenuClick = ({ key }: { key: string }) => {
    const item = menuItems.find((i) => i.key === key);
    if (item) {
      navigate(item.path);
    }
  };

  return (
    <Sider
      trigger={null}
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      theme={theme}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'sticky',
        top: 0,
        left: 0,
      }}
      width={240}
    >
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: theme === 'dark' ? '#001529' : '#ffffff',
          borderBottom: `1px solid ${theme === 'dark' ? '#303030' : '#e5e7eb'}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #165DFF 0%, #4080FF 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 'bold',
              fontSize: 14,
            }}
          >
            API
          </div>
          {!collapsed && (
            <span
              style={{
                fontSize: 16,
                fontWeight: 600,
                color: theme === 'dark' ? '#ffffff' : '#1f2937',
              }}
            >
              API版本管理
            </span>
          )}
        </div>
      </div>

      <Menu
        theme={theme}
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems.map((item) => ({
          key: item.key,
          icon: item.icon,
          label: item.label,
        }))}
        onClick={handleMenuClick}
        style={{
          borderRight: 'none',
          marginTop: 16,
        }}
      />
    </Sider>
  );
}
