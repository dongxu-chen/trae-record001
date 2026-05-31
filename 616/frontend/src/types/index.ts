import { MqType, DeadReasonType, ProcessStatus, AlertLevel } from './enums';

export interface DeadLetterMessage {
  id: string;
  mqType: MqType;
  topic: string;
  queueName: string;
  messageId: string;
  messageBody: string;
  headers: Record<string, any>;
  deadReason: string;
  deadReasonType: DeadReasonType;
  stackTrace: string;
  originalTopic: string;
  originalQueue: string;
  retryCount: number;
  processStatus: ProcessStatus;
  createTime: string;
  updateTime: string;
}

export interface AlertRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  triggerCondition: string;
  alertLevel: AlertLevel;
  notificationType: string;
  notificationTarget: string;
  createTime: string;
  updateTime: string;
}

export interface AnalysisResult {
  reasonType: DeadReasonType;
  confidence: number;
  suggestedAction: string;
  repairSteps: string[];
  rootCause: string;
  details: Record<string, any>;
}

export interface Statistics {
  totalCount: number;
  pendingCount: number;
  processedCount: number;
  replayedCount: number;
  archivedCount: number;
  ignoredCount: number;
  todayCount: number;
  weekCount: number;
  monthCount: number;
}

export interface PageResult<T> {
  list: T[];
  total: number;
  pageNum: number;
  pageSize: number;
}

export interface Result<T> {
  code: number;
  message: string;
  data: T;
}

export interface DeadLetterQueryParams {
  pageNum?: number;
  pageSize?: number;
  mqType?: MqType;
  deadReasonType?: DeadReasonType;
  processStatus?: ProcessStatus;
  topic?: string;
  startTime?: string;
  endTime?: string;
}

export interface ReplayRequest {
  id: string;
  remark?: string;
}

export interface ArchiveRequest {
  ids: string[];
  archiveDays?: number;
}

export interface AlertRuleDTO {
  name: string;
  description: string;
  enabled: boolean;
  triggerCondition: string;
  alertLevel: AlertLevel;
  notificationType: string;
  notificationTarget: string;
}
