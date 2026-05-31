import dayjs from 'dayjs';
import {
  ProcessStatus,
  ProcessStatusLabel,
  DeadReasonType,
  DeadReasonTypeLabel,
  MqType,
  MqTypeLabel,
  AlertLevel,
  AlertLevelLabel,
} from '@/types/enums';

export const formatDateTime = (
  date: string | Date | undefined,
  format: string = 'YYYY-MM-DD HH:mm:ss'
): string => {
  if (!date) return '-';
  return dayjs(date).format(format);
};

export const formatDate = (
  date: string | Date | undefined,
  format: string = 'YYYY-MM-DD'
): string => {
  if (!date) return '-';
  return dayjs(date).format(format);
};

export const formatProcessStatus = (status: ProcessStatus): string => {
  return ProcessStatusLabel[status] || status;
};

export const formatDeadReasonType = (type: DeadReasonType): string => {
  return DeadReasonTypeLabel[type] || type;
};

export const formatMqType = (type: MqType): string => {
  return MqTypeLabel[type] || type;
};

export const formatAlertLevel = (level: AlertLevel): string => {
  return AlertLevelLabel[level] || level;
};

export const getProcessStatusColor = (status: ProcessStatus): string => {
  const colorMap: Record<ProcessStatus, string> = {
    [ProcessStatus.PENDING]: 'orange',
    [ProcessStatus.PROCESSED]: 'green',
    [ProcessStatus.REPLAYED]: 'blue',
    [ProcessStatus.ARCHIVED]: 'default',
    [ProcessStatus.IGNORED]: 'gray',
  };
  return colorMap[status] || 'default';
};

export const getAlertLevelColor = (level: AlertLevel): string => {
  const colorMap: Record<AlertLevel, string> = {
    [AlertLevel.INFO]: 'blue',
    [AlertLevel.WARNING]: 'orange',
    [AlertLevel.CRITICAL]: 'red',
  };
  return colorMap[level] || 'default';
};

export const getDeadReasonColor = (type: DeadReasonType): string => {
  const colorMap: Record<DeadReasonType, string> = {
    [DeadReasonType.FORMAT_ERROR]: 'red',
    [DeadReasonType.BIZ_EXCEPTION]: 'orange',
    [DeadReasonType.TIMEOUT]: 'gold',
    [DeadReasonType.REJECTED]: 'purple',
    [DeadReasonType.OTHER]: 'default',
  };
  return colorMap[type] || 'default';
};

export const formatConfidence = (confidence: number): string => {
  return `${(confidence * 100).toFixed(1)}%`;
};

export const truncateText = (text: string, maxLength: number): string => {
  if (!text) return '-';
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
};

export const formatNumber = (num: number | undefined): string => {
  if (num === undefined || num === null) return '-';
  return num.toLocaleString();
};
