import { useState, useMemo, useCallback } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { AlertCondition, ConditionGroup } from '@/types';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';
import { Plus, X, GripVertical, Brackets, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/utils/helpers';

const OPERATORS = ['>', '<', '>=', '<=', '==', '!='] as const;
const LOGICS = ['AND', 'OR'] as const;

interface SortableConditionProps {
  condition: AlertCondition;
  index: number;
  total: number;
  groups: ConditionGroup[];
  metric: string;
  isDragging: boolean;
  onChange: (patch: Partial<AlertCondition>) => void;
  onRemove: () => void;
  onAddGroup: () => void;
  onRemoveGroup: () => void;
}

function SortableCondition({
  condition,
  index,
  total,
  groups,
  metric,
  isDragging,
  onChange,
  onRemove,
  onAddGroup,
  onRemoveGroup,
}: SortableConditionProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: condition.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const label = METRIC_DISPLAY_CONFIG[metric]?.label || metric;
  const hasGroup = condition.groupId != null;
  const currentGroup = hasGroup ? groups.find((g) => g.id === condition.groupId) : null;

  return (
    <div ref={setNodeRef} style={style} className="group/item relative">
      <div className="flex items-center gap-2">
        <button
          type="button"
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing p-1 text-brand-text-secondary hover:text-brand-text-primary transition-colors shrink-0"
        >
          <GripVertical className="h-4 w-4" />
        </button>

        {hasGroup && index === 0 && (
          <div className="flex items-center gap-1">
            <span className="text-brand-cyan font-mono text-lg font-bold">(</span>
            <select
              value={currentGroup?.logic || 'AND'}
              onChange={(e) => onChange({ groupId: condition.groupId })}
              className="rounded-md border border-brand-border bg-brand-card px-2 py-1 text-xs text-brand-cyan focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan outline-none font-semibold"
            >
              {LOGICS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <span className="text-brand-text-secondary text-xs">{currentGroup?.name}</span>
          </div>
        )}

        <span className="shrink-0 text-xs text-brand-text-secondary w-16 truncate" title={label}>
          {label}
        </span>

        <select
          value={condition.operator}
          onChange={(e) => onChange({ operator: e.target.value as AlertCondition['operator'] })}
          className="rounded-md border border-brand-border bg-brand-card px-2 py-1.5 text-xs text-brand-text-primary focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan outline-none"
        >
          {OPERATORS.map((op) => (
            <option key={op} value={op}>{op}</option>
          ))}
        </select>

        <input
          type="number"
          value={condition.value}
          onChange={(e) => onChange({ value: Number(e.target.value) })}
          className="w-24 rounded-md border border-brand-border bg-brand-card px-2 py-1.5 text-xs text-brand-text-primary focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan outline-none font-mono-num"
        />

        {index < total - 1 && (
          <select
            value={condition.logic || 'AND'}
            onChange={(e) => onChange({ logic: e.target.value as AlertCondition['logic'] })}
            className="rounded-md border border-brand-border bg-brand-card px-2 py-1.5 text-xs text-brand-cyan focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan outline-none font-semibold"
          >
            {LOGICS.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        )}

        {hasGroup && index === total - 1 && (
          <span className="text-brand-cyan font-mono text-lg font-bold">)</span>
        )}

        <div className="flex items-center gap-0.5 opacity-0 group-hover/item:opacity-100 transition-opacity">
          {!hasGroup ? (
            <button
              type="button"
              onClick={onAddGroup}
              className="rounded p-1 text-brand-text-secondary hover:text-brand-cyan hover:bg-brand-card transition-colors"
              title="创建分组"
            >
              <Brackets className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={onRemoveGroup}
              className="rounded p-1 text-brand-text-secondary hover:text-brand-amber hover:bg-brand-card transition-colors"
              title="移出分组"
            >
              <Brackets className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            type="button"
            onClick={onRemove}
            disabled={total <= 1}
            className={cn(
              'rounded p-1 transition-colors',
              total <= 1
                ? 'text-brand-border cursor-not-allowed'
                : 'text-brand-text-secondary hover:text-brand-red hover:bg-brand-card'
            )}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

interface GroupRowProps {
  group: ConditionGroup;
  collapsed: boolean;
  onToggle: () => void;
  onLogicChange: (logic: 'AND' | 'OR') => void;
  onRemove: () => void;
}

function GroupRow({ group, collapsed, onToggle, onLogicChange, onRemove }: GroupRowProps) {
  return (
    <div className="flex items-center gap-2 py-1.5 px-2 -mx-2 rounded-md hover:bg-brand-card/50 transition-colors">
      <button type="button" onClick={onToggle} className="p-0.5 text-brand-text-secondary hover:text-brand-text-primary">
        {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>
      <span className="text-brand-cyan font-mono text-sm font-bold">(</span>
      <input
        type="text"
        value={group.name || '分组'}
        onChange={(e) => {
          // 由外部处理
        }}
        className="bg-transparent text-xs text-brand-text-primary focus:outline-none border-b border-transparent focus:border-brand-cyan w-20"
        placeholder="分组名称"
      />
      <select
        value={group.logic}
        onChange={(e) => onLogicChange(e.target.value as 'AND' | 'OR')}
        className="rounded-md border border-brand-border bg-brand-card px-2 py-1 text-xs text-brand-cyan focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan outline-none font-semibold"
      >
        {LOGICS.map((l) => (
          <option key={l} value={l}>{l}</option>
        ))}
      </select>
      <span className="text-brand-text-secondary text-xs">组内关系</span>
      <button
        type="button"
        onClick={onRemove}
        className="ml-auto p-1 text-brand-text-secondary hover:text-brand-red transition-colors"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

interface VisualConditionBuilderProps {
  metric: string;
  conditions: AlertCondition[];
  groups?: ConditionGroup[];
  onChange: (conditions: AlertCondition[]) => void;
  onGroupsChange?: (groups: ConditionGroup[]) => void;
}

export default function VisualConditionBuilder({
  metric,
  conditions,
  groups = [],
  onChange,
  onGroupsChange,
}: VisualConditionBuilderProps) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const generateId = useCallback(() => `cond-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`, []);
  const generateGroupId = useCallback(() => `group-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`, []);

  const activeCondition = useMemo(
    () => conditions.find((c) => c.id === activeId) || null,
    [conditions, activeId]
  );

  const buildPreview = useCallback((): string => {
    const label = METRIC_DISPLAY_CONFIG[metric]?.label || metric;
    const groupMap = new Map(groups.map((g) => [g.id, g]));
    const groupOrder = groups.map((g) => g.id);

    const grouped: Array<{ groupId: string | null; conditions: AlertCondition[] }> = [];
    let currentGroup: { groupId: string | null; conditions: AlertCondition[] } | null = null;

    for (const cond of conditions) {
      const gid = cond.groupId || null;
      if (!currentGroup || currentGroup.groupId !== gid) {
        currentGroup = { groupId: gid, conditions: [] };
        grouped.push(currentGroup);
      }
      currentGroup.conditions.push(cond);
    }

    const parts: string[] = [];
    for (let gi = 0; gi < grouped.length; gi++) {
      const chunk = grouped[gi];
      const group = chunk.groupId ? groupMap.get(chunk.groupId) : null;
      const isFirstChunk = gi === 0;

      const innerParts: string[] = [];
      for (let i = 0; i < chunk.conditions.length; i++) {
        const c = chunk.conditions[i];
        const part = `${label} ${c.operator} ${c.value}`;
        if (i === 0) {
          innerParts.push(part);
        } else {
          const logic = group?.logic || c.logic || 'AND';
          innerParts.push(`${logic} ${part}`);
        }
      }

      let chunkStr = innerParts.join(' ');
      if (chunk.groupId) {
        chunkStr = `(${chunkStr})`;
      }

      if (!isFirstChunk) {
        const lastCond = grouped[gi - 1].conditions[grouped[gi - 1].conditions.length - 1];
        const outerLogic = lastCond?.logic || 'AND';
        chunkStr = `${outerLogic} ${chunkStr}`;
      }

      parts.push(chunkStr);
    }

    return parts.join(' ');
  }, [metric, conditions, groups]);

  const addCondition = () => {
    const logic: AlertCondition['logic'] = conditions.length > 0 ? 'AND' : undefined;
    const newCond: AlertCondition = {
      id: generateId(),
      field: metric,
      operator: '>',
      value: 0,
      logic: undefined,
    };
    const updated = conditions.map((c, i) =>
      i === conditions.length - 1 ? { ...c, logic: logic ?? c.logic } : c
    );
    onChange([...updated, newCond]);
  };

  const removeCondition = (id: string) => {
    const updated = conditions.filter((c) => c.id !== id);
    if (updated.length > 0) {
      updated[updated.length - 1] = { ...updated[updated.length - 1], logic: undefined };
    }
    onChange(updated);
  };

  const updateCondition = (id: string, patch: Partial<AlertCondition>) => {
    onChange(conditions.map((c) => (c.id === id ? { ...c, ...patch } : c)));
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (over && active.id !== over.id) {
      const oldIndex = conditions.findIndex((c) => c.id === active.id);
      const newIndex = conditions.findIndex((c) => c.id === over.id);
      if (oldIndex !== -1 && newIndex !== -1) {
        let newConditions = arrayMove(conditions, oldIndex, newIndex);
        if (newConditions.length > 1) {
          newConditions = newConditions.map((c, i) =>
            i < newConditions.length - 1 ? c : { ...c, logic: undefined }
          );
        }
        onChange(newConditions);
      }
    }
  };

  const addGroup = (conditionId: string) => {
    const cond = conditions.find((c) => c.id === conditionId);
    if (!cond || cond.groupId) return;

    const nextCond = conditions[conditions.findIndex((c) => c.id === conditionId) + 1];
    const newGroupId = generateGroupId();
    const newGroup: ConditionGroup = {
      id: newGroupId,
      name: '新分组',
      logic: 'AND',
    };

    let newConditions = conditions.map((c) => {
      if (c.id === conditionId) return { ...c, groupId: newGroupId };
      if (nextCond && c.id === nextCond.id) return { ...c, groupId: newGroupId };
      return c;
    });

    const newGroups = [...groups, newGroup];
    if (onGroupsChange) onGroupsChange(newGroups);
    onChange(newConditions);
  };

  const removeGroup = (groupId: string) => {
    const newConditions = conditions.map((c) =>
      c.groupId === groupId ? { ...c, groupId: undefined } : c
    );
    const newGroups = groups.filter((g) => g.id !== groupId);
    if (onGroupsChange) onGroupsChange(newGroups);
    onChange(newConditions);
  };

  const toggleGroupCollapsed = (groupId: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  };

  const visibleConditions = useMemo(() => {
    return conditions.filter((c) => !c.groupId || !collapsedGroups.has(c.groupId));
  }, [conditions, collapsedGroups]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-xs text-brand-text-secondary">
          拖拽排序 · 点击 <Brackets className="inline h-3.5 w-3.5 align-[-2px] mx-0.5" /> 创建分组
        </div>
        <button
          type="button"
          onClick={addCondition}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-brand-cyan hover:bg-brand-card transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
          添加条件
        </button>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={visibleConditions.map((c) => c.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-2">
            {visibleConditions.map((cond, idx) => (
              <SortableCondition
                key={cond.id}
                condition={cond}
                index={idx}
                total={visibleConditions.length}
                groups={groups}
                metric={metric}
                isDragging={activeId === cond.id}
                onChange={(patch) => updateCondition(cond.id, patch)}
                onRemove={() => removeCondition(cond.id)}
                onAddGroup={() => addGroup(cond.id)}
                onRemoveGroup={() => cond.groupId && removeGroup(cond.groupId)}
              />
            ))}
          </div>
        </SortableContext>

        <DragOverlay>
          {activeCondition ? (
            <div className="bg-brand-card border border-brand-cyan/50 rounded-md px-2 py-1.5 shadow-lg shadow-brand-cyan/20 opacity-90">
              <span className="text-xs text-brand-text-primary font-mono-num">
                {METRIC_DISPLAY_CONFIG[metric]?.label || metric} {activeCondition.operator} {activeCondition.value}
              </span>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {conditions.length > 0 && (
        <div className="rounded-md bg-brand-dark px-3 py-2 border border-brand-border">
          <span className="text-[10px] text-brand-text-secondary">表达式预览：</span>
          <span className="ml-1 font-mono-num text-xs text-brand-cyan break-all">
            {buildPreview()}
          </span>
        </div>
      )}
    </div>
  );
}
