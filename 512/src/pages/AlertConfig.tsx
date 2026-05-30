import { useState, useEffect, useCallback } from 'react';
import type { ThresholdRule } from '@/types';
import { useAlertStore } from '@/stores/alert-store';
import { cn } from '@/utils/helpers';
import { Plus, X, AlertTriangle } from 'lucide-react';
import RuleTable from '@/components/RuleTable';
import RuleEditor from '@/components/RuleEditor';

type ToastType = 'success' | 'error';

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

export default function AlertConfig() {
  const rules = useAlertStore((s) => s.rules);
  const fetchRules = useAlertStore((s) => s.fetchRules);
  const createRule = useAlertStore((s) => s.createRule);
  const updateRuleApi = useAlertStore((s) => s.updateRuleApi);
  const deleteRuleApi = useAlertStore((s) => s.deleteRuleApi);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ThresholdRule | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    fetchRules().catch(() => addToast('加载规则失败', 'error'));
  }, []);

  const addToast = useCallback((message: string, type: ToastType) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3000);
  }, []);

  const handleCreate = () => {
    setEditingRule(null);
    setEditorOpen(true);
  };

  const handleEdit = (rule: ThresholdRule) => {
    setEditingRule(rule);
    setEditorOpen(true);
  };

  const handleSave = async (data: Omit<ThresholdRule, 'id' | 'createdAt' | 'updatedAt'>) => {
    try {
      if (editingRule) {
        await updateRuleApi(editingRule.id, data);
        addToast('规则更新成功', 'success');
      } else {
        await createRule(data);
        addToast('规则创建成功', 'success');
      }
      setEditorOpen(false);
      setEditingRule(null);
      await fetchRules();
    } catch {
      addToast(editingRule ? '更新规则失败' : '创建规则失败', 'error');
    }
  };

  const handleDelete = async (id: string) => {
    setConfirmDelete(id);
  };

  const confirmDeleteAction = async () => {
    if (!confirmDelete) return;
    try {
      await deleteRuleApi(confirmDelete);
      addToast('规则已删除', 'success');
      await fetchRules();
    } catch {
      addToast('删除规则失败', 'error');
    }
    setConfirmDelete(null);
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await updateRuleApi(id, { enabled });
      addToast(enabled ? '规则已启用' : '规则已禁用', 'success');
      await fetchRules();
    } catch {
      addToast('切换状态失败', 'error');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-brand-text-primary">预警规则配置</h2>
        <button
          onClick={handleCreate}
          className="flex items-center gap-1.5 rounded-lg bg-brand-cyan px-4 py-2 text-sm font-medium text-brand-dark hover:bg-brand-cyan/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          新增规则
        </button>
      </div>

      <RuleTable
        rules={rules}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onToggle={handleToggle}
      />

      <RuleEditor
        open={editorOpen}
        rule={editingRule}
        onClose={() => {
          setEditorOpen(false);
          setEditingRule(null);
        }}
        onSave={handleSave}
      />

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setConfirmDelete(null)}
          />
          <div className="relative w-full max-w-sm rounded-xl border border-brand-border bg-brand-surface p-6 shadow-2xl animate-slide-in-modal">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="h-6 w-6 text-brand-amber" />
              <h4 className="text-base font-semibold text-brand-text-primary">确认删除</h4>
            </div>
            <p className="text-sm text-brand-text-secondary mb-6">
              确定要删除此规则吗？此操作不可撤销。
            </p>
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setConfirmDelete(null)}
                className="rounded-md border border-brand-border px-4 py-2 text-sm text-brand-text-secondary hover:bg-brand-card transition-colors"
              >
                取消
              </button>
              <button
                onClick={confirmDeleteAction}
                className="rounded-md bg-brand-red px-4 py-2 text-sm font-medium text-white hover:bg-brand-red/90 transition-colors"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}

      {toasts.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 space-y-2">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={cn(
                'flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm shadow-lg animate-fade-in-up',
                t.type === 'success'
                  ? 'border-brand-green/30 bg-brand-green/10 text-brand-green'
                  : 'border-brand-red/30 bg-brand-red/10 text-brand-red'
              )}
            >
              {t.type === 'success' ? (
                <span className="h-2 w-2 rounded-full bg-brand-green" />
              ) : (
                <X className="h-4 w-4" />
              )}
              {t.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
