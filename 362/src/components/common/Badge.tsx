import React from 'react';
import type { ColumnType } from '../../types';

interface BadgeProps {
  children: React.ReactNode;
  type?: 'numeric' | 'string' | 'boolean' | 'date' | 'mixed' | 'default' | 'success' | 'warning' | 'danger';
  className?: string;
}

const typeClasses: Record<string, string> = {
  numeric: 'badge-numeric',
  string: 'badge-string',
  boolean: 'badge-boolean',
  date: 'badge-date',
  mixed: 'badge-mixed',
  default: 'bg-bg-700 text-bg-200 border border-bg-600',
  success: 'bg-success-500/20 text-success-400 border border-success-500/30',
  warning: 'bg-warning-500/20 text-warning-400 border border-warning-500/30',
  danger: 'bg-danger-500/20 text-danger-400 border border-danger-500/30',
};

export const Badge: React.FC<BadgeProps> = ({ children, type = 'default', className = '' }) => {
  return <span className={`badge ${typeClasses[type] || typeClasses.default} ${className}`}>{children}</span>;
};

interface TypeBadgeProps {
  type: ColumnType;
}

export const TypeBadge: React.FC<TypeBadgeProps> = ({ type }) => {
  const labels: Record<ColumnType, string> = {
    numeric: '数值',
    string: '字符串',
    boolean: '布尔',
    date: '日期',
    mixed: '混合',
  };
  return <Badge type={type}>{labels[type]}</Badge>;
};
