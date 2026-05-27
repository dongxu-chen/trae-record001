import React, { useEffect, useState } from 'react';
import { Row, Col, Button, Input, Carousel, Statistic, Tag } from 'antd';
import { SearchOutlined, ArrowRightOutlined, LineChartOutlined, DollarOutlined, WalletOutlined, CloudServerOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { templateAPI } from '../services/api';
import { Template } from '../types';
import TemplateCard from '../components/TemplateCard';
import RecommendList from '../components/RecommendList';
import { CATEGORIES } from '../utils/constants';
import { formatNumber } from '../utils/helpers';

const { Search } = Input;

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await templateAPI.getTemplates({ limit: 8, sort: 'downloadCount', order: 'desc' });
      setTemplates(response.templates);
    } catch (error) {
      console.error('获取模板失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    if (value) {
      navigate(`/templates?search=${value}`);
    } else {
      navigate('/templates');
    }
  };

  const categoryIcons: Record<string, React.ReactNode> = {
    operation: <LineChartOutlined />,
    sales: <DollarOutlined />,
    finance: <WalletOutlined />,
    ops: <CloudServerOutlined />
  };

  return (
    <div className="space-y-12">
      <section className="relative overflow-hidden rounded-3xl py-16 px-12" style={{
        background: 'linear-gradient(135deg, #1E3A8A 0%, #312E81 50%, #4C1D95 100%)'
      }}>
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/20 rounded-full blur-3xl" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold text-white mb-6">
            专业仪表板模板市场
          </h1>
          <p className="text-xl text-blue-200 mb-8">
            精选运营、销售、财务、运维等多行业专业模板，一键应用，快速搭建企业级数据可视化
          </p>
          <div className="max-w-2xl mx-auto mb-8">
            <Search
              size="large"
              placeholder="搜索模板、标签或行业..."
              enterButton={<Button type="primary" icon={<SearchOutlined />}>搜索</Button>}
              onSearch={handleSearch}
              className="search-input"
            />
          </div>
          <div className="flex items-center justify-center gap-8">
            <Statistic title="模板数量" value={500} suffix="+" className="text-white" />
            <Statistic title="下载次数" value={formatNumber(50000)} className="text-white" />
            <Statistic title="活跃用户" value={formatNumber(10000)} className="text-white" />
          </div>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">行业分类</h2>
        </div>
        <Row gutter={[24, 24]}>
          {CATEGORIES.map((category) => (
            <Col xs={24} sm={12} lg={6} key={category.value}>
              <div
                className="cursor-pointer p-6 rounded-2xl transition-all duration-300 hover:scale-105 hover:shadow-xl"
                style={{
                  background: `linear-gradient(135deg, ${category.color}20 0%, ${category.color}10 100%)`,
                  border: `1px solid ${category.color}40`
                }}
                onClick={() => navigate(`/templates?category=${category.value}`)}
              >
                <div
                  className="w-14 h-14 rounded-xl flex items-center justify-center mb-4 text-2xl"
                  style={{ background: `${category.color}30`, color: category.color }}
                >
                  {categoryIcons[category.value]}
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">{category.label}</h3>
                <p className="text-slate-400 text-sm">
                  {category.value === 'operation' && '用户增长、活跃度、转化率分析'}
                  {category.value === 'sales' && '业绩分析、渠道分布、销售漏斗'}
                  {category.value === 'finance' && '收支管理、预算跟踪、财务报表'}
                  {category.value === 'ops' && '服务器监控、性能指标、告警管理'}
                </p>
              </div>
            </Col>
          ))}
        </Row>
      </section>

      <RecommendList />

      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">热门模板</h2>
          <Button type="link" onClick={() => navigate('/templates')}>
            查看全部 <ArrowRightOutlined />
          </Button>
        </div>
        <Row gutter={[24, 24]}>
          {templates.slice(0, 4).map((template) => (
            <Col xs={24} sm={12} lg={6} key={template._id}>
              <TemplateCard template={template} />
            </Col>
          ))}
        </Row>
      </section>

      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">最新上架</h2>
          <Button type="link" onClick={() => navigate('/templates?sort=createdAt&order=desc')}>
            查看全部 <ArrowRightOutlined />
          </Button>
        </div>
        <Row gutter={[24, 24]}>
          {templates.slice(4, 8).map((template) => (
            <Col xs={24} sm={12} lg={6} key={template._id}>
              <TemplateCard template={template} />
            </Col>
          ))}
        </Row>
      </section>

      <section className="py-12 px-8 rounded-3xl" style={{ background: '#1E293B' }}>
        <Row align="middle" gutter={48}>
          <Col xs={24} lg={12}>
            <h2 className="text-3xl font-bold text-white mb-4">
              成为创作者，分享你的设计
            </h2>
            <p className="text-slate-400 mb-6">
              上传你的仪表板模板，帮助更多企业快速搭建数据可视化。获得下载收益和社区认可。
            </p>
            <Button type="primary" size="large" onClick={() => navigate('/upload')}>
              立即上传模板
            </Button>
          </Col>
          <Col xs={24} lg={12}>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-6 rounded-xl bg-slate-800/50">
                <Statistic title="最高收益" prefix="¥" value={5000} />
              </div>
              <div className="p-6 rounded-xl bg-slate-800/50">
                <Statistic title="创作者数量" value={200} suffix="+" />
              </div>
              <div className="p-6 rounded-xl bg-slate-800/50">
                <Statistic title="平均评分" value={4.8} precision={1} />
              </div>
              <div className="p-6 rounded-xl bg-slate-800/50">
                <Statistic title="总分成" prefix="¥" value={formatNumber(100000)} />
              </div>
            </div>
          </Col>
        </Row>
      </section>
    </div>
  );
};

export default HomePage;
