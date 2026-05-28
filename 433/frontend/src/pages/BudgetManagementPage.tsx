import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Spin,
  Alert,
  Button,
  Space,
  InputNumber,
  Tag,
  Typography,
  Modal,
  Form,
} from 'antd';
import { api } from '../services/api';

const { Title } = Typography;

export default function BudgetManagementPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [budgets, setBudgets] = useState<Record<string, number>>({});
  const [defaultBudget, setDefaultBudget] = useState(0);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingNamespace, setEditingNamespace] = useState<string>('');
  const [editingBudget, setEditingBudget] = useState(0);
  const [form] = Form.useForm();

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getBudgets();
      setBudgets(res.data.namespaces);
      setDefaultBudget(res.data.defaultBudget);
      setError(null);
    } catch (err) {
      setError('Failed to load budgets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleEdit = (namespace: string, currentBudget: number) => {
    setEditingNamespace(namespace);
    setEditingBudget(currentBudget);
    form.setFieldsValue({ budget: currentBudget });
    setIsModalVisible(true);
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      await api.setBudget(editingNamespace, editingBudget);
      setBudgets({ ...budgets, [editingNamespace]: editingBudget });
      setIsModalVisible(false);
      setError(null);
    } catch (err) {
      setError('Failed to update budget');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Namespace',
      dataIndex: 'namespace',
      key: 'namespace',
      render: (text: string) => <code>{text}</code>,
    },
    {
      title: 'Monthly Budget (USD)',
      dataIndex: 'budget',
      key: 'budget',
      render: (val: number) => <strong>${val.toFixed(2)}</strong>,
      sorter: (a: { budget: number }, b: { budget: number }) => a.budget - b.budget,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Is Default',
      dataIndex: 'isDefault',
      key: 'isDefault',
      render: (val: boolean) =>
        val ? <Tag color="blue">Default</Tag> : <Tag color="green">Custom</Tag>,
    },
    {
      title: 'Action',
      key: 'action',
      render: (_: any, record: { namespace: string; budget: number }) => (
        <Button type="link" onClick={() => handleEdit(record.namespace, record.budget)}>
          Edit
        </Button>
      ),
    },
  ];

  const tableData = Object.entries(budgets).map(([namespace, budget]) => ({
    namespace,
    budget,
    isDefault: budget === defaultBudget,
  }));

  return (
    <div>
      {error && (
        <Alert message="Error" description={error} type="error" showIcon style={{ marginBottom: 24 }} />
      )}

      <Card title="Budget Configuration" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Title level={5}>Default Monthly Budget</Title>
            <p style={{ color: '#666' }}>
              ${defaultBudget.toFixed(2)} per month (applied to namespaces without custom budget)
            </p>
          </div>
          <Button type="primary" onClick={loadData} loading={loading}>
            Refresh
          </Button>
        </Space>
      </Card>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
        </div>
      ) : (
        <Card title="Namespace Budgets">
          <Table
            dataSource={tableData}
            columns={columns}
            rowKey="namespace"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      )}

      <Modal
        title={`Edit Budget for ${editingNamespace}`}
        open={isModalVisible}
        onOk={handleSave}
        onCancel={() => setIsModalVisible(false)}
        confirmLoading={loading}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="budget"
            label="Monthly Budget (USD)"
            rules={[{ required: true, message: 'Please enter a budget' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              step={10}
              value={editingBudget}
              onChange={setEditingBudget}
              prefix="$"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
