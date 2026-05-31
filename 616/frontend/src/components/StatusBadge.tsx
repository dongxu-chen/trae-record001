import React from 'react';
import { Tag } from 'antd';
import {
  ProcessStatus,
  AlertLevel,
  DeadReasonType,
  MqType,
} from '@/types/enums';
import {
  formatProcessStatus,
  formatAlertLevel,
  formatDeadReasonType,
  formatMqType,
  getProcessStatusColor,
  getAlertLevelColor,
  getDeadReasonColor,
} from '@/utils/format';

interface StatusBadgeProps {
  type: 'process' | 'alert' | 'reason' | 'mq';
  value: ProcessStatus | AlertLevel | DeadReasonType | MqType;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ type, value }) => {
  let text: string;
  let color: string;

  switch (type) {
    case 'process':
      text = formatProcessStatus(value as ProcessStatus);
      color = getProcessStatusColor(value as ProcessStatus);
      break;
    case 'alert':
      text = formatAlertLevel(value as AlertLevel);
      color = getAlertLevelColor(value as AlertLevel);
      break;
    case 'reason':
      text = formatDeadReasonType(value as DeadReasonType);
      color = getDeadReasonColor(value as DeadReasonType);
      break;
    case 'mq':
      text = formatMqType(value as MqType);
      color = 'blue';
      break;
    default:
      text = String(value);
      color = 'default';
  }

  return <Tag color={color}>{text}</Tag>;
};

export default StatusBadge;
