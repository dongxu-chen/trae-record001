import { useState, useEffect } from 'react';
import { Layout, Menu, Badge, Avatar, Dropdown, Space } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Gauge,
  GitBranch,
  WarningCircle,
  SlidersHorizontal,
  LineChart,
  FileText,
  Settings,
  Bell,
  RefreshCw,
  Database,
} from '@phosphor-icons/react';
import { useAnalysisStore } from '@/stores/analysisStore';

const { Header, Sider } = Layout;

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const { fetchHealth, healthStatus, overallStatistics, loading } = useAnalysisStore();

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const menuItems = [
    {
      key: '/',
      icon: <Gauge size={20} />,
      label: '仪表盘',
    },
    {
      key: '/clustering',
      icon: <GitBranch size={20} />,
      label: '告警聚类',
    },
    {
      key: '/rules',
      icon: <WarningCircle size={20} />,
      label: (
        <Space>
          低效规则
          {overallStatistics?.inefficientRulesCount && (
            <Badge
              count={overallStatistics.inefficientRulesCount}
              size="small"
              color="#EF4444"
            />
          )}
        </Space>
      ),
    },
    {
      key: '/optimizer',
      icon: <SlidersHorizontal size={20} />,
      label: '优化建议',
    },
    {
      key: '/evaluator',
      icon: <LineChart size={20} />,
      label: '效果评估',
    },
    {
      key: '/report',
      icon: <FileText size={20} />,
      label: '分析报告',
    },
    {
      key: '/settings',
      icon: <Settings size={20} />,
      label: '系统设置',
    },
  ];

  const userMenu = {
    items: [
      {
        key: '1',
        label: '个人设置',
      },
      {
        key: '2',
        label: '帮助文档',
      },
      {
        type: 'divider' as const,
      },
      {
        key: '3',
        label: '退出登录',
      },
    ],
  };

  return (
    <Layout className="h-screen">
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={240}
        className="border-r border-dark-border"
      >
        <div className="h-16 flex items-center px-4 border-b border-dark-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-info flex items-center justify-center">
              <Database size={22} className="text-white" />
            </div>
            {!collapsed && (
              <div>
                <div className="font-display font-bold text-lg text-white leading-tight">
                  AlertOpt
                </div>
                <div className="text-xs text-gray-400">告警规则优化平台</div>
              </div>
            )}
          </div>
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          className="mt-2 border-0"
        />

        {!collapsed && (
          <div className="absolute bottom-4 left-4 right-4">
            <div className="p-3 rounded-xl bg-dark-bg border border-dark-border">
              <div className="flex items-center gap-2 text-sm">
                <div
                  className={`w-2 h-2 rounded-full ${
                    healthStatus?.skywalkingConnected ? 'bg-success' : 'bg-warning'
                  }`}
                />
                <span className="text-gray-400">
                  {healthStatus?.mockMode ? '演示模式' : 'SkyWalking 已连接'}
                </span>
              </div>
              {loading.fullReport && (
                <div className="mt-2 flex items-center gap-2 text-xs text-primary">
                  <RefreshCw size={12} className="animate-spin" />
                  <span>分析中...</span>
                </div>
              )}
            </div>
          </div>
        )}
      </Sider>

      <Layout>
        <Header className="h-16 px-6 flex items-center justify-between border-b border-dark-border bg-dark-surface">
          <div className="flex items-center gap-4">
            <h1 className="font-display text-xl font-semibold text-white">
              {menuItems.find((item) => item.key === location.pathname)?.label?.toString() || '仪表盘'}
            </h1>
          </div>

          <div className="flex items-center gap-4">
            <Badge count={3} size="small" color="#F59E0B">
              <button className="p-2 rounded-lg hover:bg-dark-border transition-colors text-gray-400 hover:text-white">
                <Bell size={20} />
              </button>
            </Badge>

            <Dropdown menu={userMenu} placement="bottomRight">
              <div className="flex items-center gap-3 cursor-pointer hover:bg-dark-border rounded-lg p-1 transition-colors">
                <Avatar size={36} className="bg-gradient-to-br from-primary to-info">
                  <span className="font-semibold">SRE</span>
                </Avatar>
                <div className="hidden md:block">
                  <div className="text-sm font-medium text-white">运维工程师</div>
                  <div className="text-xs text-gray-400">SRE Team</div>
                </div>
              </div>
            </Dropdown>
          </div>
        </Header>

        {children}
      </Layout>
    </Layout>
  );
};

export default AppLayout;
