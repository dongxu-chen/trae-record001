import mongoose, { Document, Schema } from 'mongoose';

export type RuleConditionType = 'due_date_overdue' | 'due_date_approaching' | 'in_progress_too_long' | 'priority_high_no_assignee' | 'custom';
export type RuleActionType = 'move_status' | 'change_priority' | 'add_tag' | 'remove_tag' | 'assign_to' | 'notify';

export interface IRuleCondition {
  type: RuleConditionType;
  value?: any;
}

export interface IRuleAction {
  type: RuleActionType;
  value: any;
}

export interface IAutomationRule extends Document {
  name: string;
  description: string;
  enabled: boolean;
  conditions: IRuleCondition[];
  actions: IRuleAction[];
  createdAt: Date;
  updatedAt: Date;
}

const RuleConditionSchema = new Schema<IRuleCondition>({
  type: {
    type: String,
    required: true,
    enum: ['due_date_overdue', 'due_date_approaching', 'in_progress_too_long', 'priority_high_no_assignee', 'custom'],
  },
  value: {
    type: Schema.Types.Mixed,
  },
});

const RuleActionSchema = new Schema<IRuleAction>({
  type: {
    type: String,
    required: true,
    enum: ['move_status', 'change_priority', 'add_tag', 'remove_tag', 'assign_to', 'notify'],
  },
  value: {
    type: Schema.Types.Mixed,
    required: true,
  },
});

const AutomationRuleSchema = new Schema<IAutomationRule>({
  name: {
    type: String,
    required: true,
    trim: true,
  },
  description: {
    type: String,
    trim: true,
  },
  enabled: {
    type: Boolean,
    default: true,
  },
  conditions: [RuleConditionSchema],
  actions: [RuleActionSchema],
}, {
  timestamps: true,
});

export default mongoose.model<IAutomationRule>('AutomationRule', AutomationRuleSchema);
