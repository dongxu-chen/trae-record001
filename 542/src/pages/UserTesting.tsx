import UserTestingRecruitment from '@/components/UserTestingRecruitment';
import { Users, Heart, Award, MessageSquare, Shield, Zap } from 'lucide-react';

const benefits = [
  {
    icon: <Heart className="w-5 h-5" />,
    title: '真实用户反馈',
    description: '来自全球真实色盲用户的第一手体验数据',
  },
  {
    icon: <Award className="w-5 h-5" />,
    title: '专业测试员',
    description: '经过认证的无障碍测试专家，提供专业意见',
  },
  {
    icon: <Zap className="w-5 h-5" />,
    title: '快速匹配',
    description: '智能匹配适合你项目的测试人员',
  },
  {
    icon: <MessageSquare className="w-5 h-5" />,
    title: '详细报告',
    description: '结构化的问题报告，附带截图和改进建议',
  },
  {
    icon: <Shield className="w-5 h-5" />,
    title: '隐私保护',
    description: '所有测试数据安全加密，严格保密',
  },
];

export default function UserTesting() {
  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#00d4aa]/10 text-[#00d4aa] text-sm font-medium">
          <Users className="w-4 h-4" />
          用户测试
        </div>
        <h1 className="text-3xl md:text-4xl font-bold text-zinc-100">
          连接真实色盲用户
        </h1>
        <p className="text-zinc-500 max-w-xl mx-auto">
          招募全球色盲用户进行真实体验测试，获取最真实的无障碍反馈。从用户视角发现问题，提升产品体验。
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {benefits.map((benefit, idx) => (
          <div
            key={idx}
            className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 text-center hover:border-zinc-700 transition-colors"
          >
            <div className="w-10 h-10 rounded-full bg-[#00d4aa]/10 flex items-center justify-center text-[#00d4aa] mx-auto mb-3">
              {benefit.icon}
            </div>
            <h3 className="text-sm font-semibold text-zinc-200 mb-1">{benefit.title}</h3>
            <p className="text-xs text-zinc-500">{benefit.description}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5 text-center">
          <p className="text-3xl font-bold text-[#00d4aa] font-mono">500+</p>
          <p className="text-xs text-zinc-500 mt-1">注册测试员</p>
        </div>
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5 text-center">
          <p className="text-3xl font-bold text-zinc-200 font-mono">8</p>
          <p className="text-xs text-zinc-500 mt-1">色盲类型覆盖</p>
        </div>
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5 text-center">
          <p className="text-3xl font-bold text-[#ff6b35] font-mono">1200+</p>
          <p className="text-xs text-zinc-500 mt-1">已完成测试</p>
        </div>
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5 text-center">
          <p className="text-3xl font-bold text-yellow-400 font-mono">4.8</p>
          <p className="text-xs text-zinc-500 mt-1">平均满意度</p>
        </div>
      </div>

      <UserTestingRecruitment />

      <div className="bg-gradient-to-r from-[#00d4aa]/10 via-[#00d4aa]/5 to-transparent rounded-2xl border border-[#00d4aa]/20 p-8">
        <div className="max-w-2xl">
          <h2 className="text-2xl font-bold text-zinc-100 mb-3">
            为什么需要真实用户测试？
          </h2>
          <p className="text-zinc-400 mb-6 leading-relaxed">
            自动化检测工具只能发现可量化的对比度问题，但真实用户体验涉及更多主观因素。
            色盲用户在实际使用中遇到的困惑、挫败感和操作障碍，只有通过真实测试才能发现。
            我们的测试员来自不同行业、不同文化背景，能为你提供最全面的无障碍反馈。
          </p>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-zinc-900/50 rounded-lg p-4">
              <p className="text-2xl font-bold text-[#00d4aa] mb-1">43%</p>
              <p className="text-xs text-zinc-500">的问题只有真实用户能发现</p>
            </div>
            <div className="bg-zinc-900/50 rounded-lg p-4">
              <p className="text-2xl font-bold text-[#00d4aa] mb-1">89%</p>
              <p className="text-xs text-zinc-500">的客户选择重复下单</p>
            </div>
            <div className="bg-zinc-900/50 rounded-lg p-4">
              <p className="text-2xl font-bold text-[#00d4aa] mb-1">72h</p>
              <p className="text-xs text-zinc-500">平均完成测试周期</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
