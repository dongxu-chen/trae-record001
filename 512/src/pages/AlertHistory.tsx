import { useState, useEffect, useCallback, useRef } from 'react';
import { Clock } from 'lucide-react';
import { useAlertStore } from '@/stores/alert-store';
import type { AlertHistoryQuery, AlertRecord } from '@/types';
import AlertFilterBar from '@/components/AlertFilterBar';
import VirtualAlertTable from '@/components/VirtualAlertTable';
import AlertDetailModal from '@/components/AlertDetailModal';

const DEFAULT_QUERY: AlertHistoryQuery = {
  page: 1,
  pageSize: 100,
};

function SkeletonRows() {
  return (
    <div className="rounded-xl border border-brand-border bg-brand-surface overflow-hidden">
      <div className="p-4 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4">
            <div className="h-4 w-20 rounded bg-brand-card animate-pulse" />
            <div className="h-4 w-16 rounded bg-brand-card animate-pulse" />
            <div className="h-4 w-12 rounded bg-brand-card animate-pulse" />
            <div className="h-4 w-14 rounded bg-brand-card animate-pulse" />
            <div className="h-4 w-14 rounded bg-brand-card animate-pulse" />
            <div className="h-4 w-24 rounded bg-brand-card animate-pulse" />
            <div className="h-4 w-12 rounded bg-brand-card animate-pulse" />
            <div className="h-4 w-16 rounded bg-brand-card animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AlertHistory() {
  const alerts = useAlertStore((s) => s.alerts);
  const alertsTotal = useAlertStore((s) => s.alertsTotal);
  const alertsPage = useAlertStore((s) => s.alertsPage);
  const alertsPageSize = useAlertStore((s) => s.alertsPageSize);
  const fetchAlerts = useAlertStore((s) => s.fetchAlerts);
  const acknowledgeAlert = useAlertStore((s) => s.acknowledgeAlert);

  const [query, setQuery] = useState<AlertHistoryQuery>(DEFAULT_QUERY);
  const [loading, setLoading] = useState(true);
  const [detailAlert, setDetailAlert] = useState<AlertRecord | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const viewDetailHandlerRef = useRef<((e: Event) => void) | null>(null);
  const ackHandlerRef = useRef<((e: Event) => void) | null>(null);

  const loadAlerts = useCallback(
    async (q: AlertHistoryQuery) => {
      setLoading(true);
      try {
        await fetchAlerts(q);
      } finally {
        setLoading(false);
      }
    },
    [fetchAlerts]
  );

  useEffect(() => {
    loadAlerts(query);
  }, [query, loadAlerts]);

  useEffect(() => {
    viewDetailHandlerRef.current = (e: Event) => {
      const customEvent = e as CustomEvent<AlertRecord>;
      if (customEvent.detail) {
        setDetailAlert(customEvent.detail);
        setModalOpen(true);
      }
    };
    ackHandlerRef.current = (e: Event) => {
      const customEvent = e as CustomEvent<string>;
      if (customEvent.detail) {
        handleAcknowledge(customEvent.detail);
      }
    };
    window.addEventListener('view-alert-detail', viewDetailHandlerRef.current);
    window.addEventListener('acknowledge-alert', ackHandlerRef.current);
    return () => {
      if (viewDetailHandlerRef.current) {
        window.removeEventListener('view-alert-detail', viewDetailHandlerRef.current);
      }
      if (ackHandlerRef.current) {
        window.removeEventListener('acknowledge-alert', ackHandlerRef.current);
      }
    };
  }, [query]);

  const handleFilterChange = (newQuery: AlertHistoryQuery) => {
    setQuery(newQuery);
  };

  const handleFilterReset = () => {
    setQuery(DEFAULT_QUERY);
  };

  const handlePageChange = (page: number) => {
    setQuery((prev) => ({ ...prev, page }));
  };

  const handleAcknowledge = async (id: string) => {
    await acknowledgeAlert(id);
    loadAlerts(query);
  };

  const handleViewDetail = (alert: AlertRecord) => {
    setDetailAlert(alert);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setTimeout(() => setDetailAlert(null), 200);
  };

  const handleModalAcknowledge = async (id: string) => {
    await acknowledgeAlert(id);
    setDetailAlert((prev) => (prev ? { ...prev, acknowledged: true } : prev));
    loadAlerts(query);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Clock className="h-5 w-5 text-brand-cyan" />
          <h2 className="text-lg font-semibold text-brand-text-primary">预警历史记录</h2>
          <span className="rounded-full bg-brand-cyan/10 px-2.5 py-0.5 text-xs font-medium text-brand-cyan">
            {alertsTotal} 条
          </span>
        </div>
      </div>

      <AlertFilterBar query={query} onChange={handleFilterChange} onReset={handleFilterReset} />

      {loading ? (
        <SkeletonRows />
      ) : (
        <VirtualAlertTable
          alerts={alerts}
          total={alertsTotal}
          page={alertsPage}
          pageSize={alertsPageSize}
          loading={loading}
          onPageChange={handlePageChange}
          onAcknowledge={handleAcknowledge}
          onViewDetail={handleViewDetail}
        />
      )}

      <AlertDetailModal
        open={modalOpen}
        alert={detailAlert}
        onClose={handleCloseModal}
        onAcknowledge={handleModalAcknowledge}
      />
    </div>
  );
}

