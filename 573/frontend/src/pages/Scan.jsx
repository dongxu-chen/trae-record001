import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import axios from 'axios';

export default function Scan() {
  const navigate = useNavigate();
  const [images, setImages] = useState('');
  const [scanTypes, setScanTypes] = useState({
    vulnerabilities: true,
    secrets: true,
    rules: true
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    const imageList = images.split('\n').map(img => img.trim()).filter(img => img);
    
    if (imageList.length === 0) {
      setError('请至少输入一个镜像名称');
      setLoading(false);
      return;
    }

    const selectedScanTypes = Object.entries(scanTypes)
      .filter(([, selected]) => selected)
      .map(([type]) => type);

    if (selectedScanTypes.length === 0) {
      setError('请至少选择一种扫描类型');
      setLoading(false);
      return;
    }

    try {
      const response = await axios.post('/api/scan', {
        images: imageList,
        scan_types: selectedScanTypes,
        generate_reports: true
      });

      setSuccess(`扫描任务已创建: ${response.data.job_id}`);
      setTimeout(() => {
        navigate(`/jobs/${response.data.job_id}`);
      }, 1500);
    } catch (err) {
      setError(err.response?.data?.detail || '创建扫描任务失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">新建扫描</h1>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-4 flex items-start">
          <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 mr-2" />
          <span className="text-red-700">{error}</span>
        </div>
      )}

      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-md p-4 flex items-start">
          <CheckCircle2 className="h-5 w-5 text-green-400 mt-0.5 mr-2" />
          <span className="text-green-700">{success}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white shadow rounded-lg p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Docker 镜像名称
          </label>
          <p className="text-sm text-gray-500 mb-2">
            每行输入一个镜像名称，例如：nginx:latest, alpine:3.18
          </p>
          <textarea
            className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="nginx:latest&#10;alpine:3.18&#10;myapp:v1.0.0"
            value={images}
            onChange={(e) => setImages(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <label className="block text-sm font-medium text-gray-700 mb-4">
            扫描类型
          </label>
          <div className="space-y-3">
            <label className="flex items-center">
              <input
                type="checkbox"
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                checked={scanTypes.vulnerabilities}
                onChange={(e) => setScanTypes({ ...scanTypes, vulnerabilities: e.target.checked })}
                disabled={loading}
              />
              <span className="ml-2">
                <span className="font-medium text-gray-900">漏洞扫描 (CVE)</span>
                <span className="text-gray-500 text-sm ml-2">扫描已知的安全漏洞</span>
              </span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                checked={scanTypes.secrets}
                onChange={(e) => setScanTypes({ ...scanTypes, secrets: e.target.checked })}
                disabled={loading}
              />
              <span className="ml-2">
                <span className="font-medium text-gray-900">敏感信息检测</span>
                <span className="text-gray-500 text-sm ml-2">检测密码、密钥、令牌等</span>
              </span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                checked={scanTypes.rules}
                onChange={(e) => setScanTypes({ ...scanTypes, rules: e.target.checked })}
                disabled={loading}
              />
              <span className="ml-2">
                <span className="font-medium text-gray-900">配置规则检查</span>
                <span className="text-gray-500 text-sm ml-2">检查Docker配置安全最佳实践</span>
              </span>
            </label>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center px-6 py-3 border border-transparent shadow-sm text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin mr-2 h-5 w-5" />
                创建中...
              </>
            ) : (
              <>
                <Play className="mr-2 h-5 w-5" />
                开始扫描
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
