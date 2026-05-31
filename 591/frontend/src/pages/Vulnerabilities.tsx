import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, ShieldAlert, AlertTriangle, Info, ChevronDown } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { api } from '@/utils/api';
import { cn } from '@/lib/utils';
import { severityColor, severityBg } from '@/utils/helpers';
import type { SeverityLevel, Vulnerability } from '@/types';

interface VulnStats {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

function SeverityBadge({ severity }: { severity: SeverityLevel }) {
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', severityBg(severity), severityColor(severity))}>
      {severity}
    </span>
  );
}

function CvssCircle({ score }: { score: number }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 10) * circumference;
  const color = score >= 9 ? '#FF4757' : score >= 7 ? '#FF6B35' : score >= 4 ? '#FFA502' : '#54A0FF';

  return (
    <div className="relative flex items-center justify-center">
      <svg width="100" height="100" className="-rotate-90">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#1A3A5C" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className="text-2xl font-bold" style={{ color }}>{score.toFixed(1)}</span>
        <span className="text-xs text-dep-muted">CVSS</span>
      </div>
    </div>
  );
}

const statItems: { key: keyof VulnStats; label: string; color: string; icon: React.ReactNode }[] = [
  { key: 'critical', label: 'CRITICAL', color: '#FF4757', icon: <ShieldAlert size={16} /> },
  { key: 'high', label: 'HIGH', color: '#FF6B35', icon: <AlertTriangle size={16} /> },
  { key: 'medium', label: 'MEDIUM', color: '#FFA502', icon: <Info size={16} /> },
  { key: 'low', label: 'LOW', color: '#54A0FF', icon: <Info size={16} /> },
];

