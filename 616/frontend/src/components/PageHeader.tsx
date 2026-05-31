import React from 'react';
import { Breadcrumb, Typography, Space } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';

const { Title } = Typography;

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbItems?: Array<{
    title: string;
    path?: string;
  }>;
  extra?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  breadcrumbItems,
  extra,
}) => {
  const defaultBreadcrumb = [
    {
      title: (
        <Link to="/">
          <HomeOutlined />
          <span style={{ marginLeft: 8 }}>首页</span>
        </Link>
      ),
    },
    ...(breadcrumbItems?.map((item) => ({
      title: item.path ? (
        <Link to={item.path}>{item.title}</Link>
      ) : (
        item.title
      ),
    })) || []),
  ];

  return (
    <div style={{ marginBottom: 24 }}>
      <Breadcrumb items={defaultBreadcrumb} style={{ marginBottom: 16 }} />
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <Space direction="vertical" size={4}>
          <Title level={3} style={{ margin: 0 }}>
            {title}
          </Title>
          {subtitle && (
            <Typography.Text type="secondary">
              {subtitle}
            </Typography.Text>
          )}
        </Space>
        {extra && <div>{extra}</div>}
      </div>
    </div>
  );
};

export default PageHeader;
