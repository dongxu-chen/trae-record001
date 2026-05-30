import { useState } from 'react';
import { Users, Star, Clock, Globe, Calendar, CheckCircle2, XCircle, Mail, UserPlus, Briefcase, Filter, ChevronDown, Eye } from 'lucide-react';
import type { TesterProfile, TestTask, ColorblindType } from '@/types';
import { COLORBLIND_TYPES } from '@/types';
import { MOCK_TESTERS, MOCK_TEST_TASKS } from '@/utils/batchScan';

export default function UserTestingRecruitment() {
  const [activeTab, setActiveTab] = useState<'testers' | 'tasks'>('testers');
  const [selectedTypes, setSelectedTypes] = useState<ColorblindType[]>([]);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [applyForm, setApplyForm] = useState({
    name: '',
    email: '',
    colorblindTypes: [] as ColorblindType[],
    severity: 'moderate' as 'mild' | 'moderate' | 'severe',
    bio: '',
  });

  const toggleColorblindType = (type: ColorblindType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const toggleApplyColorblindType = (type: ColorblindType) => {
    setApplyForm((prev) => ({
      ...prev,
      colorblindTypes: prev.colorblindTypes.includes(type)
        ? prev.colorblindTypes.filter((t) => t !== type)
        : [...prev.colorblindTypes, type],
    }));
  };

  const filteredTesters = selectedTypes.length > 0
    ? MOCK_TESTERS.filter((t) => t.colorblindTypes.some((ct) => selectedTypes.includes(ct)))
    : MOCK_TESTERS;

  const getColorblindBadge = (type: ColorblindType) => {
    const info = COLORBLIND_TYPES.find((t) => t.id === type);
    const categoryColors = {
      'red-green': 'bg-red-500/10 text-red-400 border-red-500/20',
      'blue-yellow': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      'total': 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    };
    return (
      <span
        key={type}
        className={`px-2 py-0.5 rounded text-xs font-medium border ${categoryColors[info?.category || 'red-green']}`}
      >
        {info?.labelZh}
      </span>
    );
  };

  const getSeverityLabel = (severity: string) => {
    const map: Record<string, { label: string; color: string }> = {
      mild: { label: '轻度', color: 'text-green-400' },
      moderate: { label: '中度', color: 'text-yellow-400' },
      severe: { label: '重度', color: 'text-red-400' },
    };
    return map[severity] || map.moderate;
  };

  const getExperienceLabel = (exp: string) => {
    const map: Record<string, string> = {
      beginner: '初级',
      intermediate: '中级',
      expert: '专家',
    };
    return map[exp] || '中级';
  };

  const getAvailabilityLabel = (avail: string) => {
    const map: Record<string, string> = {
      weekdays: '工作日',
      weekends: '周末',
      flexible: '时间灵活',
    };
    return map[avail] || '工作日';
  };

  const getTaskStatus = (status: string) => {
    const map: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
      open: { label: '招募中', color: 'text-[#00d4aa]', icon: <UserPlus className="w-3.5 h-3.5" /> },
      in_progress: { label: '进行中', color: 'text-yellow-400', icon: <Clock className="w-3.5 h-3.5" /> },
      completed: { label: '已完成', color: 'text-zinc-500', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
    };
    return map[status] || map.open;
  };

  return (
    <div className="space-y-6">
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#00d4aa]/10 flex items-center justify-center">
              <Users className="w-5 h-5 text-[#00d4aa]" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-zinc-100">真实色盲用户测试</h3>
              <p className="text-sm text-zinc-500">连接全球色盲用户，获取真实体验反馈</p>
            </div>
          </div>
          <button
            onClick={() => setShowApplyModal(true)}
            className="px-4 py-2 rounded-lg bg-[#00d4aa] text-zinc-900 text-sm font-medium hover:bg-[#00d4aa]/90 transition-colors flex items-center gap-2"
          >
            <UserPlus className="w-4 h-4" />
            申请成为测试员
          </button>
        </div>

        <div className="flex gap-2 p-1 bg-zinc-950 rounded-lg">
          <button
            onClick={() => setActiveTab('testers')}
            className={`flex-1 py-2.5 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
              activeTab === 'testers'
                ? 'bg-zinc-800 text-zinc-200'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <Users className="w-4 h-4" />
            测试员库 ({MOCK_TESTERS.length})
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            className={`flex-1 py-2.5 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
              activeTab === 'tasks'
                ? 'bg-zinc-800 text-zinc-200'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <Briefcase className="w-4 h-4" />
            测试任务 ({MOCK_TEST_TASKS.length})
          </button>
        </div>
      </div>

      {activeTab === 'testers' && (
        <>
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Filter className="w-4 h-4 text-zinc-500" />
              <span className="text-sm text-zinc-400">按色盲类型筛选</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {COLORBLIND_TYPES.map((type) => (
                <button
                  key={type.id}
                  onClick={() => toggleColorblindType(type.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    selectedTypes.includes(type.id)
                      ? 'bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/30'
                      : 'bg-zinc-800 text-zinc-400 border border-transparent hover:border-zinc-700'
                  }`}
                >
                  {type.labelZh}
                </button>
              ))}
              {selectedTypes.length > 0 && (
                <button
                  onClick={() => setSelectedTypes([])}
                  className="px-3 py-1.5 rounded-lg text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  清除筛选
                </button>
              )}
            </div>
          </div>

          <div className="space-y-4">
            {filteredTesters.map((tester) => (
              <div
                key={tester.id}
                className="bg-zinc-900 rounded-xl border border-zinc-800 p-5 hover:border-zinc-700 transition-colors"
              >
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[#00d4aa]/20 to-[#00d4aa]/5 flex items-center justify-center text-xl font-bold text-[#00d4aa] shrink-0">
                    {tester.name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="text-base font-semibold text-zinc-100">{tester.name}</h4>
                      <div className="flex items-center gap-1 text-yellow-400">
                        <Star className="w-3.5 h-3.5 fill-yellow-400" />
                        <span className="text-xs font-medium">{tester.rating}</span>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {tester.colorblindTypes.map((type) => getColorblindBadge(type))}
                    </div>
                    <p className="text-sm text-zinc-400 mb-3 line-clamp-2">{tester.bio}</p>
                    <div className="flex flex-wrap gap-4 text-xs text-zinc-500">
                      <span className="flex items-center gap-1">
                        <span className={`font-medium ${getSeverityLabel(tester.severity).color}`}>
                          {getSeverityLabel(tester.severity).label}
                        </span>
                      </span>
                      <span className="flex items-center gap-1">
                        <Briefcase className="w-3 h-3" />
                        {getExperienceLabel(tester.experience)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {getAvailabilityLabel(tester.availability)}
                      </span>
                      <span className="flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        {tester.completedTests} 次测试
                      </span>
                      <span className="flex items-center gap-1">
                        <Globe className="w-3 h-3" />
                        {tester.languages.join('、')}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 shrink-0">
                    <button className="px-4 py-2 rounded-lg bg-[#00d4aa]/10 text-[#00d4aa] text-sm font-medium hover:bg-[#00d4aa]/20 transition-colors flex items-center gap-2">
                      <Eye className="w-4 h-4" />
                      查看详情
                    </button>
                    <button className="px-4 py-2 rounded-lg bg-zinc-800 text-zinc-300 text-sm font-medium hover:bg-zinc-700 transition-colors flex items-center gap-2">
                      <Mail className="w-4 h-4" />
                      邀请测试
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {activeTab === 'tasks' && (
        <div className="space-y-4">
          {MOCK_TEST_TASKS.map((task) => {
            const status = getTaskStatus(task.status);
            return (
              <div
                key={task.id}
                className="bg-zinc-900 rounded-xl border border-zinc-800 p-5 hover:border-zinc-700 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-base font-semibold text-zinc-100">{task.title}</h4>
                      <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${status.color} bg-zinc-800`}>
                        {status.icon}
                        {status.label}
                      </span>
                    </div>
                    <p className="text-sm text-zinc-500 font-mono">{task.url}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-[#00d4aa]">{task.compensation}</p>
                    <p className="text-xs text-zinc-500">{task.estimatedTime}</p>
                  </div>
                </div>

                <p className="text-sm text-zinc-400 mb-4">{task.description}</p>

                <div className="flex items-center gap-2 mb-4">
                  <span className="text-xs text-zinc-500">目标用户:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {task.targetColorblindTypes.map((type) => getColorblindBadge(type))}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-zinc-800">
                  <div className="flex items-center gap-4 text-xs text-zinc-500">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      截止: {task.deadline.toLocaleDateString()}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" />
                      {task.applicants.length} 人申请
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {task.acceptedTester && (
                      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800">
                        <div className="w-6 h-6 rounded bg-[#00d4aa]/20 flex items-center justify-center text-xs font-bold text-[#00d4aa]">
                          {task.acceptedTester.name.charAt(0)}
                        </div>
                        <span className="text-xs text-zinc-300">{task.acceptedTester.name}</span>
                      </div>
                    )}
                    {task.status === 'open' && (
                      <button className="px-4 py-2 rounded-lg bg-[#00d4aa] text-zinc-900 text-sm font-medium hover:bg-[#00d4aa]/90 transition-colors">
                        申请参与
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showApplyModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 rounded-2xl border border-zinc-800 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-zinc-800">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-zinc-100">申请成为测试员</h3>
                <button
                  onClick={() => setShowApplyModal(false)}
                  className="w-8 h-8 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors flex items-center justify-center"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">姓名</label>
                <input
                  type="text"
                  value={applyForm.name}
                  onChange={(e) => setApplyForm({ ...applyForm, name: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 placeholder-zinc-500 focus:border-[#00d4aa] focus:outline-none transition-colors"
                  placeholder="请输入你的姓名"
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-2">邮箱</label>
                <input
                  type="email"
                  value={applyForm.email}
                  onChange={(e) => setApplyForm({ ...applyForm, email: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 placeholder-zinc-500 focus:border-[#00d4aa] focus:outline-none transition-colors"
                  placeholder="your@email.com"
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-2">你的色盲类型（可多选）</label>
                <div className="grid grid-cols-2 gap-2">
                  {COLORBLIND_TYPES.map((type) => (
                    <button
                      key={type.id}
                      onClick={() => toggleApplyColorblindType(type.id)}
                      className={`p-3 rounded-lg text-left transition-colors ${
                        applyForm.colorblindTypes.includes(type.id)
                          ? 'bg-[#00d4aa]/10 border-[#00d4aa]/30 border'
                          : 'bg-zinc-800 border border-transparent hover:border-zinc-700'
                      }`}
                    >
                      <p className={`text-sm font-medium ${applyForm.colorblindTypes.includes(type.id) ? 'text-[#00d4aa]' : 'text-zinc-200'}`}>
                        {type.labelZh}
                      </p>
                      <p className="text-xs text-zinc-500">{type.prevalence}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-2">严重程度</label>
                <div className="flex gap-2">
                  {(['mild', 'moderate', 'severe'] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => setApplyForm({ ...applyForm, severity: s })}
                      className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                        applyForm.severity === s
                          ? 'bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/30'
                          : 'bg-zinc-800 text-zinc-400 border border-transparent hover:border-zinc-700'
                      }`}
                    >
                      {getSeverityLabel(s).label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-2">个人简介</label>
                <textarea
                  value={applyForm.bio}
                  onChange={(e) => setApplyForm({ ...applyForm, bio: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 placeholder-zinc-500 focus:border-[#00d4aa] focus:outline-none transition-colors resize-none"
                  rows={3}
                  placeholder="介绍一下你的背景、无障碍测试经验等..."
                />
              </div>
            </div>
            <div className="p-6 border-t border-zinc-800 flex gap-3">
              <button
                onClick={() => setShowApplyModal(false)}
                className="flex-1 py-3 rounded-lg bg-zinc-800 text-zinc-300 font-medium hover:bg-zinc-700 transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => {
                  alert('申请已提交！我们会尽快审核你的资料。');
                  setShowApplyModal(false);
                }}
                className="flex-1 py-3 rounded-lg bg-[#00d4aa] text-zinc-900 font-medium hover:bg-[#00d4aa]/90 transition-colors"
              >
                提交申请
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
