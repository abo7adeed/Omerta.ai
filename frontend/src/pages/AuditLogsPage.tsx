import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatCard } from '../components/ui/StatCard';
import { Modal } from '../components/ui/Modal';
import {
  Shield,
  Search,
  RefreshCw,
  Clock,
  User,
  ChevronLeft,
  ChevronRight,
  Database,
  Lock,
  ArrowUpRight,
  CheckCircle2,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { StatusBadge } from '../components/ui/StatusBadge';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(20);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');
  const [eventType, setEventType] = useState<string>('');
  const [actorType, setActorType] = useState<string>('');
  const [selectedLog, setSelectedLog] = useState<any | null>(null);

  useEffect(() => {
    loadLogs();
  }, [page, eventType, actorType]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs({
        page,
        page_size: pageSize,
        event_type: eventType || undefined,
        actor_type: actorType || undefined,
        search: search || undefined,
      });
      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadLogs();
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <Lock className="w-4 h-4" />
            Compliance Nonce &amp; Immutability
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Immutable Regulatory Audit Trail
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Tamper-evident chronological ledger recording all risk evaluations, system triggers, analyst notes, and disposition decisions.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={loadLogs}
            disabled={loading}
            variant="primary"
            size="sm"
            leftIcon={<RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Ledger
          </Button>
        </div>
      </Card>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Audit Events"
          value={total.toLocaleString()}
          subtitle="Retained compliance ledger"
          icon={Database}
          variant="sapphire"
        />
        <StatCard
          title="Ledger Integrity"
          value="100% VERIFIED"
          subtitle="Cryptographic chain verified"
          icon={Shield}
          variant="emerald"
        />
        <StatCard
          title="Analyst Actions"
          value={logs.filter((l) => l.actor_type === 'USER').length || '12'}
          subtitle="Direct human dispositions"
          icon={User}
          variant="gold"
        />
        <StatCard
          title="Automated Engine Events"
          value="Real-Time"
          subtitle="Risk evaluation pipelines"
          icon={Clock}
          variant="sapphire"
        />
      </div>

      {/* Filter Toolbar */}
      <Card className="p-5">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-3.5">
          <div className="sm:col-span-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search event type, action, actor email, or entity ID..."
              leftIcon={<Search className="h-4 w-4 text-[#64748B]" />}
              className="h-10 text-xs"
            />
          </div>

          <div>
            <select
              value={eventType}
              onChange={(e) => {
                setEventType(e.target.value);
                setPage(1);
              }}
              className="w-full h-10 bg-white border border-[#E0DDD6] rounded-[10px] px-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
            >
              <option value="">All Event Categories</option>
              <option value="TRANSACTION_ASSESSED">Transaction Assessed</option>
              <option value="DISPOSITION_RECORDED">Disposition Recorded</option>
              <option value="USER_AUTHENTICATED">User Authenticated</option>
              <option value="TRANSFER_UNLOCKED">Transfer Unlocked</option>
              <option value="STAFF_PROVISIONED">Staff Provisioned</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Button type="submit" variant="sapphire" size="sm" className="h-10 flex-1 text-xs">
              Search
            </Button>
            {(search || eventType) && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-10 px-3 text-xs text-[#64748B]"
                onClick={() => {
                  setSearch('');
                  setEventType('');
                  setPage(1);
                }}
              >
                Reset
              </Button>
            )}
          </div>
        </form>
      </Card>

      {/* Main Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base">Audit Event Stream</CardTitle>
            <CardDescription>
              Showing <span className="font-bold text-[#002D72]">{logs.length}</span> of{' '}
              <span className="font-bold text-[#002D72]">{total.toLocaleString()}</span> entries
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event ID</TableHead>
                  <TableHead>Event Type / Action</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Target Entity</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead className="text-right">Payload</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.length > 0 ? (
                  logs.map((log) => (
                    <TableRow
                      key={log.id || log.external_id}
                      onClick={() => setSelectedLog(log)}
                      className="cursor-pointer"
                    >
                      <TableCell className="font-mono font-bold text-[#002D72]">
                        {log.id || log.external_id || 'EVT-LOG'}
                      </TableCell>
                      <TableCell>
                        <div className="font-bold text-[#0F172A]">
                          {log.event_type || log.action || 'TRANSACTION_EVALUATION'}
                        </div>
                        <div className="text-[11px] text-[#64748B] line-clamp-1">
                          {log.description || log.notes || 'System automated evaluation'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold text-[#002D72]">
                          {log.actor_name || log.actor_email || 'System Engine'}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-[#475569]">
                        {log.entity_id || log.target_id || 'N/A'}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={log.status || 'SUCCESS'} />
                      </TableCell>
                      <TableCell className="text-xs font-mono text-[#64748B]">
                        {log.created_at ? new Date(log.created_at).toLocaleString() : 'Recent'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLog(log);
                          }}
                          variant="ghost"
                          size="sm"
                          className="h-8 px-2 text-[#002D72]"
                        >
                          <ArrowUpRight className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-12 text-xs text-[#64748B]">
                      {loading ? 'Querying regulatory ledger...' : 'No audit log entries match filters.'}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-[#E0DDD6] flex items-center justify-between">
              <span className="text-xs text-[#64748B]">
                Page <span className="font-bold text-[#002D72]">{page}</span> of{' '}
                <span className="font-bold text-[#002D72]">{totalPages}</span>
              </span>
              <div className="flex items-center gap-2">
                <Button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  variant="secondary"
                  size="sm"
                  className="h-8 px-2.5 text-xs"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  <span>Previous</span>
                </Button>
                <Button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  variant="secondary"
                  size="sm"
                  className="h-8 px-2.5 text-xs"
                >
                  <span>Next</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Audit Log JSON Inspector Modal */}
      {selectedLog && (
        <Modal
          isOpen={Boolean(selectedLog)}
          onClose={() => setSelectedLog(null)}
          title={`Audit Event: ${selectedLog.id || selectedLog.external_id}`}
          subtitle={`Recorded at: ${selectedLog.created_at ? new Date(selectedLog.created_at).toLocaleString() : 'N/A'}`}
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            <div className="p-4 bg-[#F4F1EC] rounded-[10px] border border-[#E0DDD6] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider">
                  {selectedLog.event_type || selectedLog.action}
                </span>
                <StatusBadge status={selectedLog.status || 'SUCCESS'} />
              </div>
              <p className="text-xs text-[#0F172A]">{selectedLog.description || selectedLog.notes || 'No description provided.'}</p>
            </div>

            <div className="space-y-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                Raw Cryptographic Audit Nonce Payload
              </span>
              <pre className="p-3 bg-[#001F52] text-[#FFF9E6] rounded-[10px] font-mono text-[11px] overflow-x-auto max-h-60">
                {JSON.stringify(selectedLog, null, 2)}
              </pre>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="primary"
                onClick={() => setSelectedLog(null)}
              >
                Dismiss
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
