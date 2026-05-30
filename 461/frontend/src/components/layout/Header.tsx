import { Layout, Button, Avatar, Dropdown, Space, Badge } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  SunOutlined,
  MoonOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useAppStore } from '@/store/useAppStore';

const { Header: AntHeader } = Layout;

export default function Header() {
  const { collapsed, toggleCollapsed, theme, toggleTheme } = useAppStore();

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  const headerBg = theme === 'dark' ? '#001529' : '#ffffff';
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937';
  const borderColor = theme === 'dark' ? '#303030' : '#e5e7eb';

  return (
    <AntHeader
      style={{
        padding: '0 24px',
        background: headerBg,
        borderBottom: `1px solid ${borderColor}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: 64,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={toggleCollapsed}
          style={{
            fontSize: '16px',
            width: 64,
            height: 64,
            color: textColor,
          }}
        />
        <h1
          style={{
            margin: 0,
            fontSize: 18,
            fontWeight: 600,
            color: textColor,
          }}
        >
          API版本管理系统
        </h1>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Button
          type="text"
          icon={theme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
          onClick={toggleTheme}
          style={{ color: textColor }}
        />

        <Badge count={3} size="small">
          <Button type="text" icon={<BellOutlined />} style={{ color: textColor }} />
        </Badge>

        <Dropdown
          menu={{ items: userMenuItems }}
          placement="bottomRight"
          arrow
        >
          <Space style={{ cursor: 'pointer', padding: '0 8px', borderRadius: 8 }}>
            <Avatar
              size="small"
              style={{ backgroundColor: '#165DFF' }}
              icon={<UserOutlined />}
            />
            <span style={{ color: textColor }}>管理员</span>
          </Space>
        </Dropdown>
      </div>
    </AntHeader>
  );
}
