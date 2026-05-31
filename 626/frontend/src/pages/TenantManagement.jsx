import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  message,
  Popconfirm,
  Tag,
  Steps,
  Alert,
  Descriptions,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, TransferOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
import { tenantApi } from '../services/api';

const { Option } = Select;

const TenantManagement = () => {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [transferModalVisible, setTransferModalVisible] = useState(false);
  const [editingTenant, setEditingTenant] = useState(null);
  const [form] = Form.useForm();
  const [transferForm] = Form.useForm();

  const [tccStep, setTccStep] = useState(0);
  const [tccTransaction, setTccTransaction] = useState(null);
  const [tccLoading, setTccLoading] = useState(false);

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    setLoading(true);
    try {
      const result = await tenantApi.list();
      setTenants(result.data || []);
    } catch (error) {
      message.error('加载租户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingTenant(null);
    form.resetFields();
    form.setFieldsValue({
      enabled: true,
      warningThreshold: 0.8,
      overLimitStrategy: 'REJECT',
    });
    setModalVisible(true);
  };

  const handleEdit = (tenant) => {
    setEditingTenant(tenant);
    form.setFieldsValue(tenant);
    setModalVisible(true);
  };

  const handleDelete = async (tenantId) => {
    try {
      await tenantApi.delete(tenantId);
      message.success('删除成功');
      loadTenants();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingTenant) {
        await tenantApi.update({ ...editingTenant, ...values });
        message.success('更新成功');
      } else {
        await tenantApi.create(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      loadTenants();
    } catch (error) {
      if (error.errorFields) {
        return;
      }
      message.error(editingTenant ? '更新失败' : '创建失败');
    }
  };

  const handleOpenTransfer = () => {
    transferForm.resetFields();
    setTccStep(0);
    setTccTransaction(null);
    setTransferModalVisible(true);
  };

  const handleTccTry = async () => {
    try {
      const values = await transferForm.validateFields();
      setTccLoading(true);
      const result = await tenantApi.transferTry(values);
      if (result.code === 200) {
        setTccTransaction(result.data);
        setTccStep(1);
        message.success('TCC Try成功，资源已预留');
      } else {
        message.error(result.message || 'TCC Try失败');
      }
    } catch (error) {
      if (!error.errorFields) {
        message.error('资源预留失败：' + (error.response?.data?.message || '请稍后重试'));
      }
    } finally {
      setTccLoading(false);
    }
  };

  const handleTccConfirm = async () => {
    if (!tccTransaction) return;
    setTccLoading(true);
    try {
      const result = await tenantApi.transferConfirm({ transactionId: tccTransaction.transactionId });
      if (result.code === 200) {
        setTccStep(2);
        message.success('TCC Confirm成功，配额转移已确认');
        loadTenants();
      } else {
        message.error(result.message || '确认失败');
      }
    } catch (error) {
      message.error('确认失败');
    } finally {
      setTccLoading(false);
    }
  };

  const handleTccCancel = async () => {
    if (!tccTransaction) return;
    setTccLoading(true);
    try {
      const result = await tenantApi.transferCancel({ transactionId: tccTransaction.transactionId });
      if (result.code === 200) {
        setTccStep(3);
        message.warning('TCC Cancel成功，配额转移已回滚');
      } else {
        message.error(result.message || '回滚失败');
      }
    } catch (error) {
      message.error('回滚失败');
    } finally {
      setTccLoading(false);
    }
  };

  const columns = [
    {
      title: '租户ID',
      dataIndex: 'tenantId',
      key: 'tenantId',
    },
    {
      title: '租户名称',
      dataIndex: 'tenantName',
      key: 'tenantName',
    },
    {
      title: '分钟限额',
      dataIndex: 'minuteLimit',
      key: 'minuteLimit',
    },
    {
      title: '小时限额',
      dataIndex: 'hourLimit',
      key: 'hourLimit',
    },
    {
      title: '日限额',
      dataIndex: 'dayLimit',
      key: 'dayLimit',
    },
    {
      title: '超限策略',
      dataIndex: 'overLimitStrategy',
      key: 'overLimitStrategy',
      render: (strategy) => {
        const colors = { REJECT: 'red', DOWNGRADE: 'orange', QUEUE: 'blue' };
        const labels = { REJECT: '拒绝', DOWNGRADE: '降级', QUEUE: '排队' };
        return <Tag color={colors[strategy]}>{labels[strategy]}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled) => (
        <Tag color={enabled ? 'green' : 'default'}>{enabled ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除该租户吗?"
            onConfirm={() => handleDelete(record.tenantId)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const getTccStepStatus = () => {
    if (tccStep === 0) return 'process';
    if (tccStep === 1) return 'process';
    if (tccStep === 2) return 'finish';
    if (tccStep === 3) return 'error';
    return 'wait';
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加租户
        </Button>
        <Button icon={<TransferOutlined />} onClick={handleOpenTransfer}>
          TCC配额转移
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={tenants}
        rowKey="tenantId"
        loading={loading}
      />

      <Modal
        title={editingTenant ? '编辑租户' : '添加租户'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="tenantId"
            label="租户ID"
            rules={[{ required: true, message: '请输入租户ID' }]}
          >
            <Input disabled={!!editingTenant} placeholder="请输入租户ID" />
          </Form.Item>
          <Form.Item
            name="tenantName"
            label="租户名称"
            rules={[{ required: true, message: '请输入租户名称' }]}
          >
            <Input placeholder="请输入租户名称" />
          </Form.Item>
          <Form.Item name="notificationEmail" label="通知邮箱">
            <Input placeholder="请输入预警通知邮箱" />
          </Form.Item>
          <Form.Item label="配额限制">
            <Space>
              <Form.Item
                name="minuteLimit"
                noStyle
                rules={[{ required: true, message: '请输入分钟限额' }]}
              >
                <InputNumber min={1} placeholder="分钟限额" addonBefore="分钟" />
              </Form.Item>
              <Form.Item
                name="hourLimit"
                noStyle
                rules={[{ required: true, message: '请输入小时限额' }]}
              >
                <InputNumber min={1} placeholder="小时限额" addonBefore="小时" />
              </Form.Item>
              <Form.Item
                name="dayLimit"
                noStyle
                rules={[{ required: true, message: '请输入日限额' }]}
              >
                <InputNumber min={1} placeholder="日限额" addonBefore="日" />
              </Form.Item>
            </Space>
          </Form.Item>
          <Form.Item
            name="overLimitStrategy"
            label="超限策略"
            rules={[{ required: true, message: '请选择超限策略' }]}
          >
            <Select>
              <Option value="REJECT">拒绝请求</Option>
              <Option value="DOWNGRADE">降级处理</Option>
              <Option value="QUEUE">排队等待</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="warningThreshold"
            label="预警阈值"
            rules={[{ required: true, message: '请输入预警阈值' }]}
          >
            <InputNumber min={0} max={1} step={0.1} addonAfter="%" formatter={value => `${value * 100}`} parser={value => value.replace('%', '') / 100} />
          </Form.Item>
          <Form.Item name="enabled" label="启用状态" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="TCC配额转移"
        open={transferModalVisible}
        onCancel={() => { setTransferModalVisible(false); setTccStep(0); setTccTransaction(null); }}
        width={700}
        footer={null}
      >
        <Steps
          current={tccStep}
          status={getTccStepStatus()}
          items={[
            { title: 'Try', description: '预留资源' },
            { title: 'Confirm/Cancel', description: '确认或回滚' },
            { title: '完成' },
          ]}
          style={{ marginBottom: 24 }}
        />

        {tccStep === 0 && (
          <Form form={transferForm} layout="vertical">
            <Form.Item
              name="fromTenantId"
              label="源租户"
              rules={[{ required: true, message: '请选择源租户' }]}
            >
              <Select placeholder="选择源租户">
                {tenants.map(t => (
                  <Option key={t.tenantId} value={t.tenantId}>
                    {t.tenantName}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item
              name="toTenantId"
              label="目标租户"
              rules={[{ required: true, message: '请选择目标租户' }]}
            >
              <Select placeholder="选择目标租户">
                {tenants.map(t => (
                  <Option key={t.tenantId} value={t.tenantId}>
                    {t.tenantName}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item
              name="granularity"
              label="粒度"
              rules={[{ required: true, message: '请选择粒度' }]}
            >
              <Select>
                <Option value="minute">分钟</Option>
                <Option value="hour">小时</Option>
                <Option value="day">日</Option>
              </Select>
            </Form.Item>
            <Form.Item
              name="amount"
              label="转移数量"
              rules={[{ required: true, message: '请输入转移数量' }]}
            >
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Button type="primary" loading={tccLoading} onClick={handleTccTry} block>
              Try - 预留资源
            </Button>
          </Form>
        )}

        {tccStep === 1 && tccTransaction && (
          <div>
            <Alert
              message="资源已预留，等待确认或取消"
              description={`事务ID: ${tccTransaction.transactionId}`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Descriptions bordered size="small" column={1} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="源租户">{tccTransaction.fromTenantId}</Descriptions.Item>
              <Descriptions.Item label="目标租户">{tccTransaction.toTenantId}</Descriptions.Item>
              <Descriptions.Item label="粒度">{tccTransaction.granularity}</Descriptions.Item>
              <Descriptions.Item label="数量">{tccTransaction.amount}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color="blue">{tccTransaction.status}</Tag>
              </Descriptions.Item>
            </Descriptions>
            <Space style={{ width: '100%', justifyContent: 'center' }}>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                loading={tccLoading}
                onClick={handleTccConfirm}
              >
                Confirm - 确认转移
              </Button>
              <Button
                danger
                icon={<CloseOutlined />}
                loading={tccLoading}
                onClick={handleTccCancel}
              >
                Cancel - 回滚
              </Button>
            </Space>
          </div>
        )}

        {tccStep === 2 && (
          <div>
            <Alert
              message="配额转移成功！"
              description="TCC事务已确认，配额已从源租户转移到目标租户。"
              type="success"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Button onClick={() => { setTransferModalVisible(false); setTccStep(0); }} block>
              关闭
            </Button>
          </div>
        )}

        {tccStep === 3 && (
          <div>
            <Alert
              message="配额转移已回滚"
              description="TCC事务已取消，源租户的配额已恢复。"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Button onClick={() => { setTransferModalVisible(false); setTccStep(0); }} block>
              关闭
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TenantManagement;
