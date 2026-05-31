export enum MqType {
  KAFKA = 'KAFKA',
  ROCKETMQ = 'ROCKETMQ',
  RABBITMQ = 'RABBITMQ',
}

export enum DeadReasonType {
  FORMAT_ERROR = 'FORMAT_ERROR',
  BIZ_EXCEPTION = 'BIZ_EXCEPTION',
  TIMEOUT = 'TIMEOUT',
  REJECTED = 'REJECTED',
  OTHER = 'OTHER',
}

export enum ProcessStatus {
  PENDING = 'PENDING',
  PROCESSED = 'PROCESSED',
  REPLAYED = 'REPLAYED',
  ARCHIVED = 'ARCHIVED',
  IGNORED = 'IGNORED',
}

export enum AlertLevel {
  INFO = 'INFO',
  WARNING = 'WARNING',
  CRITICAL = 'CRITICAL',
}

export const MqTypeLabel: Record<MqType, string> = {
  [MqType.KAFKA]: 'Kafka消息队列',
  [MqType.ROCKETMQ]: 'RocketMQ消息队列',
  [MqType.RABBITMQ]: 'RabbitMQ消息队列',
};

export const DeadReasonTypeLabel: Record<DeadReasonType, string> = {
  [DeadReasonType.FORMAT_ERROR]: '格式错误',
  [DeadReasonType.BIZ_EXCEPTION]: '业务异常',
  [DeadReasonType.TIMEOUT]: '消费超时',
  [DeadReasonType.REJECTED]: '消费被拒绝',
  [DeadReasonType.OTHER]: '其他原因',
};

export const ProcessStatusLabel: Record<ProcessStatus, string> = {
  [ProcessStatus.PENDING]: '待处理',
  [ProcessStatus.PROCESSED]: '已处理',
  [ProcessStatus.REPLAYED]: '已重放',
  [ProcessStatus.ARCHIVED]: '已归档',
  [ProcessStatus.IGNORED]: '已忽略',
};

export const AlertLevelLabel: Record<AlertLevel, string> = {
  [AlertLevel.INFO]: '信息',
  [AlertLevel.WARNING]: '警告',
  [AlertLevel.CRITICAL]: '严重',
};
