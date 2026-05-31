import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, Settings, Zap } from 'lucide-react';
import axios from 'axios';

export default function Rules() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const response = await axios.get('/api/rules');
      setRules(response.data);
    } catch (error) {
      console.error('Failed to fetch rules:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    const colors = {
      critical: 'bg-red-100 text-red-800 border-red-200',
      high: 'bg-orange-100 text-orange-800 border-orange-200',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      low: 'bg-green-100 text-green-800 border-green-200'
    };
    return colors[severity] || 'bg-gray-100 text-gray-800';
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'configuration':
        return <Settings className="h-5 w-5" />;
      case 'runtime':
        return <Zap className="h-5 w-5" />;
      case 'optimization':
        return <AlertTriangle className="h-5 w-5" />;
      default:
        return <Shield className="h-5 w-5" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  const categories = [...new Set(rules.map(r => r.category))];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">规则配置</h1>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <Shield className="h-5 w-5 text-blue-400 mt-0.5" />
          <p className="ml-3 text-sm text-blue-700">
            共 {rules.length} 条安全检查规则，涵盖容器安全最佳实践、配置风险检测和优化建议。
          </p>
        </div>
      </div>

      {categories.map((category) => (
        <div key={category} className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <h2 className="text-lg font-medium text-gray-900 flex items-center">
              {getCategoryIcon(category)}
              <span className="ml-2 capitalize">{category}</span>
              <span className="ml-2 text-sm text-gray-500">
                ({rules.filter(r => r.category === category).length} 条规则)
              </span>
            </h2>
          </div>
          <div className="divide-y divide-gray-200">
            {rules
              .filter(r => r.category === category)
              .map((rule) => (
                <div key={rule.id} className="px-6 py-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center">
                        <span className="text-sm font-mono text-gray-400 mr-3">[{rule.id}]</span>
                        <h3 className="text-sm font-medium text-gray-900">{rule.name}</h3>
                      </div>
                      <p className="mt-1 text-sm text-gray-500">{rule.description}</p>
                    </div>
                    <span className={`ml-4 px-2.5 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(rule.severity)}`}>
                      {rule.severity.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
