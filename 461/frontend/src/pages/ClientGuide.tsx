import { useState } from 'react';
import {
  Card,
  Typography,
  Table,
  Tag,
  Button,
  Space,
  Steps,
  Collapse,
  Row,
  Col,
  Alert,
  Descriptions,
  Divider,
} from 'antd';
import {
  RocketOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  ArrowRightOutlined,
  AndroidOutlined,
  AppleOutlined,
  CodeOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;
const { Panel } = Collapse;

interface CompatibilityRow {
  key: string;
  clientVersion: string;
  apiV1: string;
  apiV2: string;
  apiV21: string;
  apiV3: string;
  supportStatus: 'recommended' | 'compatible' | 'limited' | 'incompatible';
}

interface SDKItem {
  platform: string;
  icon: React.ReactNode;
  version: string;
  size: string;
  updateTime: string;
  downloadUrl: string;
  docsUrl: string;
}

const compatibilityData: CompatibilityRow[] = [
  {
    key: '1',
    clientVersion: 'v3.0.0 (最新)',
    apiV1: 'incompatible',
    apiV2: 'compatible',
    apiV21: 'compatible',
    apiV3: 'recommended',
    supportStatus: 'recommended',
  },
  {
    key: '2',
    clientVersion: 'v2.5.0',
    apiV1: 'limited',
    apiV2: 'compatible',
    apiV21: 'compatible',
    apiV3: 'limited',
    supportStatus: 'compatible',
  },
  {
    key: '3',
    clientVersion: 'v2.0.0',
    apiV1: 'compatible',
    apiV2: 'recommended',
    apiV21: 'compatible',
    apiV3: 'incompatible',
    supportStatus: 'compatible',
  },
  {
    key: '4',
    clientVersion: 'v1.8.0',
    apiV1: 'recommended',
    apiV2: 'limited',
    apiV21: 'incompatible',
    apiV3: 'incompatible',
    supportStatus: 'limited',
  },
  {
    key: '5',
    clientVersion: 'v1.5.0 (已废弃)',
    apiV1: 'compatible',
    apiV2: 'incompatible',
    apiV21: 'incompatible',
    apiV3: 'incompatible',
    supportStatus: 'incompatible',
  },
];

const sdkData: SDKItem[] = [
  {
    platform: 'Android',
    icon: <AndroidOutlined style={{ fontSize: 24, color: '#3DDC84' }} />,
    version: 'v3.0.0',
    size: '2.4 MB',
    updateTime: '2026-05-20',
    downloadUrl: '#',
    docsUrl: '#',
  },
  {
    platform: 'iOS',
    icon: <AppleOutlined style={{ fontSize: 24, color: '#000000' }} />,
    version: 'v3.0.0',
    size: '3.1 MB',
    updateTime: '2026-05-20',
    downloadUrl: '#',
    docsUrl: '#',
  },
  {
    platform: 'JavaScript',
    icon: <CodeOutlined style={{ fontSize: 24, color: '#F7DF1E' }} />,
    version: 'v3.0.0',
    size: '156 KB',
    updateTime: '2026-05-20',
    downloadUrl: '#',
    docsUrl: '#',
  },
  {
    platform: 'Java',
    icon: <GlobalOutlined style={{ fontSize: 24, color: '#007396' }} />,
    version: 'v3.0.0',
    size: '1.8 MB',
    updateTime: '2026-05-20',
    downloadUrl: '#',
    docsUrl: '#',
  },
  {
    platform: 'Python',
    icon: <CodeOutlined style={{ fontSize: 24, color: '#3776AB' }} />,
    version: 'v3.0.0',
    size: '89 KB',
    updateTime: '2026-05-20',
    downloadUrl: '#',
    docsUrl: '#',
  },
  {
    platform: 'Go',
    icon: <CodeOutlined style={{ fontSize: 24, color: '#00ADD8' }} />,
    version: 'v3.0.0',
    size: '1.2 MB',
    updateTime: '2026-05-20',
    downloadUrl: '#',
    docsUrl: '#',
  },
];

const upgradeSteps = [
  {
    title: '版本检查',
    description: '确认当前客户端版本，查看兼容性矩阵确定升级路径',
  },
  {
    title: '下载最新SDK',
    description: '从下方下载对应平台的最新版本SDK',
  },
  {
    title: '备份配置',
    description: '备份当前客户端配置和数据，防止升级过程中丢失',
  },
  {
    title: '更新依赖',
    description: '替换旧版SDK，更新项目依赖配置',
  },
  {
    title: '适配API变更',
    description: '根据API变更文档调整调用代码，处理废弃接口',
  },
  {
    title: '测试验证',
    description: '在测试环境进行完整的功能测试和兼容性验证',
  },
  {
    title: '灰度发布',
    description: '通过灰度发布机制逐步放量，监控错误率和性能指标',
  },
  {
    title: '全量上线',
    description: '确认无问题后全量发布，完成升级',
  },
];

const faqData = [
  {
    question: '升级到 v3.0.0 需要做哪些代码改动？',
    answer: '升级到 v3.0.0 主要需要关注以下几点：1) 认证方式从 API Key 改为 JWT Token；2) 用户接口路径从 /v1/users 改为 /v3/users；3) 订单创建接口新增了必填字段 payMethod；4) 商品模块新增了库存管理相关接口。建议先阅读版本迁移指南，逐步替换废弃的接口调用。',
  },
  {
    question: '旧版本 SDK 还能继续使用吗？',
    answer: 'v1.x 版本已于 2026-03-01 停止维护，v2.0.x 版本将于 2026-06-30 停止维护。建议尽快升级到 v2.5.0 或 v3.0.0 版本。停止维护后，旧版本 SDK 将不再接收安全更新和功能更新，但已有的 API 调用在废弃前仍可正常使用。',
  },
  {
    question: '如何处理 API 版本不兼容的问题？',
    answer: '如果无法立即升级客户端，可以通过 API 网关的版本路由功能暂时使用旧版本 API。同时建议制定升级计划，在废弃截止日期前完成升级。对于关键业务，可以采用双版本并行运行的策略，逐步迁移流量到新版本。',
  },
  {
    question: '升级后如何验证功能是否正常？',
    answer: '建议按照以下步骤验证：1) 在测试环境使用测试账号进行完整的功能回归测试；2) 使用我们提供的 Postman 集合进行 API 接口测试；3) 接入监控告警，关注错误率、响应时间等关键指标；4) 通过灰度发布小流量验证，确认无误后再全量上线。',
  },
  {
    question: 'SDK 支持自动更新吗？',
    answer: '目前 SDK 不支持自动更新功能。建议通过依赖管理工具（如 npm、maven、gradle 等）来管理 SDK 版本。当有新版本发布时，我们会通过邮件和站内信通知所有注册开发者。',
  },
  {
    question: '遇到升级问题如何获取技术支持？',
    answer: '如果在升级过程中遇到问题，可以通过以下途径获取帮助：1) 查阅本文档的常见问题部分；2) 访问开发者社区查看其他开发者的经验分享；3) 提交工单到技术支持团队，工作时间 24 小时内响应；4) 紧急问题可拨打技术支持热线。',
  },
];

const compatibilityMap: Record<string, { text: string; icon: React.ReactNode; color: string }> = {
  recommended: { text: '完全支持', icon: <CheckCircleOutlined />, color: 'green' },
  compatible: { text: '兼容', icon: <CheckCircleOutlined />, color: 'green' },
  limited: { text: '有限支持', icon: <WarningOutlined />, color: 'orange' },
  incompatible: { text: '不支持', icon: <CloseCircleOutlined />, color: 'red' },
};

const renderCompatibilityCell = (value: string) => {
  const config = compatibilityMap[value];
  return (
    <Space>
      <span style={{ color: config.color }}>{config.icon}</span>
      <span style={{ color: config.color }}>{config.text}</span>
    </Space>
  );
};

export default function ClientGuide() {
  const [currentStep, setCurrentStep] = useState(0);

  const columns: ColumnsType<CompatibilityRow> = [
    {
      title: '客户端版本',
      dataIndex: 'clientVersion',
      key: 'clientVersion',
      width: 180,
      render: (text, record) => (
        <Space>
          <Text strong>{text}</Text>
          {record.supportStatus === 'recommended' && (
            <Tag color="green">推荐</Tag>
          )}
          {record.supportStatus === 'incompatible' && (
            <Tag color="red">已废弃</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'API v1.0.0',
      dataIndex: 'apiV1',
      key: 'apiV1',
      width: 120,
      render: renderCompatibilityCell,
    },
    {
      title: 'API v2.0.0',
      dataIndex: 'apiV2',
      key: 'apiV2',
      width: 120,
      render: renderCompatibilityCell,
    },
    {
      title: 'API v2.1.0',
      dataIndex: 'apiV21',
      key: 'apiV21',
      width: 120,
      render: renderCompatibilityCell,
    },
    {
      title: 'API v3.0.0 (最新)',
      dataIndex: 'apiV3',
      key: 'apiV3',
      width: 150,
      render: renderCompatibilityCell,
    },
  ];

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <Space>
              <RocketOutlined style={{ fontSize: 24, color: '#165DFF' }} />
              <Title level={3} style={{ margin: 0 }}>
                客户端升级引导
              </Title>
            </Space>
            <Text type="secondary" className="mt-2 block">
              了解版本兼容性，获取最新 SDK，平滑升级到最新版本
            </Text>
          </Col>
        </Row>

        <Alert
          message="重要提示"
          description="v1.x 版本已停止维护，建议尽快升级到 v3.0.0 版本以获得最新功能和安全更新。v2.x 版本将于 2026-06-30 停止维护。"
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Title level={4}>
          <Space>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
            版本兼容矩阵
          </Space>
        </Title>
        <Paragraph type="secondary">
          下表展示了各客户端版本与 API 版本的兼容性情况，请根据您当前使用的版本选择合适的升级路径。
        </Paragraph>

        <Table
          columns={columns}
          dataSource={compatibilityData}
          pagination={false}
          bordered
          style={{ marginBottom: 32 }}
        />

        <Divider />

        <Title level={4}>
          <Space>
            <ArrowRightOutlined style={{ color: '#165DFF' }} />
            升级指南
          </Space>
        </Title>
        <Paragraph type="secondary">
          请按照以下步骤完成客户端版本升级，每个步骤都包含详细的操作说明。
        </Paragraph>

        <Card style={{ marginBottom: 24 }}>
          <Steps
            direction="vertical"
            current={currentStep}
            onChange={setCurrentStep}
            items={upgradeSteps.map((step, index) => ({
              title: step.title,
              description: step.description,
            }))}
          />
        </Card>

        {currentStep < upgradeSteps.length && (
          <Descriptions
            title={`第 ${currentStep + 1} 步：${upgradeSteps[currentStep].title}`}
            bordered
            column={1}
            style={{ marginBottom: 32 }}
          >
            <Descriptions.Item label="操作说明">
              {upgradeSteps[currentStep].description}
            </Descriptions.Item>
            <Descriptions.Item label="注意事项">
              {currentStep === 0 && '请务必确认当前版本号，可以在客户端设置页面查看。'}
              {currentStep === 1 && '请从官方渠道下载 SDK，避免使用第三方来源。'}
              {currentStep === 2 && '建议将配置文件和数据库导出备份到安全位置。'}
              {currentStep === 3 && '更新依赖后请清理构建缓存，避免使用旧版本文件。'}
              {currentStep === 4 && '请参考版本迁移文档，逐一检查每个 API 调用。'}
              {currentStep === 5 && '测试环境请尽可能模拟生产环境的配置。'}
              {currentStep === 6 && '建议按照 5% → 20% → 50% → 100% 的节奏逐步放量。'}
              {currentStep === 7 && '全量上线后建议持续监控至少 72 小时。'}
            </Descriptions.Item>
            <Descriptions.Item label="相关文档">
              {currentStep === 0 && '版本兼容性说明 | 版本发布日志'}
              {currentStep === 1 && 'SDK 下载中心 | 校验和验证指南'}
              {currentStep === 2 && '配置文件说明 | 数据导出工具'}
              {currentStep === 3 && '依赖配置示例 | 构建工具集成指南'}
              {currentStep === 4 && 'API 变更日志 | 版本迁移指南'}
              {currentStep === 5 && '测试用例模板 | Postman 测试集合'}
              {currentStep === 6 && '灰度发布配置 | 监控指标说明'}
              {currentStep === 7 && '运维监控面板 | 告警配置指南'}
            </Descriptions.Item>
          </Descriptions>
        )}

        <Divider />

        <Title level={4}>
          <Space>
            <DownloadOutlined style={{ color: '#52c41a' }} />
            SDK 下载
          </Space>
        </Title>
        <Paragraph type="secondary">
          选择您使用的平台下载最新版本的 SDK，所有 SDK 均已通过安全扫描。
        </Paragraph>

        <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
          {sdkData.map((sdk) => (
            <Col xs={24} sm={12} md={8} key={sdk.platform}>
              <Card size="small" hoverable>
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  <div style={{ marginBottom: 12 }}>{sdk.icon}</div>
                  <Title level={5} style={{ margin: '0 0 8px 0' }}>
                    {sdk.platform} SDK
                  </Title>
                  <Text type="secondary" block>
                    版本 {sdk.version}
                  </Text>
                  <Text type="secondary" block>
                    {sdk.size} · 更新于 {sdk.updateTime}
                  </Text>
                  <Space style={{ marginTop: 16 }}>
                    <Button type="primary" icon={<DownloadOutlined />} href={sdk.downloadUrl}>
                      下载
                    </Button>
                    <Button href={sdk.docsUrl}>文档</Button>
                  </Space>
                </div>
              </Card>
            </Col>
          ))}
        </Row>

        <Divider />

        <Title level={4}>
          <Space>
            <QuestionCircleOutlined style={{ color: '#FAAD14' }} />
            常见问题
          </Space>
        </Title>
        <Paragraph type="secondary">
          以下是开发者在升级过程中最常遇到的问题，点击展开查看详细解答。
        </Paragraph>

        <Collapse
          accordion
          defaultActiveKey={['0']}
          items={faqData.map((item, index) => ({
            key: String(index),
            label: <Text strong>{item.question}</Text>,
            children: (
              <div style={{ paddingLeft: 8 }}>
                <Paragraph style={{ margin: 0 }}>{item.answer}</Paragraph>
              </div>
            ),
          }))}
        />

        <Divider />

        <Alert
          message="需要更多帮助？"
          description="如果以上内容无法解决您的问题，可以访问开发者社区或提交工单联系我们的技术支持团队。"
          type="info"
          showIcon
          action={
            <Space>
              <Button size="small" type="primary">
                访问社区
              </Button>
              <Button size="small">提交工单</Button>
            </Space>
          }
          style={{ marginTop: 24 }}
        />
      </Card>
    </div>
  );
}