export default function Vulnerabilities() {
  const navigate = useNavigate();
  const { vulnerabilities, repositories, fetchVulnerabilities, fetchRepositories, loading } = useAppStore();
  const [stats, setStats] = useState<VulnStats>({ critical: 0, high: 0, medium: 0, low: 0 });
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [serviceFilter, setServiceFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedVuln, setSelectedVuln] = useState<Vulnerability | null>(null);

  useEffect(() => {
    fetchVulnerabilities();
    fetchRepositories();
    api.vulnerabilities.getStats().then(setStats).catch(() => {
      setStats({ critical: 1, high: 2, medium: 1, low: 1 });
    });
  }, [fetchVulnerabilities, fetchRepositories]);

  const serviceNames = useMemo(() => [...new Set(repositories.map((r) => r.name))], [repositories]);

  const filtered = useMemo(() => {
    return vulnerabilities.filter((v) => {
      if (severityFilter !== 'ALL' && v.severity !== severityFilter) return false;
      if (serviceFilter !== 'ALL' && !v.affectedServices.some((s) => s.repoName === serviceFilter)) return false;
      if (searchQuery && !v.cveId.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });
  }, [vulnerabilities, severityFilter, serviceFilter, searchQuery]);

  function cvssColor(score: number): string {
    if (score >= 9) return 'text-dep-critical';
    if (score >= 7) return 'text-dep-high';
    if (score >= 4) return 'text-dep-medium';
    return 'text-dep-low';
  }

  return (
    <div className="min-h-screen bg-dep-bg p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-dep-text">漏洞报告</h1>
        <p className="text-sm text-dep-muted mt-1">检测到的安全漏洞及CVE详情</p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        {statItems.map((item) => (
          <div key={item.key} className="bg-dep-card border border-dep-border rounded-lg p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${item.color}20` }}>
              <span style={{ color: item.color }}>{item.icon}</span>
            </div>
            <div>
              <div className="text-2xl font-bold" style={{ color: item.color }}>{stats[item.key]}</div>
              <div className="text-xs text-dep-muted">{item.label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-4 mb-6">
        <div className="relative">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="appearance-none bg-dep-card border border-dep-border rounded-lg px-4 py-2 pr-8 text-sm text-dep-text focus:outline-none focus:border-dep-accent cursor-pointer"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
          <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-dep-muted pointer-events-none" />
        </div>

        <div className="relative">
          <select
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
            className="appearance-none bg-dep-card border border-dep-border rounded-lg px-4 py-2 pr-8 text-sm text-dep-text focus:outline-none focus:border-dep-accent cursor-pointer"
          >
            <option value="ALL">All Services</option>
            {serviceNames.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-dep-muted pointer-events-none" />
        </div>

        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dep-muted" />
          <input
            type="text"
            placeholder="搜索CVE编号..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-dep-card border border-dep-border rounded-lg pl-9 pr-4 py-2 text-sm text-dep-text placeholder:text-dep-muted focus:outline-none focus:border-dep-accent"
          />
        </div>
      </div>

      <div className="bg-dep-card border border-dep-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-dep-border">
              <th className="text-left text-xs font-medium text-dep-muted px-4 py-3 uppercase tracking-wider">CVE编号</th>
              <th className="text-left text-xs font-medium text-dep-muted px-4 py-3 uppercase tracking-wider">严重性</th>
              <th className="text-left text-xs font-medium text-dep-muted px-4 py-3 uppercase tracking-wider">CVSS评分</th>
              <th className="text-left text-xs font-medium text-dep-muted px-4 py-3 uppercase tracking-wider">依赖</th>
              <th className="text-left text-xs font-medium text-dep-muted px-4 py-3 uppercase tracking-wider">受影响版本</th>
              <th className="text-left text-xs font-medium text-dep-muted px-4 py-3 uppercase tracking-wider">修复版本</th>
              <th className="text-left text-xs font-medium text-dep-muted px-4 py-3 uppercase tracking-wider">受影响服务</th>
            </tr>
          </thead>
          <tbody>
            {loading.vulns ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-dep-muted">加载中...</td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-dep-muted">暂无漏洞数据</td>
              </tr>
            ) : (
              filtered.map((v) => (
                <tr
                  key={v.cveId}
                  onClick={() => { setSelectedVuln(v); navigate(`/vulnerabilities/${v.cveId}`); }}
                  className="border-b border-dep-border/50 cursor-pointer transition-colors hover:bg-dep-hover"
                >
                  <td className="px-4 py-3 font-mono text-sm text-dep-accent">{v.cveId}</td>
                  <td className="px-4 py-3"><SeverityBadge severity={v.severity} /></td>
                  <td className="px-4 py-3">
                    <span className={cn('font-bold font-mono text-sm', cvssColor(v.cvssScore))}>
                      {v.cvssScore.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-dep-text">{v.affectedServices[0]?.dependency ?? '-'}</td>
                  <td className="px-4 py-3 font-mono text-sm text-dep-text">{v.affectedVersions}</td>
                  <td className="px-4 py-3 font-mono text-sm text-dep-safe">{v.fixedVersion}</td>
                  <td className="px-4 py-3 text-sm text-dep-text">{v.affectedServices.length}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selectedVuln && (
        <>
          <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setSelectedVuln(null)} />
          <div className="fixed right-0 top-0 h-full w-[480px] bg-dep-secondary border-l border-dep-border z-50 animate-slide-in overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-dep-text">漏洞详情</h2>
                <button onClick={() => setSelectedVuln(null)} className="p-1 rounded hover:bg-dep-hover text-dep-muted hover:text-dep-text transition-colors">
                  <X size={20} />
                </button>
              </div>

              <div className="flex items-center gap-3 mb-6">
                <span className="font-mono text-xl font-bold text-dep-accent">{selectedVuln.cveId}</span>
                <SeverityBadge severity={selectedVuln.severity} />
              </div>

              <div className="flex justify-center mb-6">
                <CvssCircle score={selectedVuln.cvssScore} />
              </div>

              <div className="space-y-4 mb-6">
                <div>
                  <h3 className="text-xs font-medium text-dep-muted uppercase tracking-wider mb-1">描述</h3>
                  <p className="text-sm text-dep-text leading-relaxed">{selectedVuln.description}</p>
                </div>
                <div>
                  <h3 className="text-xs font-medium text-dep-muted uppercase tracking-wider mb-1">影响版本范围</h3>
                  <span className="font-mono text-sm text-dep-text">{selectedVuln.affectedVersions}</span>
                </div>
                <div>
                  <h3 className="text-xs font-medium text-dep-muted uppercase tracking-wider mb-1">修复版本</h3>
                  <span className="font-mono text-sm text-dep-safe">{selectedVuln.fixedVersion}</span>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-medium text-dep-muted uppercase tracking-wider mb-3">受影响服务</h3>
                <div className="space-y-2">
                  {selectedVuln.affectedServices.map((s, i) => (
                    <div key={i} className="bg-dep-card border border-dep-border rounded-lg px-4 py-3 flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-dep-text">{s.repoName}</div>
                        <div className="font-mono text-xs text-dep-muted">{s.dependency}</div>
                      </div>
                      <span className="font-mono text-xs text-dep-high">{s.version}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
