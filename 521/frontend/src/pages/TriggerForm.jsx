import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, Card, message, Space, Radio, Alert, Typography, Tag } from 'antd';
import { SaveOutlined, ArrowLeftOutlined, CopyOutlined, LinkOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { triggerApi, workflowApi } from '../api';

const { Text } = Typography;
const { Option } = Select;

const TriggerForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;
  const [form] = Form.useForm();
  const [workflows, setWorkflows] = useState([]);
  const [triggerType, setTriggerType] = useState('CRON');
  const [loading, setLoading] = useState(false);
  const [webhookInfo, setWebhookInfo] = useState(null);

  useEffect(() => {
    fetchWorkflows();
    if (isEdit) {
      fetchTrigger();
    }
  }, [id]);

  const fetchWorkflows = async () => {
    try {
      const data = await workflowApi.list();
      setWorkflows(data.filter(wf => wf.status === 'PUBLISHED'));
    } catch (err) {
      message.error('加载工作流列表失败');
    }
  };

  const fetchTrigger = async () => {
    try {
      const data = await triggerApi.get(id);
      form.setFieldsValue(data);
      setTriggerType(data.triggerType);
      if (data.webhookPath) {
        setWebhookInfo({
          path: data.webhookPath,
          url: triggerApi.getWebhookUrl(data.webhookPath),
          secret: data.webhookSecret
        });
      }
    } catch (err) {
      message.error('加载触发策略失败');
    }
  };

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      const result = isEdit ? await triggerApi.update(id, values) : await triggerApi.create(values);
      message.success(isEdit ? '更新成功' : '创建成功');

      if (values.triggerType === 'WEBHOOK' && result.webhookPath) {
        setWebhookInfo({
          path: result.webhookPath,
          url: triggerApi.getWebhookUrl(result.webhookPath),
          secret: result.webhookSecret
        });
      }

      if (!isEdit) {
        navigate('/triggers');
      }
    } catch (err) {
      message.error('保存失败');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  };

  const cronPresets = [
    { label: '每分钟', value: '0 * * * * ?' },
    { label: '每小时', value: '0 0 * * * ?' },
    { label: '每天0点', value: '0 0 0 * * ?' },
    { label: '每周一0点', value: '0 0 0 ? * MON' },
    { label: '每月1号0点', value: '0 0 0 1 * ?' },
  ];

  return (
    <div style={{ maxWidth: 650, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/triggers')}>
          返回
        </Button>
        <h2 style={{ marginTop: 16 }}>{isEdit ? '编辑触发策略' : '新建触发策略'}</h2>
      </div>

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ triggerType: 'CRON' }}
        >
          <Form.Item
            name="workflowId"
            label="关联工作流"
            rules={[{ required: true, message: '请选择工作流' }]}
          >
            <Select placeholder="选择要触发的工作流">
              {workflows.map(wf => (
                <Option key={wf.id} value={wf.id}>{wf.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="triggerType"
            label="触发类型"
            rules={[{ required: true, message: '请选择触发类型' }]}
          >
            <Radio.Group onChange={(e) => setTriggerType(e.target.value)}>
              <Radio value="CRON">定时触发 (Cron)</Radio>
              <Radio value="EVENT">事件触发</Radio>
              <Radio value="WEBHOOK">WebHook触发</Radio>
            </Radio.Group>
          </Form.Item>

          {triggerType === 'CRON' && (
            <>
              <Alert
                message="Cron表达式说明"
                description={
                  <div>
                    格式: 秒 分 时 日 月 周<br />
                    例: 0 0 12 * * ? (每天中午12点)
                  </div>
                }
                type="info"
                style={{ marginBottom: 16 }}
                showIcon
              />
              <Form.Item label="快捷选择">
                <Space wrap>
                  {cronPresets.map(preset => (
                    <Button
                      key={preset.value}
                      size="small"
                      onClick={() => form.setFieldsValue({ cronExpression: preset.value })}
                    >
                      {preset.label}
                    </Button>
                  ))}
                </Space>
              </Form.Item>
              <Form.Item
                name="cronExpression"
                label="Cron表达式"
                rules={[{ required: true, message: '请输入Cron表达式' }]}
              >
                <Input placeholder="例如: 0 0 12 * * ?" />
              </Form.Item>
            </>
          )}

          {triggerType === 'EVENT' && (
            <>
              <Alert
                message="事件触发说明"
                description="当指定的事件Topic收到消息时，自动触发工作流执行"
                type="info"
                style={{ marginBottom: 16 }}
                showIcon
              />
              <Form.Item
                name="eventTopic"
                label="事件Topic"
                rules={[{ required: true, message: '请输入事件Topic' }]}
              >
                <Input placeholder="例如: order.created, data.imported" />
              </Form.Item>
              <Form.Item name="eventFilter" label="事件过滤条件 (JSON)">
                <Input.TextArea rows={4} placeholder='例如: {"type": "important"}' />
              </Form.Item>
            </>
          )}

          {triggerType === 'WEBHOOK' && (
            <>
              <Alert
                message="WebHook推模式触发"
                description={
                  <div>
                    外部系统通过HTTP POST推送触发工作流执行，实现秒级触发。<br />
                    支持HMAC-SHA256签名校验确保安全。<br />
                    请求头: <code>X-Webhook-Signature</code>
                  </div>
                }
                type="info"
                style={{ marginBottom: 16 }}
                showIcon
              />
              <Form.Item
                name="webhookPath"
                label="WebHook路径 (留空自动生成)"
              >
                <Input placeholder="例如: deploy-notify (自动生成wh-xxx)" />
              </Form.Item>
              <Form.Item
                name="webhookSecret"
                label="签名密钥 (留空自动生成)"
              >
                <Input.Password placeholder="HMAC-SHA256签名密钥" />
              </Form.Item>

              {webhookInfo && (
                <Card
                  type="inner"
                  title={<Space><LinkOutlined /> WebHook配置信息</Space>}
                  style={{ marginBottom: 16, background: '#f6ffed' }}
                >
                  <div style={{ marginBottom: 12 }}>
                    <Text strong>WebHook URL:</Text>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                      <Tag color="blue" style={{ fontSize: 12, maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {webhookInfo.url}
                      </Tag>
                      <Button
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(webhookInfo.url)}
                      >
                        复制
                      </Button>
                    </div>
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <Text strong>签名密钥:</Text>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                      <Tag color="orange" style={{ fontSize: 12, maxWidth: 350, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {webhookInfo.secret}
                      </Tag>
                      <Button
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(webhookInfo.secret)}
                      >
                        复制
                      </Button>
                    </div>
                  </div>
                  <Alert
                    message="调用示例 (curl)"
                    description={
                      <pre style={{ fontSize: 11, margin: 0, whiteSpace: 'pre-wrap' }}>
{`curl -X POST ${webhookInfo.url} \\
  -H "Content-Type: application/json" \\
  -H "X-Webhook-Signature: <computed_signature>" \\
  -d '{"event": "deploy", "status": "success"}'`}
                      </pre>
                    }
                    type="success"
                    style={{ marginTop: 8 }}
                    showIcon
                  />
                </Card>
              )}
            </>
          )}

          <Form.Item>
            <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button onClick={() => navigate('/triggers')}>取消</Button>
              <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
                保存
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default TriggerForm;
