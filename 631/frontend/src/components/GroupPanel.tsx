import React, { useState } from 'react';
import {
  Collapse, List, Button, Modal, Form, Input, Select, Tag, Space, Typography,
  Popconfirm, message, Empty, Card, Tooltip
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, DownOutlined, RightOutlined,
  AppstoreOutlined, TeamOutlined, UserOutlined
} from '@ant-design/icons';
import type { TopologyGroup, ConsumerGroupNode, TopologyNode } from '../types';
import { topologyApi } from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

interface GroupPanelProps {
  groups: TopologyGroup[];
  consumerGroups: ConsumerGroupNode[];
  collapsedGroups: Set<string>;
  onGroupClick: (groupId: string) => void;
  onGroupCreated: () => void;
  services: TopologyNode[];
}

const GroupPanel: React.FC<GroupPanelProps> = ({
  groups, consumerGroups, collapsedGroups, onGroupClick, onGroupCreated, services
}) => {
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const handleCreateGroup = async (values: any) => {
    try {
      await topologyApi.createGroup({
        name: values.name,
        namespace: values.namespace || 'default',
        groupType: values.groupType || 'custom',
        description: values.description,
        serviceIds: values.serviceIds || [],
        parentId: values.parentId
      });
      message.success('分组创建成功');
      setModalVisible(false);
      form.resetFields();
      onGroupCreated();
    } catch (error) {
      message.error('分组创建失败');
      console.error(error);
    }
  };

  const handleDeleteGroup = async (groupId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await topologyApi.deleteGroup(groupId);
      message.success('分组删除成功');
      onGroupCreated();
    } catch (error) {
      message.error('分组删除失败');
    }
  };

  const renderGroupIcon = (groupType: string) => {
    switch (groupType) {
      case 'namespace': return <AppstoreOutlined style={{ color: '#1890ff' }} />;
      case 'business': return <TeamOutlined style={{ color: '#52c41a' }} />;
      case 'language': return <UserOutlined style={{ color: '#fa8c16' }} />;
      default: return <AppstoreOutlined style={{ color: '#722ed1' }} />;
    }
  };

  const getGroupTypeColor = (groupType: string): string => {
    switch (groupType) {
      case 'namespace': return 'blue';
      case 'business': return 'green';
      case 'language': return 'orange';
      default: return 'purple';
    }
  };

  const buildGroupTree = (groups: TopologyGroup[]) => {
    const rootGroups = groups.filter(g => !g.parentId);
    const childGroups = groups.filter(g => g.parentId);

    const renderGroup = (group: TopologyGroup, level: number = 0) => {
      const children = childGroups.filter(c => c.parentId === group.id);
      const groupServices = services.filter(s => s.groupId === group.id);
      const isCollapsed = collapsedGroups.has(group.id);

      return (
        <div key={group.id} style={{ marginLeft: level * 16 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 12px',
              borderRadius: 4,
              cursor: 'pointer',
              background: isCollapsed ? '#f6ffed' : '#f0f5ff',
              marginBottom: 4,
              border: `1px solid ${isCollapsed ? '#b7eb8f' : '#adc6ff'}`
            }}
            onClick={() => onGroupClick(group.id)}
          >
            <Space>
              {children.length > 0 || groupServices.length > 0 ? (
                isCollapsed ? <RightOutlined /> : <DownOutlined />
              ) : <span style={{ width: 14 }} />}
              {renderGroupIcon(group.groupType)}
              <Space>
                <Text strong>{group.name}</Text>
                <Tag color={getGroupTypeColor(group.groupType)} size="small">
                  {group.groupType}
                </Tag>
              </Space>
            </Space>
            <Space>
              <Tag color="blue">{group.serviceCount}个服务</Tag>
              {children.length > 0 && (
                <Tag color="green">{children.length}个子组</Tag>
              )}
              <Popconfirm
                title="确定删除此分组？"
                onConfirm={(e) => handleDeleteGroup(group.id, e as React.MouseEvent)}
                okText="确定"
                cancelText="取消"
              >
                <Button
                  type="text"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>
            </Space>
          </div>

          {!isCollapsed && (
            <>
              {groupServices.length > 0 && (
                <div style={{ marginLeft: 30, marginBottom: 8 }}>
                  <List
                    size="small"
                    dataSource={groupServices}
                    renderItem={service => (
                      <List.Item style={{ padding: '4px 8px' }}>
                        <Space>
                          <div
                            style={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              background: service.status === 'ACTIVE' ? '#52c41a' : '#ff4d4f'
                            }}
                          />
                          <Text type="secondary">{service.name}</Text>
                          {service.language && (
                            <Tag color="default" size="small">{service.language}</Tag>
                          )}
                        </Space>
                      </List.Item>
                    )}
                  />
                </div>
              )}
              {children.map(child => renderGroup(child, level + 1))}
            </>
          )}
        </div>
      );
    };

    return rootGroups.map(g => renderGroup(g));
  };

  return (
    <div style={{ padding: 16, height: '100%', overflowY: 'auto' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Space style={{ justifyContent: 'space-between', width: '100%' }}>
            <Title level={5} style={{ margin: 0 }}>
              <AppstoreOutlined /> 服务分组
            </Title>
            <Tooltip title="创建新分组">
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={() => setModalVisible(true)}
              >
                新建
              </Button>
            </Tooltip>
          </Space>

          {groups.length > 0 ? (
            <div style={{ marginTop: 16 }}>
              {buildGroupTree(groups)}
            </div>
          ) : (
            <Empty description="暂无分组" style={{ marginTop: 24 }} />
          )}
        </div>

        {consumerGroups.length > 0 && (
          <div>
            <Title level={5} style={{ marginBottom: 16 }}>
              <TeamOutlined /> 消费组
            </Title>
            <Collapse defaultActiveKey={['1']}>
              <Panel
                header={`${consumerGroups.length} 个消费组`}
                key="1"
              >
                <List
                  size="small"
                  dataSource={consumerGroups}
                  renderItem={cg => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space>
                            <Tag color="purple">{cg.messageQueue}</Tag>
                            <Text strong>{cg.name}</Text>
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size="small" style={{ width: '100%' }}>
                            <div>
                              <Text type="secondary">Topic: </Text>
                              <Text code>{cg.topic}</Text>
                            </div>
                            <div>
                              <Tag color="green">{cg.producerIds.length} 生产者</Tag>
                              <Tag color="blue">{cg.consumerCount} 消费者</Tag>
                              <Tag color={cg.status === 'ACTIVE' ? 'success' : 'default'}>
                                {cg.status}
                              </Tag>
                            </div>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              </Panel>
            </Collapse>
          </div>
        )}

        <div>
          <Title level={5} style={{ marginBottom: 16 }}>
            未分组服务
          </Title>
          {services.filter(s => !s.groupId).length > 0 ? (
            <List
              size="small"
              dataSource={services.filter(s => !s.groupId)}
              renderItem={service => (
                <List.Item>
                  <Space>
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: service.status === 'ACTIVE' ? '#52c41a' : '#ff4d4f'
                      }}
                    />
                    <Text>{service.name}</Text>
                    {service.language && (
                      <Tag color="default" size="small">{service.language}</Tag>
                    )}
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty description="全部服务已分组" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </div>
      </Space>

      <Modal
        title="创建服务分组"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateGroup}
        >
          <Form.Item
            name="name"
            label="分组名称"
            rules={[{ required: true, message: '请输入分组名称' }]}
          >
            <Input placeholder="请输入分组名称" />
          </Form.Item>

          <Form.Item
            name="namespace"
            label="命名空间"
            initialValue="default"
          >
            <Input placeholder="请输入命名空间" />
          </Form.Item>

          <Form.Item
            name="groupType"
            label="分组类型"
            initialValue="custom"
          >
            <Select>
              <Option value="namespace">命名空间</Option>
              <Option value="business">业务域</Option>
              <Option value="language">语言栈</Option>
              <Option value="custom">自定义</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea rows={3} placeholder="请输入分组描述" />
          </Form.Item>

          <Form.Item
            name="parentId"
            label="父分组"
          >
            <Select placeholder="选择父分组（可选）" allowClear>
              {groups.map(g => (
                <Option key={g.id} value={g.id}>{g.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="serviceIds"
            label="包含服务"
          >
            <Select
              mode="multiple"
              placeholder="选择要加入分组的服务"
              optionFilterProp="children"
              showSearch
            >
              {services.filter(s => !s.groupId).map(s => (
                <Option key={s.id} value={s.id}>
                  {s.name} ({s.namespace})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default GroupPanel;
