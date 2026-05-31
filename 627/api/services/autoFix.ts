import type { QualityIssue, AutoFixResult, AutoFixPreview } from '../../shared/types.js';
import { issuesRepository } from '../db/repositories.js';

const FIX_STRATEGIES: Record<string, {
  strategy: string;
  canFix: (issue: QualityIssue) => boolean;
  computeFix: (issue: QualityIssue) => { newValue: string; message: string };
}> = {
  null_check: {
    strategy: 'default_fill',
    canFix: (issue) => issue.issueType === 'null_check',
    computeFix: (issue) => {
      const columnDefaults: Record<string, string> = {
        email: 'unknown@example.com',
        name: '未知用户',
        age: '0',
        amount: '0',
        status: 'unknown',
      };
      const defaultValue = columnDefaults[issue.columnName] ?? 'N/A';
      return {
        newValue: defaultValue,
        message: `空值填充为默认值: ${defaultValue}`,
      };
    },
  },
  value_range: {
    strategy: 'clamp',
    canFix: (issue) => issue.issueType === 'value_range',
    computeFix: (issue) => {
      return {
        newValue: '[需人工确认-值域修正]',
        message: `值域越界问题需人工确认修正范围`,
      };
    },
  },
};

export function previewAutoFix(issues: QualityIssue[]): AutoFixPreview {
  const fixes: AutoFixResult[] = issues.map(issue => {
    const strategy = FIX_STRATEGIES[issue.issueType];
    if (!strategy || !strategy.canFix(issue)) {
      return {
        issueId: issue.id,
        issueType: issue.issueType,
        tableName: issue.tableName,
        columnName: issue.columnName,
        rowIdentifier: issue.rowIdentifier,
        fixStrategy: 'none',
        oldValue: '',
        newValue: '',
        fixed: false,
        message: '此类型问题暂不支持自动修复',
      };
    }

    const { newValue, message } = strategy.computeFix(issue);
    return {
      issueId: issue.id,
      issueType: issue.issueType,
      tableName: issue.tableName,
      columnName: issue.columnName,
      rowIdentifier: issue.rowIdentifier,
      fixStrategy: strategy.strategy,
      oldValue: '(null/empty)',
      newValue,
      fixed: issue.issueType === 'null_check',
      message,
    };
  });

  return {
    totalFixable: fixes.filter(f => f.fixed).length,
    fixes,
  };
}

export function executeAutoFix(issueIds: string[]): AutoFixResult[] {
  const allIssues = issuesRepository.getAll();
  const targetIssues = allIssues.filter(i => issueIds.includes(i.id));

  const results: AutoFixResult[] = targetIssues.map(issue => {
    const strategy = FIX_STRATEGIES[issue.issueType];
    if (!strategy || !strategy.canFix(issue)) {
      return {
        issueId: issue.id,
        issueType: issue.issueType,
        tableName: issue.tableName,
        columnName: issue.columnName,
        rowIdentifier: issue.rowIdentifier,
        fixStrategy: 'none',
        oldValue: '',
        newValue: '',
        fixed: false,
        message: '此类型问题暂不支持自动修复',
      };
    }

    const { newValue, message } = strategy.computeFix(issue);

    if (issue.issueType === 'null_check') {
      issuesRepository.update(issue.id, { status: 'resolved' });
      return {
        issueId: issue.id,
        issueType: issue.issueType,
        tableName: issue.tableName,
        columnName: issue.columnName,
        rowIdentifier: issue.rowIdentifier,
        fixStrategy: strategy.strategy,
        oldValue: '(null/empty)',
        newValue,
        fixed: true,
        message: `${message}，问题已标记为已解决`,
      };
    }

    return {
      issueId: issue.id,
      issueType: issue.issueType,
      tableName: issue.tableName,
      columnName: issue.columnName,
      rowIdentifier: issue.rowIdentifier,
      fixStrategy: strategy.strategy,
      oldValue: '(invalid)',
      newValue,
      fixed: false,
      message,
    };
  });

  return results;
}
