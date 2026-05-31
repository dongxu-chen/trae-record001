import { Card, Tag, Descriptions, Progress, Steps, Alert } from 'antd'
import { BulbOutlined, CheckCircleOutlined } from '@ant-design/icons'
import type { DeadLetterAnalysisResult } from '@/types'

interface AnalysisResultProps {
  result: DeadLetterAnalysisResult
  loading?: boolean
}

const AnalysisResult: React.FC<AnalysisResultProps> = ({ result, loading }) => {
  const getReasonTypeColor = (type: string) => {
    const colorMap: Record<string, string> = {
      BIZ_EXCEPTION: 'red',
      TIMEOUT: 'orange',
      REJECTED: 'gold',
      FORMAT_ERROR: 'purple',
      NULL_POINTER: 'magenta',
      DATABASE_ERROR: 'volcano',
      OTHER: 'default',
    }
    return colorMap[type] || 'default'
  }

  const getReasonTypeName = (type: string) => {
    const nameMap: Record<string, string> = {
      BIZ_EXCEPTION: '业务异常',
      TIMEOUT: '超时异常',
      REJECTED: '被拒绝',
      FORMAT_ERROR: '格式错误',
      NULL_POINTER: '空指针',
      DATABASE_ERROR: '数据库错误',
      OTHER: '其他',
    }
    return nameMap[type] || type
  }

  const getConfidenceStatus = (confidence: number) => {
    if (confidence >= 80) return 'success'
    if (confidence >= 60) return 'normal'
    return 'exception'
  }

  if (!result) {
    return (
      <Card title="分析结果" loading={loading}>
        <Alert
          message="暂无分析结果"
          description="请点击分析按钮获取死信原因分析结果"
          type="info"
          showIcon
        />
      </Card>
    )
  }

  return (
    <Card title="分析结果" loading={loading}>
      <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small">
        <Descriptions.Item label="原因类型">
          <Tag color={getReasonTypeColor(result.reasonType)}>
            {getReasonTypeName(result.reasonType)}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="置信度">
          <Progress
            percent={result.confidence}
            size="small"
            status={getConfidenceStatus(result.confidence)}
          />
        </Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 16 }}>
        <Alert
          message="处理建议"
          description={result.suggestion}
          type="info"
          showIcon
          icon={<BulbOutlined />}
        />
      </div>

      {result.fixSteps && result.fixSteps.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 12, fontWeight: 500 }}>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            修复步骤
          </div>
          <Steps
            direction="vertical"
            size="small"
            current={result.fixSteps.length}
            items={result.fixSteps.map((step, index) => ({
              title: `步骤 ${index + 1}`,
              description: step,
              status: 'finish',
            }))}
          />
        </div>
      )}
    </Card>
  )
}

export default AnalysisResult
