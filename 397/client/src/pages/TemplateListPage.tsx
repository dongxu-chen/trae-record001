import React, { useEffect, useState } from 'react';
import { Row, Col, Input, Select, Slider, Pagination, Spin, Empty, Button } from 'antd';
import { SearchOutlined, FilterOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { templateAPI, userAPI } from '../services/api';
import { Template, TemplateFilter } from '../types';
import TemplateCard from '../components/TemplateCard';
import { CATEGORIES, COMPLEXITY, SORT_OPTIONS } from '../utils/constants';
import { debounce } from '../utils/helpers';

const { Search } = Input;
const { Option } = Select;

const TemplateListPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ page: 1, limit: 12, total: 0, pages: 0 });
  const [filters, setFilters] = useState<TemplateFilter>({});
  const [favorites, setFavorites] = useState<string[]>([]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const newFilters: TemplateFilter = {};
    params.forEach((value, key) => {
      (newFilters as any)[key] = value;
    });
    setFilters(newFilters);
  }, [location.search]);

  useEffect(() => {
    fetchTemplates();
  }, [filters]);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await templateAPI.getTemplates(filters);
      setTemplates(response.templates);
      setPagination(response.pagination);
    } catch (error) {
      console.error('获取模板列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = debounce((value: string) => {
    const newFilters = { ...filters, search: value, page: 1 };
    navigate(`/templates?${new URLSearchParams(newFilters as any).toString()}`);
  }, 300);

  const handleFilterChange = (key: string, value: any) => {
    const newFilters = { ...filters, [key]: value, page: 1 };
    if (!value) delete (newFilters as any)[key];
    navigate(`/templates?${new URLSearchParams(newFilters as any).toString()}`);
  };

  const handlePageChange = (page: number) => {
    const newFilters = { ...filters, page };
    navigate(`/templates?${new URLSearchParams(newFilters as any).toString()}`);
  };

  const handleFavorite = async (id: string) => {
    try {
      if (favorites.includes(id)) {
        await userAPI.removeFavorite(id);
        setFavorites(favorites.filter(f => f !== id));
      } else {
        await userAPI.addFavorite(id);
        setFavorites([...favorites, id]);
      }
    } catch (error) {
      console.error('收藏操作失败:', error);
    }
  };

  return (
    <div className="flex gap-6">
      <div className="w-64 flex-shrink-0">
        <div className="sticky top-24 space-y-6 p-6 rounded-2xl" style={{ background: '#1E293B' }}>
          <div className="flex items-center gap-2">
            <FilterOutlined className="text-blue-400" />
            <h3 className="text-lg font-semibold text-white">筛选条件</h3>
          </div>

          <div>
            <label className="block text-slate-400 text-sm mb-2">行业分类</label>
            <Select
              style={{ width: '100%' }}
              placeholder="选择分类"
              allowClear
              value={filters.category || undefined}
              onChange={(value) => handleFilterChange('category', value)}
            >
              {CATEGORIES.map(cat => (
                <Option key={cat.value} value={cat.value}>{cat.label}</Option>
              ))}
            </Select>
          </div>

          <div>
            <label className="block text-slate-400 text-sm mb-2">复杂度</label>
            <Select
              style={{ width: '100%' }}
              placeholder="选择复杂度"
              allowClear
              value={filters.complexity || undefined}
              onChange={(value) => handleFilterChange('complexity', value)}
            >
              {COMPLEXITY.map(c => (
                <Option key={c.value} value={c.value}>{c.label}</Option>
              ))}
            </Select>
          </div>

          <div>
            <label className="block text-slate-400 text-sm mb-2">最低评分</label>
            <Slider
              min={0}
              max={5}
              step={0.5}
              value={filters.minRating || 0}
              onChange={(value) => handleFilterChange('minRating', value)}
              tooltip={{ formatter: (value) => `${value} 分` }}
            />
          </div>

          <div>
            <label className="block text-slate-400 text-sm mb-2">排序方式</label>
            <Select
              style={{ width: '100%' }}
              placeholder="选择排序"
              value={filters.sort || 'createdAt'}
              onChange={(value) => handleFilterChange('sort', value)}
            >
              {SORT_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </div>

          <Button
            type="default"
            block
            onClick={() => {
              navigate('/templates');
              setFilters({});
            }}
          >
            重置筛选
          </Button>
        </div>
      </div>

      <div className="flex-1">
        <div className="mb-6 flex items-center justify-between">
          <Search
            placeholder="搜索模板..."
            allowClear
            enterButton={<SearchOutlined />}
            size="large"
            onSearch={handleSearch}
            onChange={(e) => handleSearch(e.target.value)}
            defaultValue={filters.search}
            style={{ maxWidth: 400 }}
          />
          <span className="text-slate-400">
            共 <span className="text-white font-semibold">{pagination.total}</span> 个模板
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Spin size="large" />
          </div>
        ) : templates.length > 0 ? (
          <>
            <Row gutter={[24, 24]}>
              {templates.map((template) => (
                <Col xs={24} sm={12} lg={8} xl={6} key={template._id}>
                  <TemplateCard
                    template={template}
                    onFavorite={handleFavorite}
                    isFavorite={favorites.includes(template._id)}
                  />
                </Col>
              ))}
            </Row>
            <div className="flex justify-center mt-8">
              <Pagination
                current={pagination.page}
                total={pagination.total}
                pageSize={pagination.limit}
                onChange={handlePageChange}
              />
            </div>
          </>
        ) : (
          <Empty description="暂无匹配的模板" style={{ marginTop: 80 }} />
        )}
      </div>
    </div>
  );
};

export default TemplateListPage;
