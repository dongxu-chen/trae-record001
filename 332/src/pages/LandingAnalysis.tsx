import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, Users, MapPin, Smartphone, Globe, Clock, TrendingUp, Target, PieChart, Activity, ArrowRight, Eye } from 'lucide-react';
import { toast } from '@/components/ui/toast';
import { useAuthStore, useDynamicCodeStore } from '@/store';
import { dynamicCodeAPI, statsAPI } from '@/utils/api';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Filler } from 'chart.js';
import { Pie, Bar, Line, Doughnut } from 'react-chartjs-2';
import type { LandingPageAnalysis, CodeAnalysis, UserProfile, DynamicCode } from '@/types';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Filler);

const ageGroups = ['18-24', '25-34', '35-44', '45-54', '55+'];
const genders = ['男性', '女性', '未知'];
const interests = ['科技', '电商', '教育', '娱乐', '资讯', '游戏', '生活服务', '金融'];

export default function LandingAnalysis() {
  const { isAuthenticated } = useAuthStore();
  const { codes } = useDynamicCodeStore();
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'7' | '30' | '90'>('30');
  const [analysis, setAnalysis] = useState<CodeAnalysis | null>(null);
  const [userProfiles, setUserProfiles] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated() && codes.length > 0) {
      loadAnalysis();
    }
  }, [selectedCode, timeRange, codes]);

  const loadAnalysis = async () => {
    if (!selectedCode) {
      if (codes.length > 0) {
        setSelectedCode(codes[0].id);
      }
      return;
    }

    setLoading(true);
    try {
      const code = codes.find(c => c.id === selectedCode);
      if (code) {
        const mockProfiles = generateMockUserProfiles(50);
        setUserProfiles(mockProfiles);
        
        const mockAnalysis = generateMockAnalysis(code);
        setAnalysis(mockAnalysis);
      }
    } catch (error) {
      toast.error('加载分析数据失败');
    } finally {
      setLoading(false);
    }
  };

  const generateMockUserProfiles = (count: number): UserProfile[] => {
    const countries = ['中国', '美国', '日本', '德国', '英国', '法国', '韩国', '澳大利亚'];
    const regions = ['北京', '上海', '广东', '浙江', '江苏', '四川', '湖北', '山东'];
    const cities = ['北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '武汉'];
    const browsers = ['Chrome', 'Safari', 'Firefox', 'Edge', 'Opera', '微信浏览器'];
    const osList = ['Windows', 'macOS', 'iOS', 'Android', 'Linux'];
    const languages = ['zh-CN', 'en-US', 'ja-JP', 'ko-KR', 'de-DE', 'fr-FR'];
    const deviceTypes = ['mobile', 'desktop', 'tablet'];

    return Array.from({ length: count }, () => ({
      country: countries[Math.floor(Math.random() * countries.length)],
      region: regions[Math.floor(Math.random() * regions.length)],
      city: cities[Math.floor(Math.random() * cities.length)],
      deviceType: deviceTypes[Math.floor(Math.random() * deviceTypes.length)],
      browser: browsers[Math.floor(Math.random() * browsers.length)],
      os: osList[Math.floor(Math.random() * osList.length)],
      language: languages[Math.floor(Math.random() * languages.length)],
      isMobile: Math.random() > 0.5,
      ageGroup: ageGroups[Math.floor(Math.random() * ageGroups.length)],
      gender: genders[Math.floor(Math.random() * genders.length)],
      interests: interests.filter(() => Math.random() > 0.6).slice(0, 3),
    }));
  };

  const generateMockAnalysis = (code: DynamicCode): CodeAnalysis => {
    const totalScans = code.scanCount || Math.floor(Math.random() * 1000) + 100;
    const uniqueVisitors = Math.floor(totalScans * (0.3 + Math.random() * 0.4));
    const totalConversions = Math.floor(uniqueVisitors * (0.05 + Math.random() * 0.2));
    const conversionValue = totalConversions * (50 + Math.random() * 200);

    return {
      codeId: code.id,
      codeName: code.name,
      totalScans,
      uniqueVisitors,
      bounceRate: 20 + Math.random() * 40,
      avgTimeOnPage: 30 + Math.random() * 120,
      conversionRate: (totalConversions / uniqueVisitors) * 100,
      totalConversions,
      conversionValue,
      roi: (conversionValue - totalScans * 0.5) / (totalScans * 0.5) * 100,
    };
  };

  const getDeviceStats = () => {
    const mobile = userProfiles.filter(p => p.isMobile).length;
    const desktop = userProfiles.filter(p => !p.isMobile && p.deviceType === 'desktop').length;
    const tablet = userProfiles.filter(p => p.deviceType === 'tablet').length;
    return { mobile, desktop, tablet };
  };

  const getAgeStats = () => {
    return ageGroups.map(age => ({
      age,
      count: userProfiles.filter(p => p.ageGroup === age).length
    }));
  };

  const getGenderStats = () => {
    return genders.map(gender => ({
      gender,
      count: userProfiles.filter(p => p.gender === gender).length
    }));
  };

  const getCountryStats = () => {
    const countries = [...new Set(userProfiles.map(p => p.country))];
    return countries.map(country => ({
      country,
      count: userProfiles.filter(p => p.country === country).length
    })).sort((a, b) => b.count - a.count).slice(0, 8);
  };

  const getInterestStats = () => {
    const interestCount: { [key: string]: number } = {};
    userProfiles.forEach(p => {
      p.interests?.forEach(i => {
        interestCount[i] = (interestCount[i] || 0) + 1;
      });
    });
    return Object.entries(interestCount)
      .map(([interest, count]) => ({ interest, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  };

  const deviceStats = getDeviceStats();
  const ageStats = getAgeStats();
  const genderStats = getGenderStats();
  const countryStats = getCountryStats();
  const interestStats = getInterestStats();

  const deviceChartData = {
    labels: ['移动端', '桌面端', '平板'],
    datasets: [{
      data: [deviceStats.mobile, deviceStats.desktop, deviceStats.tablet],
      backgroundColor: ['#3b82f6', '#8b5cf6', '#06b6d4'],
      borderWidth: 0,
    }]
  };

  const ageChartData = {
    labels: ageStats.map(a => a.age),
    datasets: [{
      label: '用户数',
      data: ageStats.map(a => a.count),
      backgroundColor: 'rgba(59, 130, 246, 0.5)',
      borderColor: '#3b82f6',
      borderWidth: 2,
      borderRadius: 8,
    }]
  };

  const genderChartData = {
    labels: genderStats.map(g => g.gender),
    datasets: [{
      data: genderStats.map(g => g.count),
      backgroundColor: ['#60a5fa', '#f472b6', '#94a3b8'],
      borderWidth: 0,
    }]
  };

  const interestChartData = {
    labels: interestStats.map(i => i.interest),
    datasets: [{
      label: '感兴趣人数',
      data: interestStats.map(i => i.count),
      backgroundColor: 'rgba(6, 182, 212, 0.5)',
      borderColor: '#06b6d4',
      borderWidth: 2,
      borderRadius: 8,
    }]
  };

  const funnelStages = [
    { name: '扫码访问', count: analysis?.totalScans || 0, rate: 100 },
    { name: '页面浏览', count: Math.floor((analysis?.totalScans || 0) * 0.85), rate: 85 },
    { name: '深度浏览', count: Math.floor((analysis?.totalScans || 0) * 0.6), rate: 60 },
    { name: '目标转化', count: analysis?.totalConversions || 0, rate: analysis?.conversionRate || 0 },
  ];

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
        ticks: {
          color: '#94a3b8',
        },
      },
      x: {
        grid: {
          display: false,
        },
        ticks: {
          color: '#94a3b8',
        },
      },
    },
  };

  const doughnutOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          color: '#94a3b8',
          padding: 20,
          usePointStyle: true,
        },
      },
    },
  };

  if (!isAuthenticated()) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <BarChart3 className="mx-auto h-16 w-16 text-slate-600 mb-4" />
          <h2 className="text-2xl font-bold text-slate-300 mb-2">请先登录</h2>
          <p className="text-slate-500">登录后即可查看落地页分析数据</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent mb-2">
                落地页分析
              </h1>
              <p className="text-slate-400">深度分析扫码用户画像和转化漏斗</p>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={selectedCode || ''}
                onChange={(e) => setSelectedCode(e.target.value)}
                className="px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-200 focus:outline-none focus:border-blue-500"
              >
                <option value="">选择二维码</option>
                {codes.map(code => (
                  <option key={code.id} value={code.id}>{code.name}</option>
                ))}
              </select>
              <div className="flex gap-1 bg-slate-800/50 rounded-xl p-1">
                {(['7', '30', '90'] as const).map(range => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      timeRange === range
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {range}天
                  </button>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : analysis ? (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {[
                { label: '总扫码量', value: analysis.totalScans.toLocaleString(), icon: Eye, color: 'blue' },
                { label: '独立访客', value: analysis.uniqueVisitors.toLocaleString(), icon: Users, color: 'purple' },
                { label: '转化率', value: `${analysis.conversionRate.toFixed(1)}%`, icon: Target, color: 'green' },
                { label: 'ROI', value: `${analysis.roi.toFixed(0)}%`, icon: TrendingUp, color: 'cyan' },
              ].map((stat, index) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-5"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      stat.color === 'blue' ? 'bg-blue-500/20' :
                      stat.color === 'purple' ? 'bg-purple-500/20' :
                      stat.color === 'green' ? 'bg-green-500/20' :
                      'bg-cyan-500/20'
                    }`}>
                      <stat.icon size={20} className={
                        stat.color === 'blue' ? 'text-blue-400' :
                        stat.color === 'purple' ? 'text-purple-400' :
                        stat.color === 'green' ? 'text-green-400' :
                        'text-cyan-400'
                      } />
                    </div>
                    <span className="text-slate-400 text-sm">{stat.label}</span>
                  </div>
                  <p className="text-2xl font-bold text-white">{stat.value}</p>
                </motion.div>
              ))}
            </div>

            <div className="grid lg:grid-cols-2 gap-6 mb-8">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
              >
                <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <Activity size={20} className="text-cyan-400" />
                  转化漏斗
                </h3>
                <div className="space-y-3">
                  {funnelStages.map((stage, index) => (
                    <div key={stage.name} className="relative">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-slate-300">{stage.name}</span>
                        <span className="text-sm text-slate-400">{stage.count.toLocaleString()} ({stage.rate.toFixed(0)}%)</span>
                      </div>
                      <div className="h-8 bg-slate-800 rounded-xl overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${stage.rate}%` }}
                          transition={{ delay: 0.3 + index * 0.1, duration: 0.8 }}
                          className="h-full rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500"
                        />
                      </div>
                      {index < funnelStages.length - 1 && (
                        <div className="flex justify-center my-1">
                          <ArrowRight size={16} className="text-slate-600" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
              >
                <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <Smartphone size={20} className="text-purple-400" />
                  设备分布
                </h3>
                <div className="h-64">
                  <Doughnut data={deviceChartData} options={doughnutOptions} />
                </div>
              </motion.div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 mb-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
              >
                <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <Users size={20} className="text-blue-400" />
                  年龄分布
                </h3>
                <div className="h-64">
                  <Bar data={ageChartData} options={chartOptions} />
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
              >
                <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <PieChart size={20} className="text-pink-400" />
                  性别分布
                </h3>
                <div className="h-64">
                  <Pie data={genderChartData} options={doughnutOptions} />
                </div>
              </motion.div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 mb-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
              >
                <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <MapPin size={20} className="text-green-400" />
                  地域分布 (Top 8)
                </h3>
                <div className="space-y-2">
                  {countryStats.map((item, index) => (
                    <motion.div
                      key={item.country}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.7 + index * 0.05 }}
                      className="flex items-center gap-3"
                    >
                      <span className="w-6 text-right text-slate-500 text-sm">{index + 1}</span>
                      <span className="flex-1 text-slate-300">{item.country}</span>
                      <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${(item.count / userProfiles.length) * 100}%` }}
                          transition={{ delay: 0.8 + index * 0.05, duration: 0.5 }}
                          className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full"
                        />
                      </div>
                      <span className="w-16 text-right text-slate-400 text-sm">{item.count}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
                className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
              >
                <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <Globe size={20} className="text-orange-400" />
                  兴趣标签
                </h3>
                <div className="h-64">
                  <Bar data={interestChartData} options={{ ...chartOptions, indexAxis: 'y' as const }} />
                </div>
              </motion.div>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
            >
              <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <Clock size={20} className="text-blue-400" />
                性能指标
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: '平均页面加载时间', value: `${(1.5 + Math.random() * 2).toFixed(1)}s` },
                  { label: '跳出率', value: `${analysis.bounceRate.toFixed(1)}%` },
                  { label: '平均会话时长', value: `${Math.floor(analysis.avgTimeOnPage / 60)}分${Math.floor(analysis.avgTimeOnPage % 60)}秒` },
                  { label: '每会话浏览页数', value: `${(1.5 + Math.random() * 3).toFixed(1)}` },
                ].map((item, index) => (
                  <div key={item.label} className="text-center p-4 rounded-xl bg-slate-800/30">
                    <p className="text-2xl font-bold text-white mb-1">{item.value}</p>
                    <p className="text-sm text-slate-400">{item.label}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          </>
        ) : (
          <div className="text-center py-20">
            <BarChart3 className="mx-auto h-16 w-16 text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold text-slate-300 mb-2">暂无分析数据</h3>
            <p className="text-slate-500">请先创建动态二维码并获取扫码数据</p>
          </div>
        )}
      </div>
    </div>
  );
}
