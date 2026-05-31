import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Download, 
  Loader2, 
  AlertTriangle, 
  Key, 
  Settings,
  RefreshCw,
  CheckCircle,
  XCircle
} from 'lucide-react';
import axios from 'axios';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

export default function JobDetail() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('vulnerabilities');

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [jobId]);

  const fetchData = async () => {
    try {
      const statusRes = await axios.get(`/api/scan/${jobId}`);
      setJob(statusRes.data);

      if (statusRes.data.status === 'completed') {
        const resultsRes = await axios.get(`/api/scan/${jobId}/results`);
        setResults(resultsRes.data);
      }
    } catch (error) {
      console.error('Failed to fetch job details:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async (type) => {
    try {
      const response = await axios.post(`/api/scan/${jobId}/reports?report_type=${type}`);
      window.open(`/api/reports/${response.data.filename}`, '_blank');
    } catch (error) {
      console.error('Failed to generate report:', error);
    }
  };

  const getSeverityColor = (severity) => {
    const colors = {
      CRITICAL: '#dc2626',
      HIGH: '#f97316',
      MEDIUM: '#eab308',
      LOW: '#22c55e'
    };
    return colors[severity] || '#6b7280';
  };

  const getSeverityClass = (severity) => {
    const classes = {
      CRITICAL: 'severity-critical',
      HIGH: 'severity-high',
      MEDIUM: 'severity-medium',
      LOW: 'severity-low'
    };
    return classes[severity] || 'bg-gray-100 text-gray-800';
  };

  const getRiskClass = (score) => {
    if (score >= 70) return 'risk-critical';
    if (score >= 50) return 'risk-high';
    if (score >= 30) return 'risk-medium';
    if (score > 0) return 'risk-low';
    return 'risk-safe';
  };

  const getRiskText = (score) => {
    if (score >= 70) return '严重';
    if (score >= 50) return '高';
    if (score >= 30) return '中';
    if (score > 0) return '低';
    return '安全';
  };

  const getSeverityChartData = (bySeverity) => {
    return [
      { name: 'Critical', value: bySeverity.CRITICAL || 0, color: '#dc2626' },
      { name: 'High', value: bySeverity.HIGH || 0, color: '#f97316' },
      { name: 'Medium', value: bySeverity.MEDIUM || 0, color: '#eab308' },
      { name: 'Low', value: bySeverity.LOW || 0, color: '#22c55e' }
    ].filter(d => d.value > 0);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">任务不存在</p>
        <Link to="/jobs" className="mt-4 inline-flex items-center text-indigo-600 hover:text-indigo-900">
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回任务列表
        </Link>
      </div>
    );
  }

  const isCompleted = job.status === 'completed';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link to="/jobs" className="mr-4 text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">任务详情</h1>
            <p className="text-sm text-gray-500">{jobId}</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={fetchData}
            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </button>
          {isCompleted && (
            <>
              <button
                onClick={() => generateReport('json')}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <Download className="mr-2 h-4 w-4" />
                JSON报告
              </button>
              <button
                onClick={() => generateReport('html')}
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
              >
                <Download className="mr-2 h-4 w-4" />
                HTML报告
              </button>
            </>
          )}
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm font-medium text-gray-500">状态</p>
            <p className="mt-1 text-lg font-semibold">
              {job.status === 'completed' && <span className="text-green-600"><CheckCircle className="inline h-5 w-5 mr-1" />已完成</span>}
              {job.status === 'running' && <span className="text-blue-600"><Loader2 className="inline h-5 w-5 mr-1 animate-spin" />运行中</span>}
              {job.status === 'pending' && <span className="text-yellow-600">等待中</span>}
              {job.status === 'failed' && <span className="text-red-600"><XCircle className="inline h-5 w-5 mr-1" />失败</span>}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">镜像数量</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">{job.image_names.length} 个</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">进度</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {job.progress?.completed_images || 0} / {job.progress?.total_images || 0}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">创建时间</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {new Date(job.created_at).toLocaleString()}
            </p>
          </div>
        </div>

        {job.status === 'running' && (
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${job.progress?.percentage || 0}%` }}
              />
            </div>
            <p className="mt-1 text-sm text-gray-500 text-right">{job.progress?.percentage || 0}%</p>
          </div>
        )}
      </div>

      {isCompleted && results && (
        <div className="space-y-6">
          {Object.entries(results.results).map(([imageName, imageResult]) => (
            <div key={imageName} className="bg-white shadow rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">📦 {imageName}</h3>
                  <div className="flex items-center">
                    <span className="text-sm text-gray-500 mr-2">风险分数:</span>
                    <span className={`text-2xl font-bold ${getRiskClass(imageResult.overall_risk_score || 0)}`}>
                      {imageResult.overall_risk_score || 0}
                    </span>
                    <span className={`ml-2 px-2 py-1 rounded text-sm font-medium ${getRiskClass(imageResult.overall_risk_score || 0)}`}>
                      {getRiskText(imageResult.overall_risk_score || 0)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="border-b border-gray-200">
                <nav className="flex -mb-px">
                  {[
                    { id: 'vulnerabilities', label: '漏洞', icon: AlertTriangle },
                    { id: 'secrets', label: '敏感信息', icon: Key },
                    { id: 'rules', label: '规则检查', icon: Settings }
                  ].map((tab) => {
                    const Icon = tab.icon;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`mr-8 py-4 px-1 border-b-2 font-medium text-sm flex items-center ${
                          activeTab === tab.id
                            ? 'border-indigo-500 text-indigo-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <Icon className="mr-2 h-4 w-4" />
                        {tab.label}
                      </button>
                    );
                  })}
                </nav>
              </div>

              <div className="p-6">
                {activeTab === 'vulnerabilities' && imageResult.vulnerabilities && (
                  <div>
                    <div className="flex items-start space-x-6 mb-6">
                      <div className="w-48 h-48">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={getSeverityChartData(imageResult.vulnerabilities.summary?.by_severity || {})}
                              dataKey="value"
                              nameKey="name"
                              cx="50%"
                              cy="50%"
                              outerRadius={60}
                              label={({ name, value }) => `${name}: ${value}`}
                            >
                              {getSeverityChartData(imageResult.vulnerabilities.summary?.by_severity || {}).map((entry, index) => (
                                <Cell key={index} fill={entry.color} />
                              ))}
                            </Pie>
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex-1">
                        <h4 className="text-lg font-medium mb-2">漏洞统计</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
                            <div key={sev} className={`p-3 rounded-lg border ${getSeverityClass(sev)}`}>
                              <p className="text-sm">{sev}</p>
                              <p className="text-2xl font-bold">
                                {imageResult.vulnerabilities.summary?.by_severity?.[sev] || 0}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {imageResult.vulnerabilities.vulnerabilities?.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">CVE ID</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">严重程度</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">标题</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">软件包</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">修复版本</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {imageResult.vulnerabilities.vulnerabilities.slice(0, 20).map((vuln, idx) => (
                              <tr key={idx}>
                                <td className="px-4 py-3 text-sm font-mono text-indigo-600">{vuln.id}</td>
                                <td className="px-4 py-3">
                                  <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityClass(vuln.severity)}`}>
                                    {vuln.severity}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-900">{vuln.title}</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">{vuln.package}</td>
                                <td className="px-4 py-3 text-sm text-gray-500">{vuln.fixed_version || '-'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {imageResult.vulnerabilities.vulnerabilities.length > 20 && (
                          <p className="mt-2 text-sm text-gray-500 text-center">
                            ... 还有 {imageResult.vulnerabilities.vulnerabilities.length - 20} 个漏洞
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <CheckCircle className="mx-auto h-12 w-12 text-green-400 mb-2" />
                        未发现漏洞
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'secrets' && imageResult.secrets && (
                  <div>
                    {imageResult.secrets.findings?.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">文件路径</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">严重程度</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">行号</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {imageResult.secrets.findings.map((secret, idx) => (
                              <tr key={idx}>
                                <td className="px-4 py-3 text-sm font-mono text-gray-900">{secret.file_path}</td>
                                <td className="px-4 py-3 text-sm text-gray-500">{secret.pattern_name}</td>
                                <td className="px-4 py-3">
                                  <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityClass(secret.severity)}`}>
                                    {secret.severity}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-500">{secret.line_number}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <CheckCircle className="mx-auto h-12 w-12 text-green-400 mb-2" />
                        未发现敏感信息
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'rules' && imageResult.rules && (
                  <div>
                    <div className="mb-4 flex items-center justify-between">
                      <span className="text-sm text-gray-500">
                        通过: {imageResult.rules.summary?.passed || 0} / {imageResult.rules.summary?.total_rules || 0}
                      </span>
                      <span className="text-sm text-gray-500">
                        规则风险分数: {imageResult.rules.summary?.risk_score || 0}
                      </span>
                    </div>
                    
                    {imageResult.rules.results?.length > 0 ? (
                      <div className="space-y-3">
                        {imageResult.rules.results.map((rule, idx) => (
                          <div 
                            key={idx} 
                            className={`p-4 rounded-lg border ${
                              rule.passed 
                                ? 'bg-green-50 border-green-200' 
                                : 'bg-red-50 border-red-200'
                            }`}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex items-center">
                                {rule.passed ? (
                                  <CheckCircle className="h-5 w-5 text-green-500 mr-2 mt-0.5" />
                                ) : (
                                  <XCircle className="h-5 w-5 text-red-500 mr-2 mt-0.5" />
                                )}
                                <div>
                                  <p className="font-medium">
                                    <span className="text-gray-400 mr-2">[{rule.rule_id}]</span>
                                    {rule.rule_name}
                                  </p>
                                  <p className="text-sm text-gray-500">{rule.description}</p>
                                </div>
                              </div>
                              <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityClass(rule.severity)}`}>
                                {rule.severity}
                              </span>
                            </div>
                            {!rule.passed && rule.remediation && (
                              <p className="mt-2 text-sm text-red-700 ml-7">
                                <strong>修复建议:</strong> {rule.remediation}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        无规则检查结果
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
