import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Row,
  Col,
  Statistic,
  Tag,
  Tabs,
  Popconfirm,
} from 'antd';
import {
  ShoppingOutlined,
  DollarOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  ReloadOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { marketApi, tenantApi } from '../services/api';

const { Option } = Select;

const QuotaMarket = () => {
  const [granularity, setGranularity] = useState('minute');
  const [sellOrders, setSellOrders] = useState([]);
  const [buyOrders, setBuyOrders] = useState([]);
  const [trades, setTrades] = useState([]);
  const [myOrders, setMyOrders] = useState([]);
  const [stats, setStats] = useState({});
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState('');
  const [loading, setLoading] = useState(false);
  const [sellModalVisible, setSellModalVisible] = useState(false);
  const [buyModalVisible, setBuyModalVisible] = useState(false);
  const [sellForm] = Form.useForm();
  const [buyForm] = Form.useForm();

  useEffect(() => {
    loadTenants();
  }, []);

  useEffect(() => {
    if (selectedTenant) {
      loadAllData();
      const interval = setInterval(loadAllData, 5000);
      return () => clearInterval(interval);
    }
  }, [granularity, selectedTenant]);

  const loadTenants = async () => {
    try {
      const result = await tenantApi.list();
      const list = result.data || [];
      setTenants(list);
      if (list.length > 0) {
        setSelectedTenant(list[0].tenantId);
      }
    } catch (error) {
      message.error('加载租户失败');
    }
  };

  const loadAllData = async () => {
    if (!selectedTenant) return;
    setLoading(true);
    try {
      const [sellRes, buyRes, tradesRes, statsRes, myOrdersRes] = await Promise.all([
        marketApi.getSellOrderBook(granularity),
        marketApi.getBuyOrderBook(granularity),
        marketApi.getRecentTrades(granularity, 50),
        marketApi.getStats(granularity),
        marketApi.getMyOrders(selectedTenant),
      ]);
      setSellOrders(sellRes.data || []);
      setBuyOrders(buyRes.data || []);
      setTrades(tradesRes.data || []);
      setStats(statsRes.data || {});
      setMyOrders(myOrdersRes.data || []);
    } catch (error) {
      console.error('Load market data failed', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePlaceSell = async () => {
    try {
      const values = await sellForm.validateFields();
      await marketApi.placeSell({ tenantId: selectedTenant, ...values, granularity });
      message.success('挂单成功');
      setSellModalVisible(false);
      sellForm.resetFields();
      loadAllData();
    } catch (error) {
      if (!error.errorFields) {
        message.error(error.response?.data?.message || '挂单失败');
      }
    }
  };

  const handlePlaceBuy = async () => {
    try {
      const values = await buyForm.validateFields();
      await marketApi.placeBuy({ tenantId: selectedTenant, ...values, granularity });
      message.success('挂单成功');
      setBuyModalVisible(false);
      buyForm.resetFields();
      loadAllData();
    } catch (error) {
      if (!error.errorFields) {
        message.error(error.response?.data?.message || '挂单失败');
      }
    }
  };

  const handleCancelOrder = async (orderId) => {
    try {
      await marketApi.cancel(orderId);
      message.success('撤单成功');
      loadAllData();
    } catch (error) {
      message.error('撤单失败');
    }
  };

  const orderBookColumns = [
    { title: '价格', dataIndex: 'pricePerUnit', key: 'price', render: (p) => <b style={{ color: '#1890ff' }}>{p}</b> },
    { title: '数量', dataIndex: 'remainingAmount', key: 'amount' },
    { title: '租户', dataIndex: 'tenantName', key: 'tenant' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (s) => <Tag color={s === 'PENDING' ? 'blue' : 'green'}>{s}</Tag> },
  ];

  const tradeColumns = [
    { title: '时间', dataIndex: 'tradedAt', key: 'time' },
    { title: '价格', dataIndex: 'pricePerUnit', key: 'price', render: (p) => <Tag color="green">{p}</Tag> },
    { title: '数量', dataIndex: 'amount', key: 'amount' },
    { title: '卖方', dataIndex: 'sellerTenantId', key: 'seller' },
    { title: '买方', dataIndex: 'buyerTenantId', key: 'buyer' },
  ];

  const myOrderColumns = [
    { title: '类型', dataIndex: 'orderType', key: 'type', render: (t) => <Tag color={t === 'SELL' ? 'red' : 'green'}>{t === 'SELL' ? '卖出' : '买入'}</Tag> },
    { title: '粒度', dataIndex: 'granularity', key: 'granularity' },
    { title: '价格', dataIndex: 'pricePerUnit', key: 'price' },
    { title: '总数', dataIndex: 'totalAmount', key: 'total' },
    { title: '成交', dataIndex: 'filledAmount', key: 'filled' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (s) => {
      const colors = { PENDING: 'blue', PARTIAL: 'orange', FILLED: 'green', CANCELLED: 'default', EXPIRED: 'red' };
      return <Tag color={colors[s]}>{s}</Tag>;
    }},
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        record.status === 'PENDING' || record.status === 'PARTIAL' ? (
          <Popconfirm title="确定撤单？" onConfirm={() => handleCancelOrder(record.orderId)}>
            <Button type="link" danger size="small">撤单</Button>
          </Popconfirm>
        ) : null
      ),
    },
  ];

  const priceChange = stats.lastPrice && stats.bestBid ? ((stats.lastPrice - stats.bestBid) / stats.bestBid * 100).toFixed(2) : 0;

  const tabItems = [
    {
      key: 'orderbook',
      label: '订单簿',
      children: (
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Card title="卖单" size="small" extra={<Tag color="red">卖 {stats.sellCount || 0}</Tag>}>
              <Table columns={orderBookColumns} dataSource={sellOrders} rowKey="orderId" size="small" pagination={false} loading={loading} />
            </Card>
          </Col>
          <Col span={12}>
            <Card title="买单" size="small" extra={<Tag color="green">买 {stats.buyCount || 0}</Tag>}>
              <Table columns={orderBookColumns} dataSource={buyOrders} rowKey="orderId" size="small" pagination={false} loading={loading} />
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'trades',
      label: '成交记录',
      children: (
        <Card size="small">
          <Table columns={tradeColumns} dataSource={trades} rowKey="tradeId" size="small" loading={loading} pagination={{ pageSize: 10 }} />
        </Card>
      ),
    },
    {
      key: 'myorders',
      label: '我的订单',
      children: (
        <Card size="small">
          <Table columns={myOrderColumns} dataSource={myOrders} rowKey="orderId" size="small" loading={loading} pagination={{ pageSize: 10 }} />
        </Card>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Select value={selectedTenant} onChange={setSelectedTenant} style={{ width: '100%' }}>
              {tenants.map(t => (
                <Option key={t.tenantId} value={t.tenantId}>
                  {t.tenantName}
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={4}>
            <Select value={granularity} onChange={setGranularity} style={{ width: '100%' }}>
              <Option value="minute">分钟</Option>
              <Option value="hour">小时</Option>
              <Option value="day">日</Option>
            </Select>
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={loadAllData}>刷新</Button>
          </Col>
          <Col flex="auto" style={{ textAlign: 'right' }}>
            <Button type="primary" icon={<ArrowUpOutlined />} onClick={() => setSellModalVisible(true)}>
              卖出配额
            </Button>
            <Button icon={<ArrowDownOutlined />} onClick={() => setBuyModalVisible(true)} style={{ marginLeft: 8 }}>
              买入配额
            </Button>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Card size="small">
              <Statistic title="最新成交价" value={stats.lastPrice || 0} prefix={<DollarOutlined />} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="24h涨跌"
                value={priceChange}
                suffix="%"
                valueStyle={{ color: priceChange >= 0 ? '#52c41a' : '#f5222d' }}
                prefix={priceChange >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="24h成交量" value={stats.volume24h || 0} prefix={<ShoppingOutlined />} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="卖一价" value={stats.bestAsk || 0} valueStyle={{ color: '#f5222d' }} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="买一价" value={stats.bestBid || 0} valueStyle={{ color: '#52c41a' }} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="24h成交数" value={stats.tradeCount24h || 0} />
            </Card>
          </Col>
        </Row>

        <Tabs items={tabItems} />
      </Card>

      <Modal title="卖出配额" open={sellModalVisible} onOk={handlePlaceSell} onCancel={() => setSellModalVisible(false)}>
        <Form form={sellForm} layout="vertical">
          <Form.Item name="amount" label="卖出数量" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="pricePerUnit" label="单价" rules={[{ required: true }]}>
            <InputNumber min={0.01} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="expireMinutes" label="有效期(分钟)" initialValue={1440}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="买入配额" open={buyModalVisible} onOk={handlePlaceBuy} onCancel={() => setBuyModalVisible(false)}>
        <Form form={buyForm} layout="vertical">
          <Form.Item name="amount" label="买入数量" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="pricePerUnit" label="单价" rules={[{ required: true }]}>
            <InputNumber min={0.01} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="expireMinutes" label="有效期(分钟)" initialValue={1440}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};

export default QuotaMarket;
