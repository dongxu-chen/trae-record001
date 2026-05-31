import { useState, useEffect, useCallback } from 'react';
import { Plus, Pencil, Trash2, X } from 'lucide-react';
import { useLifecycleStore } from '@/store';
import type { TTLPolicy, TTLRule, ActionType } from '@/types';
import { cn } from '@/lib/utils';

const EMPTY_POLICY: Omit<TTLPolicy, 'id' | 'created_at' | 'updated_at'> = {
  name: '',
  database: '',
  table: '',
  description: '',
  enabled: true,
  rules: [],
};

const EMPTY_RULE: Omit<TTLRule, 'id'> = {
  age_days: 30,
  action: 'move_to_disk' as ActionType,
  target_disk: '',
  priority: 0,
};

const ACTION_OPTIONS: { value: ActionType; label: string }[] = [
  { value: 'move_to_disk', label: 'Move to Disk' },
  { value: 'drop', label: 'Drop' },
  { value: 'freeze', label: 'Freeze' },
  { value: 'optimize', label: 'Optimize' },
];

function formatRuleBadge(rule: TTLRule) {
  const actionLabel = ACTION_OPTIONS.find((o) => o.value === rule.action)?.label ?? rule.action;
  const disk = rule.action === 'move_to_disk' && rule.target_disk ? ` → ${rule.target_disk}` : '';
  return `age >= ${rule.age_days} days → ${actionLabel}${disk}`;
}

