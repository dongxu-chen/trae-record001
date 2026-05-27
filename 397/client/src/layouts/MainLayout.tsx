import React, { useState } from 'react';
import { Layout, Menu, Button, Dropdown, Avatar, Badge } from 'antd';
import {
  HomeOutlined, AppstoreOutlined, UploadOutlined, UserOutlined, LogoutOutlined, HeartOutlined, DownOutlined, SettingOutlined } from '@ant-design/icons';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../store';
import { logout } from '../store';

const { Header, Content, Footer } = Layout;

const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const { isAuthenticated, user } = useSelector((state: RootState) => state.auth);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  const getUserMenu = () => {
    const menu = [
      {
        key: 'profile',
        icon: <UserOutlined />,
        label: '个人中心',
        onClick: () => navigate('/profile')
      },
      {
        key: 'favorites',
        icon: <HeartOutlined />,
        label: '我的收藏',
        onClick: () => navigate('/profile?tab=favorites')
      }
    ];

    if (user?.role === 'admin') {
      menu.push({
        key: 'admin',
        icon: <SettingOutlined />,
        label: '管理后台',
        onClick: () => navigate('/admin')
      });
    }

    menu.push({
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout
    });

    return menu;
  };

  const navItems = [
    { key: '/', label: <Link to="/">首页</Link>, icon: <HomeOutlined /> },
    { key: '/templates', label: <Link to="/templates">模板市场</Link>, icon: <AppstoreOutlined /> }
  ];

  return (
    <Layout className="min-h-screen">
      <Header className="sticky top-0 z-50 px-8" style={{ background: '#0F172A', borderBottom: '1px solid #1E293B' }}>
        <div className="flex items-center justify-between h-full">
          <div className="flex items-center gap-8">
            <Link to="/" className="text-2xl font-bold text-white flex items-center gap-2">
              <span className="bg-gradient-to-r from-blue-500 to-indigo-600 bg-clip-text text-transparent">
                Dashboard
              </span>
              <span className="text-orange-500">Market</span>
            </Link>
            <Menu
              theme="dark"
              mode="horizontal"
              selectedKeys={[location.pathname]}
              items={navItems}
              className="bg-transparent border-0 flex-1 min-w-0"
            />
          </div>
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate('/upload')}>
                  上传模板
                </Button>
                <Dropdown menu={{ items: getUserMenu() }}>
                  <div className="flex items-center gap-2 cursor-pointer text-white hover:text-blue-400 transition-colors">
                    <Avatar size="small" icon={<UserOutlined />} />
                    <span>{user?.username}</span>
                    <DownOutlined />
                  </div>
                </Dropdown>
              </>
            ) : (
              <>
                <Button type="text" className="text-white" onClick={() => navigate('/login')}>
                  登录
                </Button>
                <Button type="primary" onClick={() => navigate('/register')}>
                  注册
                </Button>
              </>
            )}
          </div>
        </div>
      </Header>
      <Content className="px-8 py-6" style={{ background: '#0F172A' }}>
        {children}
      </Content>
      <Footer className="text-center" style={{ background: '#0F172A', borderTop: '1px solid #1E293B', color: '#94A3B8' }}>
        Dashboard Market ©2024 专业仪表板模板市场
      </Footer>
    </Layout>
  );
};

export default MainLayout;
