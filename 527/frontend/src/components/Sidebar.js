import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';

const SidebarContainer = styled.aside`
  width: 250px;
  background-color: var(--bg-secondary);
  position: fixed;
  height: 100vh;
  left: 0;
  top: 0;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
`;

const Logo = styled.div`
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
  
  h1 {
    font-size: 18px;
    font-weight: 700;
    color: var(--accent-primary);
    display: flex;
    align-items: center;
    gap: 10px;
  }
`;

const Nav = styled.nav`
  padding: 16px 0;
  flex: 1;
`;

const NavItem = styled(Link)`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  color: ${props => props.active ? 'var(--text-primary)' : 'var(--text-secondary)'};
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s ease;
  background-color: ${props => props.active ? 'var(--bg-tertiary)' : 'transparent'};
  border-left: 3px solid ${props => props.active ? 'var(--accent-primary)' : 'transparent'};
  
  &:hover {
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
  }
  
  svg {
    width: 20px;
    height: 20px;
  }
`;

const Footer = styled.div`
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-secondary);
`;

const Sidebar = () => {
  const location = useLocation();
  
  const isActive = (path) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <SidebarContainer>
      <Logo>
        <h1>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
          </svg>
          标注工具
        </h1>
      </Logo>
      
      <Nav>
        <NavItem to="/" active={isActive('/') ? 1 : 0}>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
          </svg>
          仪表盘
        </NavItem>
        
        <NavItem to="/tasks" active={isActive('/tasks') ? 1 : 0}>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
          </svg>
          任务管理
        </NavItem>
        
        <NavItem to="/templates" active={isActive('/templates') ? 1 : 0}>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M4 4h16v4H4V4zm0 6h16v4H4v-4zm0 6h16v4H4v-4zm2-10v2h12V6H6zm0 6v2h12v-2H6zm0 6v2h12v-2H6z"/>
          </svg>
          模板库
        </NavItem>
      </Nav>
      
      <div style={{ borderTop: '1px solid var(--border-color)', padding: '16px 0' }}>
        <div style={{ padding: '0 24px 8px', fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: '600' }}>
          数据分析
        </div>
        <NavItem to="#" onClick={(e) => { e.preventDefault(); alert('请先选择一个任务'); }} active={0}>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
          </svg>
          质量评分
        </NavItem>
        <NavItem to="#" onClick={(e) => { e.preventDefault(); alert('请先选择一个任务'); }} active={0}>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 5h-2V3H7v2H5c-1.1 0-2 .9-2 2v1c0 2.55 1.92 4.63 4.39 4.94.63 1.5 1.98 2.63 3.61 2.96V19H7v2h10v-2h-4v-3.1c1.63-.33 2.98-1.46 3.61-2.96C19.08 12.63 21 10.55 21 8V7c0-1.1-.9-2-2-2zM5 8V7h2v3.82C5.84 10.4 5 9.3 5 8zm14 0c0 1.3-.84 2.4-2 2.82V7h2v1z"/>
          </svg>
          成就中心
        </NavItem>
      </div>
      
      <Footer>
        v1.0.0 | 信息抽取标注平台
      </Footer>
    </SidebarContainer>
  );
};

export default Sidebar;
