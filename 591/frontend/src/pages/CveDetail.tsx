import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink, Calendar, Bug, CheckCircle } from 'lucide-react';
import { api } from '@/utils/api';
import { Card, SeverityBadge, HealthScore } from '@/components/ui';
import { cn, timeAgo } from '@/utils/helpers';
import type { Vulnerability } from '@/types';
import { mockVulnerabilities } from '@/utils/mockData';

export default function CveDetail() {
  const { cveId } = useParams<{ cveId: string }>();
  const [vuln, setVuln] = useState<Vulnerability | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      if (!cveId) return;
      setLoading(true);
      try {
        const data = await api.vulnerabilities.get(cveId);
        setVuln(data);
      } catch (e) {
        const mock = mockVulnerabilities.find((v) => v.cveId === cveId) || null;
        setVuln(mock);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [cveId]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-dep-accent border-t-transparent" />
      </div>
    );
  }

  if (!vuln) {
    return (
      <div className="p-6">
        <p className="text-dep-muted">CVE信息不存在</p>
        <Link to="/vulnerabilities" className="mt-4 inline-flex items-center gap-2 text-sm text-dep-accent hover:underline">
          <ArrowLeft className="h-4 w-4" />
          返回漏洞报告
        </Link>
      </div>
    );
  }

  const cvssColor = vuln.cvssScore >= 9
    ? 'text-dep-critical'
    : vuln.cvssScore >= 7
    ? 'text-dep-high'
    : vuln.cvssScore >= 4
    ? 'text-dep-medium'
    : 'text-dep-low';

  return (
    <div className="min-h-screen bg-dep-bg p-6 font-sans">
      <Link to="/vulnerabilities" className="mb-4 inline-flex items-center gap-2 text-sm text-dep-muted hover:text-dep-text">
        <ArrowLeft className="h-4 w-4" />
        返回漏洞报告
      </Link>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-3xl font-bold text-dep-text">{vuln.cveId}</h1>
            <SeverityBadge severity={vuln.severity} />
          </div>
          <div className="mt-2 flex items-center gap-4 text-sm text-dep-muted">
            <span className="inline-flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              发布于 {timeAgo(vuln.publishedDate)}
            </span>
            <a
              href={`https://nvd.nist.gov/vuln/detail/${vuln.cveId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-dep-accent hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              NVD详情
            </a>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <HealthScore score={vuln.cvssScore * 10} size={100} strokeWidth={10} />
          <div className="text-right">
            <p className="text-xs text-dep-muted">CVSS评分</p>
            <p className={cn('font-mono text-3xl font-bold', cvssColor)}>{vuln.cvssScore.toFixed(1)}</p>
            <p className="text-xs text-dep-muted">/ 10.0</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-dep-muted">漏洞描述</h2>
          <p className="text-sm leading-relaxed text-dep-text">{vuln.description}</p>
        </Card>

        <div className="space-y-4">
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-dep-muted">影响版本</h2>
            <div className="flex items-center gap-2">
              <Bug className="h-4 w-4 text-dep-critical" />
              <span className="font-mono text-sm text-dep-text">{vuln.affectedVersions}</span>
            </div>
          </Card>
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-dep-muted">修复版本</h2>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-dep-safe" />
              <span className="font-mono text-sm text-dep-safe">{vuln.fixedVersion}</span>
            </div>
          </Card>
        </div>
      </div>

      <Card className="mt-6">
        <h2 className="mb-4 text-sm font-semibold text-dep-muted">受影响的服务 ({vuln.affectedServices.length})</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-dep-border">
                <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">服务名称</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">依赖</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">当前版本</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-dep-muted">操作</th>
              </tr>
            </thead>
            <tbody>
              {vuln.affectedServices.map((svc, i) => (
                <tr key={i} className="border-b border-dep-border/50 transition-colors hover:bg-dep-hover">
                  <td className="px-4 py-3 text-sm font-medium text-dep-text">{svc.repoName}</td>
                  <td className="px-4 py-3 text-xs font-mono text-dep-muted">{svc.dependency}</td>
                  <td className="px-4 py-3 text-xs font-mono text-dep-critical">{svc.version}</td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/services/${svc.repoId}`}
                      className="text-xs text-dep-accent hover:underline"
                    >
                      查看详情
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
