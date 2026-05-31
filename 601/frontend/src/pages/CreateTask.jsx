import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Button,
  Card,
  Row,
  Col,
  message,
  Divider,
  Alert,
  Space
} from 'antd';
import { PlayCircleOutlined, DatabaseOutlined, SaveOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { checkApi } from '../services/api';

const { Option } = Select;
const { TextArea } = Input;

const CreateTask = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [dataSources, setDataSources] = useState([]);
  const [columns, setColumns] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [selectedSourceType, setSelectedSourceType] = useState(null);
  const [selectedTableName, setSelectedTableName] = useState(null);

  useEffect(() => {
    loadDataSources();
  }, []);

  useEffect(() => {
    if (selectedSourceType && selectedTableName) {
      loadColumns(selectedSourceType, selectedTableName);
    }
  }, [selectedSourceType, selectedTableName]);

  const loadDataSources = async () => {
    try {
      const data = await checkApi.getDataSources();
      setDataSources(data || []);
    } catch (error) {
      console.error('Failed to load data sources:', error);
    }
  };

  const loadColumns = async (type, tableName) => {
    try {
      const data = await checkApi.getColumns(type, tableName);
      setColumns(data || []);
    } catch (error) {
      console.error('Failed to load columns:', error);
    }
  };

  const handleSourceTypeChange = (value) => {
    setSelectedSourceType(value);
    setSelectedTableName(null);
    setColumns([]);
    form.setFieldsValue({ tableName: null, compareFields: [], primaryKey: null });
  };

  const handleTableNameChange = (value) => {
    setSelectedTableName(value);
  };

  const handleSubmit = async (values, executeImmediately = false) => {
    setSubmitting(true);
    try {
      const taskData = {
        ...values,
        sourceType: values.sourceType,
        tableName: values.tableName,
        compareFields: values.compareFields && values.compareFields.length > 0 ? values.compareFields : null,
        excludeFields: values.excludeFields && values.excludeFields.length > 0 ? values.excludeFields : null,
        whereCondition: values.whereCondition || null,
        batchSize: values.batchSize || null,
        latencyThresholdMs: values.latencyThresholdMs || null,
        autoRepair: values.autoRepair || false,
        stratifiedHashEnabled: values.stratifiedHashEnabled !== false,
        stratumCount: values.stratumCount || 10,
        importanceLevel: values.importanceLevel || 'MEDIUM'
      };

      if (executeImmediately) {
        await checkApi.executeTask(taskData);
        message.success('任务已创建并立即执行');
      } else {
        await checkApi.createTask(taskData);
        message.success('任务创建成功');
      }

      navigate('/tasks');
    } catch (error) {
      console.error('Failed to create task:', error);
      message.error(error.response?.data?.message || '创建任务失败');
    } finally {
      setSubmitting(false);
    }
  };

  const onFinish = (values) => {
    handleSubmit(values, false);
  };

  const onFinishAndExecute = (values) => {
    handleSubmit(values, true);
  };

  return (
    <div>
      <Alert
        message="创建数据校验任务"
        description="配置校验任务参数，支持MySQL、Redis、Elasticsearch三种数据源的数据比对，检测数据差异和同步延迟。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            batchSize: null,
            latencyThresholdMs: null,
            autoRepair: true,
            compareFields: [],
            excludeFields: [],
            stratifiedHashEnabled: true,
            stratumCount: 10,
            importanceLevel: 'MEDIUM'
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Form.Item
                name="sourceType"
                label="数据源类型"
                rules={[{ required: true, message: '请选择数据源类型' }]}
              >
                <Select
                  placeholder="请选择数据源类型"
                  onChange={handleSourceTypeChange}
                >
                  {dataSources.map(ds => (
                    <Option key={ds.type} value={ds.type} disabled={!ds.available}>
                      <DatabaseOutlined style={{ marginRight: 8 }} />
                      {ds.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="tableName"
                label="表名/索引名/Key前缀"
                rules={[{ required: true, message: '请输入表名' }]}
              >
                <Input
                  placeholder="MySQL输入表名，Redis输入Key前缀，ES输入索引名"
                  onChange={(e) => handleTableNameChange(e.target.value)}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Form.Item
                name="primaryKey"
                label="主键字段"
                tooltip="MySQL为主键名，Redis为key，ES为_id"
              >
                <Select
                  placeholder="留空则自动检测"
                  allowClear
                  showSearch
                >
                  {columns.map(col => (
                    <Option key={col} value={col}>{col}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="batchSize"
                label="批次大小"
                tooltip="每次读取的记录数"
              >
                <InputNumber
                  min={100}
                  max={10000}
                  step={100}
                  style={{ width: '100%' }}
                  placeholder="默认1000"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Form.Item
                name="importanceLevel"
                label="表重要性级别"
                tooltip="不同级别使用不同的阈值配置：CRITICAL（最严格）、HIGH、MEDIUM、LOW（最宽松）"
              >
                <Select placeholder="选择重要性级别">
                  <Option value="CRITICAL">CRITICAL - 核心表（阈值最严格）</Option>
                  <Option value="HIGH">HIGH - 重要表</Option>
                  <Option value="MEDIUM">MEDIUM - 一般表（默认）</Option>
                  <Option value="LOW">LOW - 非核心表</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="latencyThresholdMs"
                label="延迟阈值(毫秒)"
                tooltip="留空则使用重要性级别对应的默认阈值"
              >
                <InputNumber
                  min={100}
                  max={3600000}
                  step={1000}
                  style={{ width: '100%' }}
                  placeholder="根据重要性级别自动配置"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Form.Item
                name="stratifiedHashEnabled"
                label="分层哈希校验"
                tooltip="启用分层哈希校验可大幅提升比对速度，自动跳过无差异的分层"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                name="stratumCount"
                label="分层数量"
                tooltip="分层越多，定位差异越精准，但计算量稍大"
              >
                <InputNumber
                  min={2}
                  max={100}
                  step={1}
                  style={{ width: '100%' }}
                  placeholder="默认10"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                name="autoRepair"
                label="自动修复"
                tooltip="检测到差异后是否自动修复，失败时记录不重试"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">字段配置</Divider>

          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Form.Item
                name="compareFields"
                label="比对字段"
                tooltip="选择需要比对的字段，留空则比对所有字段"
              >
                <Select
                  mode="multiple"
                  placeholder="留空则比对所有字段"
                  allowClear
                  showSearch
                  optionFilterProp="children"
                >
                  {columns.map(col => (
                    <Option key={col} value={col}>{col}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="excludeFields"
                label="排除字段"
                tooltip="选择不需要比对的字段"
              >
                <Select
                  mode="multiple"
                  placeholder="选择需要排除的字段"
                  allowClear
                  showSearch
                  optionFilterProp="children"
                >
                  {columns.map(col => (
                    <Option key={col} value={col}>{col}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24}>
              <Form.Item
                name="whereCondition"
                label="查询条件"
                tooltip="MySQL为WHERE条件，ES为Query String查询，Redis不支持"
              >
                <TextArea
                  rows={3}
                  placeholder="例如: created_at > '2024-01-01' AND status = 1"
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider />

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={submitting}
              >
                创建任务
              </Button>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={submitting}
                onClick={() => form.submit().then(values => onFinishAndExecute(values))}
              >
                创建并执行
              </Button>
              <Button onClick={() => navigate('/tasks')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default CreateTask;
