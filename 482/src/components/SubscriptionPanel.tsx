import { useState } from 'react';
import { Bell, BellOff, Plus, Mail, Send, Clock, User, CheckCircle, XCircle, Trash2 } from 'lucide-react';
import { useLineageStore } from '@/stores/useLineageStore';
import { getChangeTypeLabel } from '@/services/subscription';
import { getRiskLevelLabel, getRiskLevelColor } from '@/services/riskAssessment';
import { ChangeType, RiskLevel, ChangeSubscription } from '@/types';

const ALL_CHANGE_TYPES: ChangeType[] = ['delete', 'type_change', 'rename', 'constraint_change', 'default_change'];
const ALL_RISK_LEVELS: RiskLevel[] = ['low', 'medium', 'high', 'critical'];

export const SubscriptionPanel = () => {
  const {
    analysisResult,
    selectedField,
    subscriptions,
    notifications,
    addSubscription,
    removeSubscription,
    triggerNotification,
    loadSubscriptions,
    loadNotifications,
    getDownstreamOwnerList,
  } = useLineageStore();

  const [showAddForm, setShowAddForm] = useState(false);
  const [formEmail, setFormEmail] = useState('');
  const [formName, setFormName] = useState('');
  const [formChangeTypes, setFormChangeTypes] = useState<ChangeType[]>(['delete', 'type_change']);
  const [formRiskLevels, setFormRiskLevels] = useState<RiskLevel[]>(['high', 'critical']);
  const [notifyResult, setNotifyResult] = useState<{ count: number; emails: string[] } | null>(null);

  const downstreamOwners = getDownstreamOwnerList();

  const handleAddSubscription = () => {
    if (!selectedField || !formEmail || !formName) return;
    addSubscription({
      fieldId: selectedField.id,
      fieldName: selectedField.name,
      subscriberEmail: formEmail,
      subscriberName: formName,
      changeTypes: formChangeTypes,
      notifyOnRiskLevel: formRiskLevels,
      isActive: true,
    });
    setFormEmail('');
    setFormName('');
    setFormChangeTypes(['delete', 'type_change']);
    setFormRiskLevels(['high', 'critical']);
    setShowAddForm(false);
  };

  const handleNotify = () => {
    if (!analysisResult) return;
    const notifs = triggerNotification(
      analysisResult.fieldId,
      analysisResult.fieldName,
      'type_change',
      `${analysisResult.fieldName}字段类型拟变更，请评估影响`,
      'high'
    );
    setNotifyResult({
      count: notifs.length,
      emails: notifs.flatMap(n => n.notifiedEmails),
    });
    setTimeout(() => setNotifyResult(null), 5000);
  };

  const handleRefreshSubs = () => {
    if (selectedField) {
      loadSubscriptions(selectedField.id);
      loadNotifications(selectedField.id);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <Bell className="w-4 h-4 text-primary-500" />
          变更订阅
        </h4>
        <div className="flex gap-2">
          <button
            onClick={handleRefreshSubs}
            className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            <Clock className="w-3 h-3" />
            刷新
          </button>
        </div>
      </div>

      {analysisResult && (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4">
          <h5 className="text-xs font-medium text-gray-600 mb-2">下游影响负责人</h5>
          {downstreamOwners.length > 0 ? (
            <div className="space-y-2">
              {downstreamOwners.map((owner, idx) => (
                <div key={idx} className="flex items-center gap-2 bg-white/60 rounded-lg px-3 py-2">
                  <User className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-700 flex-1">{owner.name}</span>
                  <span className="text-xs text-gray-500">{owner.role}</span>
                  <Mail className="w-3 h-3 text-gray-400" />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-500">暂无下游负责人</p>
          )}
          <button
            onClick={handleNotify}
            className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg text-sm font-medium hover:bg-primary-600 transition-colors"
          >
            <Send className="w-4 h-4" />
            模拟发送变更通知
          </button>
          {notifyResult && (
            <div className="mt-2 p-2 bg-green-50 rounded-lg flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="text-xs text-green-700">
                已向 {notifyResult.count} 位订阅者发送通知
              </span>
            </div>
          )}
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-2">
          <h5 className="text-xs font-medium text-gray-500 uppercase">订阅列表</h5>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-1 text-xs text-primary-500 hover:text-primary-600"
          >
            <Plus className="w-3 h-3" />
            新增订阅
          </button>
        </div>

        {showAddForm && (
          <div className="p-3 bg-primary-50 rounded-xl border border-primary-100 mb-3 space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">订阅人姓名</label>
              <input
                type="text"
                value={formName}
                onChange={e => setFormName(e.target.value)}
                className="input-field text-sm"
                placeholder="输入姓名"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">邮箱地址</label>
              <input
                type="email"
                value={formEmail}
                onChange={e => setFormEmail(e.target.value)}
                className="input-field text-sm"
                placeholder="user@company.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">订阅变更类型</label>
              <div className="flex flex-wrap gap-2">
                {ALL_CHANGE_TYPES.map(type => (
                  <label key={type} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formChangeTypes.includes(type)}
                      onChange={e => {
                        if (e.target.checked) {
                          setFormChangeTypes([...formChangeTypes, type]);
                        } else {
                          setFormChangeTypes(formChangeTypes.filter(t => t !== type));
                        }
                      }}
                      className="w-3 h-3"
                    />
                    <span className="text-xs text-gray-600">{getChangeTypeLabel(type)}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">通知风险等级</label>
              <div className="flex flex-wrap gap-2">
                {ALL_RISK_LEVELS.map(level => (
                  <label key={level} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formRiskLevels.includes(level)}
                      onChange={e => {
                        if (e.target.checked) {
                          setFormRiskLevels([...formRiskLevels, level]);
                        } else {
                          setFormRiskLevels(formRiskLevels.filter(l => l !== level));
                        }
                      }}
                      className="w-3 h-3"
                    />
                    <span className={`text-xs ${getRiskLevelColor(level)} px-1.5 py-0.5 rounded`}>
                      {getRiskLevelLabel(level)}
                    </span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowAddForm(false)} className="btn-secondary text-xs flex-1">
                取消
              </button>
              <button onClick={handleAddSubscription} className="btn-primary text-xs flex-1" disabled={!formEmail || !formName}>
                确认订阅
              </button>
            </div>
          </div>
        )}

        {subscriptions.length > 0 ? (
          <div className="space-y-2">
            {subscriptions.map(sub => (
              <div key={sub.id} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bell className="w-4 h-4 text-primary-500" />
                    <div>
                      <div className="text-sm font-medium text-gray-900">{sub.subscriberName}</div>
                      <div className="text-xs text-gray-500">{sub.subscriberEmail}</div>
                    </div>
                  </div>
                  <button
                    onClick={() => removeSubscription(sub.id)}
                    className="p-1 hover:bg-red-50 rounded"
                    title="取消订阅"
                  >
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {sub.changeTypes.map(type => (
                    <span key={type} className="px-1.5 py-0.5 text-xs bg-blue-50 text-blue-600 rounded">
                      {getChangeTypeLabel(type)}
                    </span>
                  ))}
                  {sub.notifyOnRiskLevel.map(level => (
                    <span key={level} className={`px-1.5 py-0.5 text-xs rounded ${getRiskLevelColor(level)}`}>
                      {getRiskLevelLabel(level)}
                    </span>
                  ))}
                </div>
                {sub.lastNotifiedAt && (
                  <div className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    上次通知: {new Date(sub.lastNotifiedAt).toLocaleString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-4 text-gray-400">
            <BellOff className="w-8 h-8 mx-auto mb-2" />
            <p className="text-xs">暂无订阅</p>
          </div>
        )}
      </div>

      {notifications.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">通知记录</h5>
          <div className="space-y-2">
            {notifications.slice(-5).reverse().map(notif => (
              <div key={notif.id} className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-700">{notif.changeDescription}</span>
                  <span className={`px-1.5 py-0.5 text-xs rounded ${getRiskLevelColor(notif.riskLevel)}`}>
                    {getRiskLevelLabel(notif.riskLevel)}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    {notif.status === 'sent' ? (
                      <CheckCircle className="w-3 h-3 text-green-500" />
                    ) : (
                      <XCircle className="w-3 h-3 text-red-500" />
                    )}
                    {notif.status === 'sent' ? '已发送' : notif.status === 'pending' ? '待发送' : '发送失败'}
                  </span>
                  <span>{new Date(notif.notifiedAt).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
