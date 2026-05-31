import React, { useState, useEffect } from 'react';
import { FileText, Download, Trash2, RefreshCw } from 'lucide-react';
import axios from 'axios';

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const response = await axios.get('/api/reports');
      setReports(response.data);
    } catch (error) {
      console.error('Failed to fetch reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteReport = async (filename) => {
    if (!confirm(`确定要删除报告 ${filename} 吗?`)) return;
    
    try {
      await axios.delete(`/api/reports/${filename}`);
      fetchReports();
    } catch (error) {
      console.error('Failed to delete report:', error);
    }
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold text-gray-900">报告</h1>
        <button
          onClick={fetchReports}
          className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </button>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        {reports.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-500">暂无报告</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {reports.map((report) => (
              <li key={report.filename}>
                <div className="px-4 py-4 sm:px-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <FileText className="h-6 w-6 text-gray-400" />
                      <div className="ml-3">
                        <p className="text-sm font-medium text-indigo-600">
                          {report.filename}
                        </p>
                        <p className="text-sm text-gray-500">
                          {report.type} · {formatSize(report.size)} · 创建于 {new Date(report.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <a
                        href={`/api/reports/${report.filename}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 text-gray-400 hover:text-gray-500"
                        title="下载"
                      >
                        <Download className="h-5 w-5" />
                      </a>
                      <button
                        onClick={() => deleteReport(report.filename)}
                        className="p-2 text-gray-400 hover:text-red-500"
                        title="删除"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
