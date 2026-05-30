import { Shield, AlertTriangle, Clock, Server, CheckCircle2, ChevronDown, ChevronRight } from 'lucide-react';
import { useLineageStore } from '@/stores/useLineageStore';
import { getChangeTypeLabel, getRiskLevelLabel, getRiskLevelColor, getRiskLevelBgColor, getRiskLevelTextColor } from '@/services/riskAssessment';
import { ChangeType, RiskLevel } from '@/types';
import { useState } from 'react';

const CHANGE_TYPES: ChangeType[] = ['delete', 'type_change', 'rename', 'constraint_change', 'default_change'];

const RISK_GAUGE_COLORS: Record<RiskLevel, string> = {
  low: '#00B42A',
  medium: '#FF7D00',
  high: '#F53F3F',
  critical: '#7B1FA2',
};

export const RiskAssessmentPanel = () => {
  const { analysisResult, riskAssessment, selectedChangeType, setSelectedChangeType, assessRisk } = useLineageStore();
  const [expandedFactors, setExpandedFactors] = useState<Set<string>>(new Set());

  if (!analysisResult) {
    return (
      <div className="p-4 text-center text-gray-500">
        <Shield className="w-10 h-10 mx-auto mb-2 text-gray-300" />
        <p className="text-sm">请先进行血缘分析</p>
      </div>
    );
  }

  const handleAssess = (changeType: ChangeType) => {
    setSelectedChangeType(changeType);
    assessRisk(analysisResult.fieldId, changeType);
  };

  const toggleFactor = (id: string) => {
    setExpandedFactors(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const gaugeAngle = riskAssessment ? (riskAssessment.riskScore / 100) * 180 : 0;

  return (
    <div className="space-y-5">
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <Shield className="w-4 h-4 text-primary-500" />
          变更类型选择
        </h4>
        <div className="grid grid-cols-3 gap-2">
          {CHANGE_TYPES.map(type => (
            <button
              key={type}
              onClick={() => handleAssess(type)}
              className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                selectedChangeType === type
                  ? 'bg-primary-50 border-primary-300 text-primary-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              {getChangeTypeLabel(type)}
            </button>
          ))}
        </div>
      </div>

      {riskAssessment && (
        <>
          <div className={`rounded-xl p-4 bg-gradient-to-br ${getRiskLevelBgColor(riskAssessment.riskLevel)}`}>
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-xs text-gray-500">风险等级</div>
                <div className={`text-xl font-bold ${getRiskLevelTextColor(riskAssessment.riskLevel)}`}>
                  {getRiskLevelLabel(riskAssessment.riskLevel)}
                </div>
              </div>
              <div className="relative w-20 h-12 overflow-hidden">
                <svg viewBox="0 0 100 60" className="w-full h-full">
                  <path d="M 10 55 A 40 40 0 0 1 90 55" fill="none" stroke="#E5E6EB" strokeWidth="8" strokeLinecap="round" />
                  <path
                    d="M 10 55 A 40 40 0 0 1 90 55"
                    fill="none"
                    stroke={RISK_GAUGE_COLORS[riskAssessment.riskLevel]}
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={`${gaugeAngle * 0.7} 200`}
                  />
                  <text x="50" y="50" textAnchor="middle" className="text-2xl font-bold" fill={RISK_GAUGE_COLORS[riskAssessment.riskLevel]} style={{ fontSize: '18px', fontWeight: 700 }}>
                    {riskAssessment.riskScore}
                  </text>
                </svg>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 mt-3">
              <div className="bg-white/60 rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-gray-900">{riskAssessment.impactScope.affectedETLTasks}</div>
                <div className="text-xs text-gray-500">ETL任务</div>
              </div>
              <div className="bg-white/60 rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-gray-900">{riskAssessment.impactScope.affectedReports}</div>
                <div className="text-xs text-gray-500">报表</div>
              </div>
              <div className="bg-white/60 rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-gray-900">{riskAssessment.impactScope.affectedOwners}</div>
                <div className="text-xs text-gray-500">影响负责人</div>
              </div>
              <div className="bg-white/60 rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-gray-900">{riskAssessment.estimatedRecoveryTime}</div>
                <div className="text-xs text-gray-500">预估恢复</div>
              </div>
            </div>

            {riskAssessment.requiresDowntime && (
              <div className="mt-3 flex items-center gap-2 bg-red-100 rounded-lg px-3 py-2">
                <AlertTriangle className="w-4 h-4 text-red-600" />
                <span className="text-xs font-medium text-red-700">此变更需要停机维护</span>
              </div>
            )}
          </div>

          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              风险因子
            </h4>
            <div className="space-y-2">
              {riskAssessment.riskFactors.map(factor => (
                <div key={factor.id} className="border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() => toggleFactor(factor.id)}
                    className="w-full px-3 py-2 flex items-center gap-2 bg-gray-50 hover:bg-gray-100 transition-colors"
                  >
                    {expandedFactors.has(factor.id) ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )}
                    <span className="text-sm text-gray-800 text-left flex-1">{factor.description}</span>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${getRiskLevelColor(factor.severity)}`}>
                      {getRiskLevelLabel(factor.severity)}
                    </span>
                  </button>
                  {expandedFactors.has(factor.id) && factor.affectedItems.length > 0 && (
                    <div className="p-3 bg-white space-y-1">
                      {factor.affectedItems.map((item, idx) => (
                        <div key={idx} className="text-xs text-gray-600 flex items-center gap-1">
                          <span className="w-1 h-1 rounded-full bg-gray-400" />
                          {item}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              变更建议
            </h4>
            <div className="space-y-2">
              {riskAssessment.recommendations.map((rec, idx) => (
                <div key={idx} className="flex items-start gap-2 p-2 bg-green-50 rounded-lg">
                  <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{rec}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
