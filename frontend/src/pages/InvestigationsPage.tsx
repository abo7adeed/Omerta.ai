import React, { useEffect, useState } from 'react';
import {
  FolderSearch,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ArrowUpRight,
  ShieldAlert,
  UserCheck,
  Clock,
  FileText,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../api/client';
import type { CaseItem } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { RiskBadge } from '../components/ui/RiskBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const InvestigationsPage: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [page, setPage] = useState(1);

  // Case Dossier Modal state
  const [selectedCase, setSelectedCase] = useState<any | null>(null);
  const [dossierLoading, setDossierLoading] = useState(false);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const res = await api.getCases({
        status: statusFilter,
        severity: severityFilter,
        page,
        page_size: 15,
      });
      setCases(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load investigation cases', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [page, statusFilter, severityFilter]);

  const handleOpenDossier = async (c: CaseItem) => {
    setDossierLoading(true);
    try {
      const res = await api.getCaseDetail(c.external_id);
      setSelectedCase(res);
    } catch (err) {
      console.error('Failed to load case detail', err);
    } finally {
      setDossierLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Page Header */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <FolderSearch className="w-4 h-4" />
            Forensic Intelligence
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Compliance Investigation Cases
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Formal forensic case files opened for high-priority AML alerts and anomalous financial typologies.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={fetchCases}
            variant="primary"
            size="sm"
            leftIcon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Cases
          </Button>
        </div>
      </Card>

      {/* Filter Toolbar */}
      <Card className="p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="h-10 bg-white border border-[#E0DDD6] rounded-[10px] px-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
          >
            <option value="">All Case Statuses</option>
            <option value="NEW">New</option>
            <option value="UNDER_INVESTIGATION">Under Investigation</option>
            <option value="ESCALATED">Escalated</option>
            <option value="RESOLVED">Resolved</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setPage(1);
            }}
            className="h-10 bg-white border border-[#E0DDD6] rounded-[10px] px-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
          >
            <option value="">All Severities</option>
            <option value="HIGH">High Severity</option>
            <option value="MEDIUM">Medium Severity</option>
            <option value="LOW">Low Severity</option>
          </select>
        </div>

        <div className="text-xs text-[#64748B] font-medium">
          Total: <span className="font-bold text-[#002D72]">{total}</span> formal cases
        </div>
      </Card>

      {/* Main Cases Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base">Investigation Case Files</CardTitle>
            <CardDescription>
              Showing <span className="font-bold text-[#002D72]">{cases.length}</span> active cases
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Case ID</TableHead>
                  <TableHead>Title / Typology Scenario</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Assigned Lead</TableHead>
                  <TableHead>Related Entity</TableHead>
                  <TableHead>Opened Date</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cases.length > 0 ? (
                  cases.map((c) => (
                    <TableRow
                      key={c.external_id}
                      onClick={() => handleOpenDossier(c)}
                      className="cursor-pointer"
                    >
                      <TableCell className="font-mono font-bold text-[#002D72]">
                        {c.external_id}
                      </TableCell>
                      <TableCell>
                        <div className="font-bold text-[#0F172A] max-w-xs truncate">
                          {c.title}
                        </div>
                        <div className="text-[11px] text-[#64748B] line-clamp-1">
                          {c.summary || (c as any).description || 'Structuring / Velocity Review'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <RiskBadge level={c.severity || 'MEDIUM'} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={c.status || 'UNDER_INVESTIGATION'} />
                      </TableCell>
                      <TableCell className="text-xs text-[#0F172A]">
                        {c.assigned_to || (c as any).assigned_to_name || 'Dr. Sarah Al-Rashid'}
                      </TableCell>
                      <TableCell className="text-xs font-mono text-[#64748B]">
                        {c.alert_id || (c as any).related_alert_id || (c as any).customer_id || 'ENT-TARGET'}
                      </TableCell>
                      <TableCell className="text-xs font-mono text-[#64748B]">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString() : 'Recent'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenDossier(c);
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
                    <TableCell colSpan={8} className="text-center py-12 text-xs text-[#64748B]">
                      {loading ? 'Retrieving case files...' : 'No investigation cases match filters.'}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Case Dossier Modal */}
      {selectedCase && (
        <Modal
          isOpen={Boolean(selectedCase)}
          onClose={() => setSelectedCase(null)}
          title={`Investigation Dossier: ${selectedCase.external_id || selectedCase.id}`}
          subtitle={`Lead Analyst: ${selectedCase.assigned_to_name || 'Dr. Sarah Al-Rashid'}`}
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-[#F4F1EC] p-3.5 rounded-[12px] border border-[#E0DDD6]">
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Case Severity</span>
                <div className="mt-0.5">
                  <RiskBadge level={selectedCase.severity || 'HIGH'} />
                </div>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Case Status</span>
                <div className="mt-0.5">
                  <StatusBadge status={selectedCase.status || 'UNDER_INVESTIGATION'} />
                </div>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Created</span>
                <p className="font-mono text-[#002D72] mt-0.5">
                  {selectedCase.created_at ? new Date(selectedCase.created_at).toLocaleDateString() : 'N/A'}
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Priority</span>
                <p className="font-bold text-[#B45309] mt-0.5">{selectedCase.priority || 'HIGH'}</p>
              </div>
            </div>

            <div className="p-4 bg-white rounded-[12px] border border-[#E0DDD6] space-y-2">
              <h5 className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider">
                Investigative Findings &amp; Evidence
              </h5>
              <p className="text-xs text-[#0F172A] leading-relaxed">
                {selectedCase.description || 'Target entity demonstrated anomalous money routing across newly linked accounts.'}
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="primary"
                onClick={() => setSelectedCase(null)}
              >
                Close Dossier
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