export default function Policies() {
  const { policies, policiesLoading, policiesError, fetchPolicies, createPolicy, updatePolicy, deletePolicy } =
    useLifecycleStore();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_POLICY);
  const [deleteTarget, setDeleteTarget] = useState<TTLPolicy | null>(null);

  useEffect(() => {
    fetchPolicies();
  }, [fetchPolicies]);

  const openCreate = useCallback(() => {
    setEditingId(null);
    setForm(EMPTY_POLICY);
    setModalOpen(true);
  }, []);

  const openEdit = useCallback((policy: TTLPolicy) => {
    setEditingId(policy.id);
    setForm({
      name: policy.name,
      database: policy.database,
      table: policy.table,
      description: policy.description,
      enabled: policy.enabled,
      rules: policy.rules.map((r) => ({ ...r })),
    });
    setModalOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setModalOpen(false);
    setEditingId(null);
    setForm(EMPTY_POLICY);
  }, []);

  const handleSave = useCallback(async () => {
    if (editingId) {
      await updatePolicy(editingId, form);
    } else {
      await createPolicy(form);
    }
    closeModal();
  }, [editingId, form, createPolicy, updatePolicy, closeModal]);

  const handleDelete = useCallback(async () => {
    if (deleteTarget) {
      await deletePolicy(deleteTarget.id);
      setDeleteTarget(null);
    }
  }, [deleteTarget, deletePolicy]);

  const addRule = useCallback(() => {
    setForm((f) => ({
      ...f,
      rules: [...f.rules, { ...EMPTY_RULE, id: crypto.randomUUID(), priority: f.rules.length }],
    }));
  }, []);

  const removeRule = useCallback((idx: number) => {
    setForm((f) => ({
      ...f,
      rules: f.rules.filter((_, i) => i !== idx),
    }));
  }, []);

  const updateRule = useCallback((idx: number, patch: Partial<TTLRule>) => {
    setForm((f) => ({
      ...f,
      rules: f.rules.map((r, i) => (i === idx ? { ...r, ...patch } : r)),
    }));
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">策略管理</h1>
          <button
            onClick={openCreate}
            className="flex items-center gap-2 rounded-lg bg-sky-400 px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300"
          >
            <Plus className="h-4 w-4" />
            新建策略
          </button>
        </div>

        {policiesError && (
          <div className="mb-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">{policiesError}</div>
        )}

        {policiesLoading && policies.length === 0 ? (
          <div className="py-20 text-center text-slate-500">Loading...</div>
        ) : policies.length === 0 ? (
          <div className="py-20 text-center text-slate-500">暂无策略，点击上方按钮创建</div>
        ) : (
          <div className="grid gap-4">
            {policies.map((policy) => (
              <div
                key={policy.id}
                className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-5"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-semibold text-white">{policy.name}</span>
                      <span className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
                        {policy.database}.{policy.table}
                      </span>
                    </div>
                    {policy.description && (
                      <p className="mt-1 text-sm text-slate-400">{policy.description}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() =>
                        updatePolicy(policy.id, { ...policy, enabled: !policy.enabled })
                      }
                      className={cn(
                        'relative h-6 w-11 rounded-full transition-colors',
                        policy.enabled ? 'bg-green-500' : 'bg-slate-600'
                      )}
                    >
                      <span
                        className={cn(
                          'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform',
                          policy.enabled ? 'left-[22px]' : 'left-0.5'
                        )}
                      />
                    </button>
                    <button
                      onClick={() => openEdit(policy)}
                      className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-700 hover:text-white"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(policy)}
                      className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-red-500/10 hover:text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {policy.rules.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {policy.rules.map((rule) => (
                      <span
                        key={rule.id}
                        className="rounded-md bg-slate-700/60 px-2.5 py-1 text-xs text-slate-300"
                      >
                        {formatRuleBadge(rule)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-800 p-6 shadow-2xl">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">
                {editingId ? '编辑策略' : '新建策略'}
              </h2>
              <button onClick={closeModal} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm text-slate-300">名称</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-sky-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm text-slate-300">Database</label>
                  <input
                    value={form.database}
                    onChange={(e) => setForm((f) => ({ ...f, database: e.target.value }))}
                    className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-sky-400"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-300">Table</label>
                  <input
                    value={form.table}
                    onChange={(e) => setForm((f) => ({ ...f, table: e.target.value }))}
                    className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-sky-400"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm text-slate-300">描述</label>
                <input
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-sky-400"
                />
              </div>

              <div className="flex items-center gap-3">
                <label className="text-sm text-slate-300">启用</label>
                <button
                  onClick={() => setForm((f) => ({ ...f, enabled: !f.enabled }))}
                  className={cn(
                    'relative h-6 w-11 rounded-full transition-colors',
                    form.enabled ? 'bg-green-500' : 'bg-slate-600'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform',
                      form.enabled ? 'left-[22px]' : 'left-0.5'
                    )}
                  />
                </button>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-sm text-slate-300">规则</label>
                  <button
                    onClick={addRule}
                    className="flex items-center gap-1 rounded px-2 py-0.5 text-xs text-sky-400 transition-colors hover:bg-slate-700"
                  >
                    <Plus className="h-3 w-3" />
                    添加规则
                  </button>
                </div>

                <div className="space-y-3">
                  {form.rules.map((rule, idx) => (
                    <div
                      key={rule.id}
                      className="rounded-lg border border-slate-700 bg-slate-900/60 p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="grid flex-1 grid-cols-2 gap-2">
                          <div>
                            <label className="mb-0.5 block text-xs text-slate-400">Age (days)</label>
                            <input
                              type="number"
                              min={0}
                              value={rule.age_days}
                              onChange={(e) =>
                                updateRule(idx, { age_days: Number(e.target.value) })
                              }
                              className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1 text-sm text-white outline-none focus:border-sky-400"
                            />
                          </div>
                          <div>
                            <label className="mb-0.5 block text-xs text-slate-400">Action</label>
                            <select
                              value={rule.action}
                              onChange={(e) =>
                                updateRule(idx, { action: e.target.value as ActionType })
                              }
                              className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1 text-sm text-white outline-none focus:border-sky-400"
                            >
                              {ACTION_OPTIONS.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                  {opt.label}
                                </option>
                              ))}
                            </select>
                          </div>
                          {rule.action === 'move_to_disk' && (
                            <div>
                              <label className="mb-0.5 block text-xs text-slate-400">
                                Target Disk
                              </label>
                              <input
                                value={rule.target_disk ?? ''}
                                onChange={(e) =>
                                  updateRule(idx, { target_disk: e.target.value })
                                }
                                className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1 text-sm text-white outline-none focus:border-sky-400"
                              />
                            </div>
                          )}
                          <div>
                            <label className="mb-0.5 block text-xs text-slate-400">Priority</label>
                            <input
                              type="number"
                              min={0}
                              value={rule.priority}
                              onChange={(e) =>
                                updateRule(idx, { priority: Number(e.target.value) })
                              }
                              className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1 text-sm text-white outline-none focus:border-sky-400"
                            />
                          </div>
                        </div>
                        <button
                          onClick={() => removeRule(idx)}
                          className="mt-4 rounded p-1 text-slate-400 hover:text-red-400"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={closeModal}
                className="rounded-lg px-4 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-700"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={!form.name || !form.database || !form.table}
                className="rounded-lg bg-sky-400 px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-800 p-6 shadow-2xl">
            <h2 className="mb-2 text-lg font-semibold text-white">确认删除</h2>
            <p className="mb-6 text-sm text-slate-400">
              确定要删除策略「{deleteTarget.name}」吗？此操作不可撤销。
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="rounded-lg px-4 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-700"
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                className="rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-400"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
