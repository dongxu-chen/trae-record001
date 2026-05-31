import { Modal, Alert, Descriptions, Spin, message } from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { replayDeadLetter } from '@/services/api'
import type { DeadLetterMessage } from '@/types'

interface ReplayModalProps {
  open: boolean
  onCancel: () => void
  onSuccess: () => void
  selectedItems: DeadLetterMessage[]
  mode?: 'single' | 'batch'
}

const ReplayModal: React.FC<ReplayModalProps> = ({
  open,
  onCancel,
  onSuccess,
  selectedItems,
  mode = 'single',
}) => {
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    if (selectedItems.length === 0) return
    setLoading(true)
    try {
      const ids = selectedItems.map((item) => item.id)
      await replayDeadLetter(ids)
      message.success(`成功重放 ${ids.length} 条消息`)
      onSuccess()
      onCancel()
    } catch (error) {
      console.error('Replay failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const getMqTypeName = (type: string) => {
    const nameMap: Record<string, string> = {
      RABBITMQ: 'RabbitMQ',
      ROCKETMQ: 'RocketMQ',
      KAFKA: 'Kafka',
    }
    return nameMap[type] || type
  }

  return (
    <Modal
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ExclamationCircleOutlined style={{ color: '#faad14' }} />
          {mode === 'batch' ? '批量重放确认' : '重放确认'}
        </span>
      }
      open={open}
      onCancel={onCancel}
      onOk={handleConfirm}
      confirmLoading={loading}
      okText="确认重放"
      cancelText="取消"
      okButtonProps={{ danger: true }}
      width={600}
    >
      <Spin spinning={loading}>
        <Alert
          message={
            mode === 'batch'
              ? `即将重放 ${selectedItems.length} 条死信消息`
              : '即将重放该死信消息'
          }
          description="重放操作会将消息重新发送到原消息队列，请确保问题已修复，否则可能再次成为死信。"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {mode === 'single' && selectedItems[0] && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="消息ID">{selectedItems[0].messageId}</Descriptions.Item>
            <Descriptions.Item label="MQ类型">{getMqTypeName(selectedItems[0].mqType)}</Descriptions.Item>
            <Descriptions.Item label="Topic">{selectedItems[0].topic}</Descriptions.Item>
            <Descriptions.Item label="死信原因">{selectedItems[0].deadReason}</Descriptions.Item>
            <Descriptions.Item label="重试次数">{selectedItems[0].retryCount}</Descriptions.Item>
          </Descriptions>
        )}

        {mode === 'batch' && (
          <div style={{ maxHeight: 300, overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: 4, padding: 12 }}>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>选中的消息：</div>
            {selectedItems.map((item) => (
              <div
                key={item.id}
                style={{
                  padding: '8px 12px',
                  marginBottom: 4,
                  background: '#fafafa',
                  borderRadius: 4,
                  fontSize: 13,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#666' }}>{item.messageId}</span>
                  <span style={{ color: '#8c8c8c', fontSize: 12 }}>{getMqTypeName(item.mqType)}</span>
                </div>
                <div style={{ color: '#8c8c8c', fontSize: 12, marginTop: 2 }}>{item.topic}</div>
              </div>
            ))}
          </div>
        )}
      </Spin>
    </Modal>
  )
}

export default ReplayModal
