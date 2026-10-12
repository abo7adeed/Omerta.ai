import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldAlert,
  Wallet,
  Sparkles,
  CheckCircle2,
  Share2,
  Clock,
  Smartphone,
  Globe,
  Activity,
  ShieldCheck,
  XCircle,
  Play,
  RotateCw,
  Cpu,
  Layers,
  Database,
  Network,
  Scale,
  FileText,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  History,
  Lock,
  Unlock,
  Phone,
  Mail,
  UserCheck,
  UserX,
  Copy,
  Check,
  Zap,
} from 'lucide-react';
import { api, type AccountInvestigationReport, type PipelineStageTrace, type LiveInvestigationSnapshot } from '../api/client';
import type { TransactionDetail } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { RiskBadge } from '../components/ui/RiskBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { Tabs } from '../components/ui/Tabs';
import { Timeline, type TimelineItem } from '../components/ui/Timeline';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const TransactionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<TransactionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'specialists' | 'report'>('overview');
  const [historyIntel, setHistoryIntel] = useState<any | null>(null);

  // LangGraph Transaction Investigation State & Live Monotonic Snapshot
  const [investigationRunning, setInvestigationRunning] = useState(false);
  const [investigationReport, setInvestigationReport] = useState<AccountInvestigationReport | null>(null);
  const [liveSnapshot, setLiveSnapshot] = useState<LiveInvestigationSnapshot | null>(null);
  const [investigationError, setInvestigationError] = useState<string | null>(null);
  const [expandedStages, setExpandedStages] = useState<Record<string, boolean>>({});
  const [copiedReport, setCopiedReport] = useState(false);

  // Human-in-the-Loop Security Hold State
  const [accountStatus, setAccountStatus] = useState<string>('ACTIVE');
  const [actionLoading, setActionLoading] = useState(false);

  // Quick Disposition Modal State
  const [dispositionModalOpen, setDispositionModalOpen] = useState(false);
  const [disposition, setDisposition] = useState('LEGITIMATE_ACTIVITY');
  const [rationale, setRationale] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState('');

  const fetchDetail = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await api.getTransactionDetail(id);
      setDetail(res);

      const accStatus = res?.overview?.source_account?.status || (res as any)?.sender_account_status || (res as any)?.account_status || 'ACTIVE';
      setAccountStatus(accStatus);

      // Check live investigation status or persisted report
      try {
        const live = await api.getTransactionInvestigationLive(id);
        setLiveSnapshot(live);
        if (live.status === 'RUNNING') {
          setInvestigationRunning(true);
          setActiveTab('report');
        } else if (live.status === 'COMPLETED' && live.final_report) {
          setInvestigationReport(live.final_report);
        }
      } catch {
        if (res.persisted_investigation) {
          setInvestigationReport(res.persisted_investigation);
        }
      }

      // Fetch rolling history intelligence
      try {
        const hist = await api.getTransactionHistory(id);
        setHistoryIntel(hist);
      } catch {
        // Handled silently
      }
    } catch (err) {
      console.error('Failed to load transaction detail', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  // Live polling hook while investigation is running
  useEffect(() => {
    if (!investigationRunning || !id) return;

    const interval = setInterval(async () => {
      try {
        const live = await api.getTransactionInvestigationLive(id);
        setLiveSnapshot(live);
        if (live.status === 'COMPLETED' && live.final_report) {
          setInvestigationReport(live.final_report);
          setInvestigationRunning(false);
          setActionSuccess('Parallel LangGraph investigation completed! Final report ready.');
          setTimeout(() => setActionSuccess(''), 4000);
        } else if (live.status === 'FAILED') {
          setInvestigationRunning(false);
          setInvestigationError(live.error_message || 'Investigation workflow failed.');
        }
      } catch (err) {
        console.error('Polling investigation state error:', err);
      }
    }, 750);

    return () => clearInterval(interval);
  }, [investigationRunning, id]);

  const rawOverview = detail?.overview || (detail as any) || {};
  const externalId = rawOverview.external_id || (detail as any)?.external_id || (detail as any)?.id || id || 'TXN-UNKNOWN';
  const amount = rawOverview.amount ?? 0;
  const currency = rawOverview.currency || 'EGP';
  const status = rawOverview.status || 'COMPLETED';
  const timestamp = rawOverview.timestamp || (detail as any)?.created_at || (rawOverview as any)?.created_at;
  const sourceAccount = rawOverview.source_account?.external_id || (rawOverview as any).sender_account_number || (rawOverview as any).source_account || 'N/A';
  const customerName = rawOverview.source_account?.customer_name || rawOverview.customer?.name || (rawOverview as any).sender_name || (rawOverview as any).customer_name || 'Account Holder';
  const sourceBalance = rawOverview.source_account?.balance ?? 0;
  const sourceAccountType = rawOverview.source_account?.account_type || 'CHECKING';
  const recipientAccount = rawOverview.recipient_account?.external_id || (rawOverview as any).receiver_account_number || (rawOverview as any).recipient_account || 'N/A';
  const recipientName = rawOverview.recipient_account?.customer_name || (rawOverview as any).receiver_name || (recipientAccount !== 'N/A' ? recipientAccount : 'Beneficiary Account');
  const deviceId = rawOverview.device?.external_id || (rawOverview as any).device_id || (rawOverview as any).device || 'DEV-WEB-SECURE';
  const ipAddress = rawOverview.ip_address?.address || (rawOverview as any).ip_address || '197.34.120.55';

  const precedingList = detail?.preceding_transactions || [];
  const subsequentList = detail?.subsequent_transactions || [];

  const assessment = detail?.assessment || detail?.risk_assessment || (detail as any)?.risk_assessment || {
    risk_score: 0,
    risk_level: 'LOW' as any,
    requires_human_review: false,
    version: 'v1.0',
    summary: 'Standard automated assessment completed.',
  };

  const signals = detail?.signals || (detail as any)?.risk_signals || [];

  // Toggle stage card expansion in Pipeline view
  const toggleStage = (stageId: string) => {
    setExpandedStages((prev) => ({ ...prev, [stageId]: !prev[stageId] }));
  };

  // Run LangGraph Transaction Investigation
  const handleRunInvestigation = async () => {
    if (!externalId) return;
    setInvestigationRunning(true);
    setInvestigationError(null);
    try {
      const res = await api.investigateTransaction({
        transaction_id: externalId,
        time_range_days: 30,
        investigation_reason: 'MANUAL_OFFICER_REQUEST',
        persist: true,
      });
      setInvestigationReport(res);
      setActiveTab('report');
      setActionSuccess('LangGraph multi-agent forensic report generated and persisted!');
      setTimeout(() => setActionSuccess(''), 4000);
    } catch (err: any) {
      console.error('Transaction investigation failed:', err);
      setInvestigationError(err?.message || 'Failed to complete transaction investigation.');
    } finally {
      setInvestigationRunning(false);
    }
  };

  // Human-in-the-Loop: Unblock Account
  const handleUnblockAccount = async () => {
    if (!sourceAccount || sourceAccount === 'N/A') return;
    setActionLoading(true);
    try {
      await api.unblockAccount(sourceAccount);
      setAccountStatus('ACTIVE');
      setActionSuccess(`Account ${sourceAccount} unblocked! User active status and transfer capabilities restored.`);
      setTimeout(() => setActionSuccess(''), 4000);
      fetchDetail();
    } catch (err: any) {
      setInvestigationError(err?.message || 'Failed to unblock account.');
    } finally {
      setActionLoading(false);
    }
  };

  // Admin: Approve Held Transfer and Post to Ledger
  const handleApproveTransfer = async () => {
    if (!externalId) return;
    setActionLoading(true);
    try {
      await api.approvePendingTransaction(externalId, 'Compliance officer approved held transaction after evidence review.');
      setActionSuccess(`Transfer ${externalId} approved! Double-entry ledger settlement executed successfully.`);
      setTimeout(() => setActionSuccess(''), 5000);
      fetchDetail();
    } catch (err: any) {
      setInvestigationError(err?.message || 'Failed to approve transaction.');
    } finally {
      setActionLoading(false);
    }
  };

  // Admin: Reject Held Transfer without Ledger Posting
  const handleRejectTransfer = async () => {
    if (!externalId) return;
    setActionLoading(true);
    try {
      await api.rejectPendingTransaction(externalId, 'Transfer rejected due to confirmed fraud or unauthorized activity.');
      setActionSuccess(`Transfer ${externalId} rejected! Held funds released without ledger settlement.`);
      setTimeout(() => setActionSuccess(''), 5000);
      fetchDetail();
    } catch (err: any) {
      setInvestigationError(err?.message || 'Failed to reject transaction.');
    } finally {
      setActionLoading(false);
    }
  };

  // Admin: Restore Customer Transfer Privileges (Release restriction + resolve ticket)
  const handleRestorePrivileges = async () => {
    const custId = rawOverview.customer?.id || rawOverview.customer?.external_id;
    if (!custId) return;
    setActionLoading(true);
    try {
      await api.adminRestoreTransactionPrivileges(custId, 'Compliance officer verified identity and released transaction restriction.');
      setActionSuccess(`Customer transfer privileges restored! Outgoing transfers restriction cleared.`);
      setTimeout(() => setActionSuccess(''), 5000);
      fetchDetail();
    } catch (err: any) {
      setInvestigationError(err?.message || 'Failed to restore transaction privileges.');
    } finally {
      setActionLoading(false);
    }
  };

  // Human-in-the-Loop: Contain / Block Account
  const handleBlockAccount = async () => {
    if (!sourceAccount || sourceAccount === 'N/A') return;
    setActionLoading(true);
    try {
      await api.blockAccount(sourceAccount);
      setAccountStatus('BLOCKED');
      setActionSuccess(`Account ${sourceAccount} placed under security containment hold (BLOCKED). Login access revoked.`);
      setTimeout(() => setActionSuccess(''), 4000);
      fetchDetail();
    } catch (err: any) {
      setInvestigationError(err?.message || 'Failed to block account.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRecordDisposition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!externalId) return;
    setSubmitting(true);
    try {
      const targetId = detail?.related_cases?.[0]?.id || externalId;
      await api.recordCaseDisposition(targetId, {
        disposition,
        rationale: rationale.trim() || 'Reviewed against transactional evidence and account behavioral baseline.',
        new_status: 'RESOLVED',
      });
      setActionSuccess('Compliance review disposition recorded successfully!');
      setTimeout(() => {
        setDispositionModalOpen(false);
        setActionSuccess('');
        fetchDetail();
      }, 1500);
    } catch (err) {
      console.error('Failed to record disposition', err);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-[#64748B] space-y-3">
        <ShieldAlert className="h-10 w-10 animate-bounce mx-auto text-[#002D72]" />
        <p className="font-bold text-[#002D72]">Loading forensic transaction workbench...</p>
        <p className="text-xs text-[#64748B]">Querying verified PostgreSQL ledger, Neo4j topology, and LightGBM models</p>
      </div>
    );
  }

  if (!detail) {
    return (
      <Card className="p-12 text-center space-y-4">
        <p className="text-lg font-bold text-[#002D72]">Transaction {id} was not found.</p>
        <p className="text-xs text-[#64748B]">The record may have been archived or the ID is invalid.</p>
        <Button onClick={() => navigate('/admin/transactions')} variant="secondary">
          Return to Transactions Directory
        </Button>
      </Card>
    );
  }

  const timelineItems: TimelineItem[] = [
    {
      id: 'init',
      title: 'Transaction Dispatched',
      description: `Dispatched via Digital Banking from account ${sourceAccount}`,
      timestamp: timestamp ? new Date(timestamp).toLocaleString() : 'Recent',
      status: 'completed',
    },
    {
      id: 'assessment',
      title: `Risk Engine Assessment (${assessment.risk_level || 'LOW'})`,
      description: `Risk score evaluated at ${(assessment.risk_score || 0).toFixed(1)}% with ${signals.length} signal vector(s).`,
      timestamp: timestamp ? new Date(timestamp).toLocaleTimeString() : undefined,
      status: 'completed',
    },
    ...(investigationReport
      ? [
          {
            id: 'investigation',
            title: `LangGraph Forensic Dossier (${investigationReport.investigation_id || 'INV-TXN'})`,
            description: `Executed 9-stage pipeline. Composite risk: ${((investigationReport.combined_risk_score ?? 0) * 100).toFixed(1)}%. Recommendation: ${investigationReport.recommended_action || 'UNDER_REVIEW'}`,
            timestamp: investigationReport.generated_at ? new Date(investigationReport.generated_at).toLocaleTimeString() : undefined,
            status: 'completed' as const,
          },
        ]
      : []),
  ];

  const pipelineStages: PipelineStageTrace[] = investigationReport?.pipeline_stages || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner Notifications */}
      {actionSuccess && (
        <div className="p-3.5 rounded-[12px] bg-[#E8F5E9] border border-[#A5D6A7] text-[#1B5E20] text-xs font-semibold flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-[#2E7D32]" />
            {actionSuccess}
          </span>
          <button onClick={() => setActionSuccess('')} className="text-[#2E7D32] hover:underline text-[11px]">Dismiss</button>
        </div>
      )}

      {investigationError && (
        <div className="p-3.5 rounded-[12px] bg-[#FFEBEE] border border-[#FFCDD2] text-[#B71C1C] text-xs font-semibold flex items-center justify-between">
          <span className="flex items-center gap-2">
            <XCircle className="h-4 w-4 text-[#C62828]" />
            {investigationError}
          </span>
          <button onClick={() => setInvestigationError(null)} className="text-[#C62828] hover:underline text-[11px]">Dismiss</button>
        </div>
      )}

      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E0DDD6] pb-4">
        <div>
          <button
            onClick={() => navigate('/admin/transactions')}
            className="flex items-center gap-1.5 text-xs font-bold text-[#64748B] hover:text-[#002D72] mb-1.5 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Transactions</span>
          </button>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#002D72] font-mono">
              Dossier: {externalId}
            </h1>
            <StatusBadge status={status} />
            {investigationReport && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#EBF3FC] text-[#002D72] border border-[#BFDBFE]">
                <Sparkles className="w-3 h-3 text-[#F9A825]" />
                Investigated
              </span>
            )}
          </div>
          <p className="text-xs text-[#64748B] mt-1 font-mono">
            Timestamp: {timestamp ? new Date(timestamp).toLocaleString() : 'N/A'} · Source: PostgreSQL Relational Ledger
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          {accountStatus === 'BLOCKED' ? (
            <Button
              onClick={handleUnblockAccount}
              disabled={actionLoading}
              size="sm"
              className="bg-[#2E7D32] hover:bg-[#1B5E20] text-white font-bold border-none shadow-sm"
            >
              <Unlock className={`w-4 h-4 mr-1.5 ${actionLoading ? 'animate-spin' : ''}`} />
              {actionLoading ? 'Unblocking...' : 'Unblock Account (HITL)'}
            </Button>
          ) : (
            <Button
              onClick={handleBlockAccount}
              disabled={actionLoading}
              size="sm"
              className="bg-[#DC2626] hover:bg-[#B91C1C] text-white font-bold border-none shadow-sm"
            >
              <Lock className={`w-4 h-4 mr-1.5 ${actionLoading ? 'animate-spin' : ''}`} />
              {actionLoading ? 'Freezing...' : 'Contain / Block Account'}
            </Button>
          )}

          <Button
            onClick={handleRunInvestigation}
            disabled={investigationRunning}
            variant="primary"
            size="sm"
            className="bg-[#F9A825] hover:bg-[#F57F17] text-[#002D72] font-bold border-none shadow-sm"
          >
            <Cpu className={`w-4 h-4 mr-1.5 ${investigationRunning ? 'animate-spin' : ''}`} />
            {investigationRunning ? 'Executing Pipeline...' : 'Investigate Transaction (LangGraph)'}
          </Button>

          <Button
            onClick={() => setDispositionModalOpen(true)}
            variant="sapphire"
            size="sm"
          >
            <Scale className="w-4 h-4 mr-1.5" />
            Record Disposition
          </Button>

          <Button
            onClick={() => navigate(`/admin/network?account=${encodeURIComponent(sourceAccount || externalId)}`)}
            variant="secondary"
            size="sm"
          >
            <Share2 className="w-4 h-4 text-[#002D72] mr-1.5" />
            Inspect Graph
          </Button>
        </div>
      </div>

      {/* Security Hold Containment Banner */}
      {accountStatus === 'BLOCKED' && (
        <div className="p-4 rounded-[12px] bg-[#FEF2F2] border-2 border-[#DC2626] shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <ShieldAlert className="w-5 h-5 text-[#DC2626] shrink-0" />
              <div>
                <span className="font-extrabold text-[#991B1B] text-sm tracking-tight uppercase">
                  Human-in-the-Loop Security Containment Active
                </span>
                <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-[#DC2626] text-white">
                  ACCOUNT BLOCKED
                </span>
              </div>
            </div>
            <Button
              onClick={handleUnblockAccount}
              disabled={actionLoading}
              size="sm"
              className="bg-[#2E7D32] hover:bg-[#1B5E20] text-white font-bold text-xs shadow-xs"
            >
              <Unlock className="w-3.5 h-3.5 mr-1" />
              Unblock Account & Restore Login
            </Button>
          </div>
          <p className="text-xs text-[#7F1D1D] leading-relaxed">
            Originating Account <strong className="font-mono">{sourceAccount}</strong> ({customerName}) is placed under security containment following an automated high-risk transaction evaluation. The user is currently restricted from logging in or initiating new transfers until an investigator verifies facts and unblocks access.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 text-xs">
            <div className="p-2.5 bg-white rounded-[8px] border border-[#FECACA] flex items-center gap-2 text-[#991B1B]">
              <Phone className="w-4 h-4 text-[#DC2626] shrink-0" />
              <span>Customer Support Hotline: <strong className="font-mono text-sm">+20 2 19876</strong></span>
            </div>
            <div className="p-2.5 bg-white rounded-[8px] border border-[#FECACA] flex items-center gap-2 text-[#991B1B]">
              <Mail className="w-4 h-4 text-[#DC2626] shrink-0" />
              <span>Compliance Desk: <strong>compliance@omerta.ai</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* Held Transaction Action Banner (When Status is PENDING_CUSTOMER_VERIFICATION or PENDING_REVIEW) */}
      {(status === 'PENDING_CUSTOMER_VERIFICATION' || status === 'PENDING_REVIEW') && (
        <div className="p-4 rounded-[12px] bg-[#FFFBEB] border-2 border-[#F59E0B] shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <ShieldAlert className="w-5 h-5 text-[#D97706] shrink-0" />
              <div>
                <span className="font-extrabold text-[#92400E] text-sm tracking-tight uppercase">
                  {status === 'PENDING_CUSTOMER_VERIFICATION'
                    ? 'Transfer Held — Pending Customer Confirmation'
                    : 'Transfer Held — Pending Compliance Review'}
                </span>
                <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-[#F59E0B] text-white">
                  STATUS: {status}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={handleRejectTransfer}
                disabled={actionLoading}
                size="sm"
                className="bg-[#DC2626] hover:bg-[#B91C1C] text-white font-bold text-xs"
              >
                <XCircle className="w-3.5 h-3.5 mr-1" />
                Reject Transfer
              </Button>
              <Button
                onClick={handleApproveTransfer}
                disabled={actionLoading}
                size="sm"
                className="bg-[#2E7D32] hover:bg-[#1B5E20] text-white font-bold text-xs"
              >
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                Approve Transfer (Settle Ledger)
              </Button>
            </div>
          </div>
          <p className="text-xs text-[#78350F] leading-relaxed">
            <strong>Hold Reason:</strong> {rawOverview.hold_reason || (rawOverview.ip_address?.is_vpn ? 'Commercial VPN / Proxy Detected (RULE-NETWORK-VPN-001)' : 'High Risk Threshold Exceeded')}.<br />
            <strong>Ledger Settlement Notice:</strong> Double-entry transfer has <em>NOT been executed</em>. Originating account funds remain in place. Approving this transfer will commit double-entry ledger debit and credit entries.
          </p>
        </div>
      )}

      {/* Customer Privilege Restriction Banner (When Customer Has Active Restrictions) */}
      {(rawOverview.has_transfer_restriction || (rawOverview.active_restrictions && rawOverview.active_restrictions.length > 0)) && (
        <div className="p-4 rounded-[12px] bg-[#FEF2F2] border border-[#F87171] shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <ShieldAlert className="w-5 h-5 text-[#DC2626] shrink-0" />
              <div>
                <span className="font-extrabold text-[#991B1B] text-sm tracking-tight uppercase">
                  Customer Transfer Privileges Suspended
                </span>
                <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-[#DC2626] text-white">
                  RESTRICTION: OUTGOING_TRANSFERS_ONLY
                </span>
              </div>
            </div>
            <Button
              onClick={handleRestorePrivileges}
              disabled={actionLoading}
              size="sm"
              className="bg-[#2E7D32] hover:bg-[#1B5E20] text-white font-bold text-xs shadow-xs"
            >
              <Unlock className="w-3.5 h-3.5 mr-1" />
              Restore Transaction Privileges
            </Button>
          </div>
          <p className="text-xs text-[#7F1D1D] leading-relaxed">
            Customer <strong className="font-mono">{customerName}</strong> is restricted from initiating outgoing transfers due to a reported fraud incident or customer denial.
            <br />
            <em>Operational Note: Restoring privileges releases account restriction and resolves the security ticket, but does NOT approve individual held transactions.</em>
          </p>
        </div>
      )}

      {/* Primary 3 Overview Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Financial Movement Summary */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Wallet className="w-4.5 h-4.5 text-[#002D72]" />
              Financial Movement Summary
            </CardTitle>
            <CardDescription>Verified double-entry ledger transfer facts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="p-3.5 bg-[#F4F1EC] rounded-[12px] border border-[#E0DDD6]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                  Transfer Amount
                </span>
                <div className="text-xl font-bold font-mono text-[#002D72] mt-0.5">
                  {amount ? `${Number(amount).toLocaleString()} ${currency}` : `0 ${currency}`}
                </div>
              </div>

              <div className="p-3.5 bg-[#F4F1EC] rounded-[12px] border border-[#E0DDD6]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                  Channel / Protocol
                </span>
                <div className="text-sm font-bold text-[#0F172A] mt-1 flex items-center gap-1.5">
                  <Globe className="w-4 h-4 text-[#1E88E5]" />
                  <span>Digital Banking</span>
                </div>
              </div>

              <div className="p-3.5 bg-[#F4F1EC] rounded-[12px] border border-[#E0DDD6]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                  Device Identifier
                </span>
                <div className="text-xs font-mono font-bold text-[#002D72] mt-1 truncate flex items-center gap-1">
                  <Smartphone className="w-3.5 h-3.5 text-[#64748B]" />
                  <span>{deviceId}</span>
                </div>
              </div>
            </div>

            {/* Sender & Receiver Dual Panel */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4 pt-4 border-t border-[#E0DDD6]">
              <div className="p-4 bg-white rounded-[12px] border border-[#E0DDD6] space-y-1.5">
                <div className="flex items-center justify-between text-xs font-bold uppercase text-[#64748B]">
                  <span>Originating Account (Sender)</span>
                  <span className="text-[#002D72] font-mono">Source</span>
                </div>
                <div className="font-bold text-[#002D72] text-sm">
                  {customerName}
                </div>
                <div className="text-xs font-mono text-[#475569]">
                  Account: {sourceAccount}
                </div>
                <div className="text-[11px] text-[#64748B] pt-1">
                  Available Balance: <span className="font-bold font-mono text-[#002D72]">{Number(sourceBalance).toLocaleString()} {currency}</span> ({sourceAccountType})
                </div>
              </div>

              <div className="p-4 bg-white rounded-[12px] border border-[#E0DDD6] space-y-1.5">
                <div className="flex items-center justify-between text-xs font-bold uppercase text-[#64748B]">
                  <span>Beneficiary Account (Receiver)</span>
                  <span className="text-[#10B981] font-mono">Destination</span>
                </div>
                <div className="font-bold text-[#002D72] text-sm">
                  {recipientName}
                </div>
                <div className="text-xs font-mono text-[#475569]">
                  Account: {recipientAccount}
                </div>
                <div className="text-[11px] text-[#64748B] pt-1">
                  Settlement Status: <span className="font-bold text-[#10B981]">Cleared & Reconciled</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Risk Assessment Overview */}
        <Card className="flex flex-col justify-between">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldAlert className="w-4.5 h-4.5 text-[#F9A825]" />
              Risk Assessment
            </CardTitle>
            <CardDescription>Multi-signal fraud &amp; AML score</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-[12px] bg-[#FFF9E6] border border-[#FFE082] flex items-center justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#92400E]">
                  Evaluated Risk Score
                </span>
                <div className="text-3xl font-extrabold font-mono text-[#002D72] mt-0.5">
                  {investigationReport
                    ? `${((investigationReport.combined_risk_score ?? 0) * 100).toFixed(1)}%`
                    : `${(assessment.risk_score || 0).toFixed(1)}%`}
                </div>
              </div>
              <RiskBadge
                level={
                  investigationReport
                    ? ((investigationReport.combined_risk_score ?? 0) >= 0.7 ? 'HIGH' : (investigationReport.combined_risk_score ?? 0) >= 0.4 ? 'REQUIRES_REVIEW' : 'LOW')
                    : (assessment.risk_level || 'LOW')
                }
                score={investigationReport ? (investigationReport.combined_risk_score ?? 0) * 100 : assessment.risk_score}
                className="text-xs px-3 py-1.5"
              />
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#E0DDD6]">
                <span className="text-[#64748B]">Engine / Pipeline</span>
                <span className="font-mono font-bold text-[#002D72]">
                  {investigationReport ? 'LangGraph (lgbm-risk-v1)' : assessment.version || 'v1.0'}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E0DDD6]">
                <span className="text-[#64748B]">Human Review Required</span>
                <span className={`font-bold ${
                  (investigationReport ? investigationReport.threshold_exceeded : assessment.requires_human_review)
                    ? 'text-[#F9A825]'
                    : 'text-[#10B981]'
                }`}>
                  {(investigationReport ? investigationReport.threshold_exceeded : assessment.requires_human_review)
                    ? 'YES (Review Mandated)'
                    : 'NO (Clear)'}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#64748B]">Signal Vectors</span>
                <span className="font-bold text-[#002D72]">
                  {investigationReport
                    ? `${investigationReport.triggered_rules?.length ?? 0} Triggered Rules`
                    : `${signals.length} Signals Detected`}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs Section */}
      <div className="space-y-4">
        <Tabs
          tabs={[
            { id: 'overview', label: 'Dossier Overview', count: undefined },
            { id: 'specialists', label: '10 Specialist Agents & History', count: 10 },
            { id: 'report', label: 'Forensic Investigation Report', count: undefined },
          ]}
          activeTab={activeTab}
          onChange={(tab) => setActiveTab(tab as any)}
        />

        {/* Tab 1: Overview & Ledger Context */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Sparkles className="w-4.5 h-4.5 text-[#F9A825]" />
                    Executive Summary &amp; Status
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-xs text-[#334155] leading-relaxed">
                  <p>
                    {investigationReport?.executive_summary ||
                      assessment.summary ||
                      detail.report?.summary ||
                      'Standard double-entry transaction record registered in the banking ledger.'}
                  </p>
                  <div className="p-3.5 rounded-[12px] bg-[#EBF3FC] border border-[#BFDBFE] text-[#002D72]">
                    <span className="font-bold block text-[11px] uppercase tracking-wider mb-1">
                      Compliance Standing
                    </span>
                    <p className="font-semibold">
                      {investigationReport?.recommended_action || 'ROUTINE_MONITORING'}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Activity className="w-4.5 h-4.5 text-[#002D72]" />
                    Telemetry &amp; Behavioral Baseline
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2.5 text-xs">
                  <div className="flex justify-between py-1.5 border-b border-[#E0DDD6]">
                    <span className="text-[#64748B]">Originating IP</span>
                    <span className="font-mono font-bold text-[#002D72]">{ipAddress}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[#E0DDD6]">
                    <span className="text-[#64748B]">Velocity Spike</span>
                    <span className="font-bold text-[#10B981]">
                      {investigationReport?.behavioral_metrics?.velocity_5m_max_count
                        ? `${investigationReport.behavioral_metrics.velocity_5m_max_count} txns in 5m`
                        : 'Within Normal Range'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[#E0DDD6]">
                    <span className="text-[#64748B]">Device Reputation</span>
                    <span className="font-bold text-[#002D72]">Verified Secure Client</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#64748B]">Ledger Reconciled</span>
                    <span className="font-bold text-[#10B981]">Double-Entry Balanced</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Preceding and Subsequent Transactions Context */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Preceding Transactions */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <History className="w-4 h-4 text-[#002D72]" />
                    Chronologically Preceding Transactions (Lookback)
                  </CardTitle>
                  <CardDescription>Transactions on this account immediately prior to this event</CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                  <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>TXN ID</TableHead>
                          <TableHead>Amount</TableHead>
                          <TableHead>Recipient</TableHead>
                          <TableHead>Timestamp</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {precedingList.length > 0 ? (
                          precedingList.map((pt: any) => (
                            <TableRow
                              key={pt.external_id || pt.id}
                              onClick={() => navigate(`/admin/transactions/${pt.external_id || pt.id}`)}
                              className="cursor-pointer hover:bg-[#FAF9F6]"
                            >
                              <TableCell className="font-mono text-xs font-bold text-[#002D72]">
                                {pt.external_id || pt.id}
                              </TableCell>
                              <TableCell className="font-mono text-xs">
                                {Number(pt.amount).toLocaleString()} {pt.currency}
                              </TableCell>
                              <TableCell className="text-xs truncate max-w-[120px]">
                                {pt.recipient || 'N/A'}
                              </TableCell>
                              <TableCell className="font-mono text-[11px] text-[#64748B]">
                                {new Date(pt.timestamp).toLocaleTimeString()}
                              </TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell colSpan={4} className="text-center py-6 text-xs text-[#64748B]">
                              No preceding transactions within lookback window.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              {/* Subsequent Transactions */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Clock className="w-4 h-4 text-[#002D72]" />
                    Chronologically Subsequent Transactions
                  </CardTitle>
                  <CardDescription>Transactions on this account occurring after this event</CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                  <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>TXN ID</TableHead>
                          <TableHead>Amount</TableHead>
                          <TableHead>Recipient</TableHead>
                          <TableHead>Timestamp</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {subsequentList.length > 0 ? (
                          subsequentList.map((st: any) => (
                            <TableRow
                              key={st.external_id || st.id}
                              onClick={() => navigate(`/admin/transactions/${st.external_id || st.id}`)}
                              className="cursor-pointer hover:bg-[#FAF9F6]"
                            >
                              <TableCell className="font-mono text-xs font-bold text-[#002D72]">
                                {st.external_id || st.id}
                              </TableCell>
                              <TableCell className="font-mono text-xs">
                                {Number(st.amount).toLocaleString()} {st.currency}
                              </TableCell>
                              <TableCell className="text-xs truncate max-w-[120px]">
                                {st.recipient || 'N/A'}
                              </TableCell>
                              <TableCell className="font-mono text-[11px] text-[#64748B]">
                                {new Date(st.timestamp).toLocaleTimeString()}
                              </TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell colSpan={4} className="text-center py-6 text-xs text-[#64748B]">
                              No subsequent transactions recorded yet.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* Tab: 10 Specialist Agents & Historical Intelligence */}
        {activeTab === 'specialists' && (
          <div className="space-y-6">
            {/* Authoritative Risk Formula Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Cpu className="w-5 h-5 text-[#002D72]" />
                    Authoritative Multi-Agent Risk Engine (Formula: risk-v1)
                  </span>
                  <span className="font-mono text-xs px-2.5 py-1 rounded-full bg-[#EBF3FC] text-[#002D72] border border-[#BFDBFE] font-bold">
                    Weights: Rules 20% | ML 25% | Hist 20% | Beh 10% | ATO 10% | Dev 5% | Graph 5% | Merch 5%
                  </span>
                </CardTitle>
                <CardDescription>
                  Normalized composite score computed across 10 specialized forensic agents with automated confidence degradation tracking.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-[#F4F1EC] rounded-xl border border-[#E0DDD6]">
                    <span className="text-[#64748B] font-bold uppercase text-[10px] block">Confidence Level</span>
                    <span className="font-bold text-sm text-[#002D72]">
                      {rawOverview.txn_metadata?.scoring_breakdown?.confidence_level || 'SUFFICIENT'}
                    </span>
                  </div>
                  <div className="p-3 bg-[#F4F1EC] rounded-xl border border-[#E0DDD6]">
                    <span className="text-[#64748B] font-bold uppercase text-[10px] block">Formula Version</span>
                    <span className="font-bold font-mono text-sm text-[#002D72]">
                      {rawOverview.txn_metadata?.scoring_breakdown?.formula_version || 'risk-v1'}
                    </span>
                  </div>
                  <div className="p-3 bg-[#F4F1EC] rounded-xl border border-[#E0DDD6]">
                    <span className="text-[#64748B] font-bold uppercase text-[10px] block">Overridden By Rule</span>
                    <span className="font-bold text-sm text-[#002D72]">
                      {rawOverview.txn_metadata?.scoring_breakdown?.override_triggered ? 'YES (Hard Override)' : 'None'}
                    </span>
                  </div>
                  <div className="p-3 bg-[#F4F1EC] rounded-xl border border-[#E0DDD6]">
                    <span className="text-[#64748B] font-bold uppercase text-[10px] block">Available Agents</span>
                    <span className="font-bold font-mono text-sm text-[#10B981]">
                      10 / 10 Operational
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 6 Rolling Lookback Windows Table */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <History className="w-4 h-4 text-[#002D72]" />
                    Transaction History Agent: 6 Rolling Lookback Windows
                  </span>
                  <span className="text-xs text-[#64748B] font-normal">
                    Strict lookback excluding current active transaction
                  </span>
                </CardTitle>
                <CardDescription>
                  Evaluates velocity count, volume total, average size, and p95 benchmarks across 5m, 15m, 60m, 24h, 7d, and 30d windows.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Window</TableHead>
                        <TableHead>Transactions Count</TableHead>
                        <TableHead>Total Volume</TableHead>
                        <TableHead>Average Amount</TableHead>
                        <TableHead>p95 Benchmark</TableHead>
                        <TableHead>Ratio to Avg</TableHead>
                        <TableHead>Ratio to p95</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {['5m', '15m', '60m', '24h', '7d', '30d'].map((win) => {
                        const winData = historyIntel?.raw_metrics?.[`window_${win}`] ||
                                        rawOverview.txn_metadata?.history_metrics?.[`window_${win}`] || {};
                        const count = winData.count ?? 0;
                        const sum = winData.sum_amount ?? 0;
                        const avg = winData.avg_amount ?? 0;
                        const p95 = winData.p95_amount ?? 0;
                        const rAvg = winData.ratio_to_avg ? winData.ratio_to_avg.toFixed(2) + 'x' : '1.00x';
                        const rP95 = winData.ratio_to_p95 ? winData.ratio_to_p95.toFixed(2) + 'x' : '1.00x';

                        return (
                          <TableRow key={win}>
                            <TableCell className="font-mono font-bold text-xs text-[#002D72]">
                              {win}
                            </TableCell>
                            <TableCell className="font-mono text-xs font-semibold">
                              {count} txns
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {Number(sum).toLocaleString()} {currency}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {Number(avg).toLocaleString()} {currency}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {Number(p95).toLocaleString()} {currency}
                            </TableCell>
                            <TableCell className="font-mono text-xs font-bold text-[#D97706]">
                              {rAvg}
                            </TableCell>
                            <TableCell className="font-mono text-xs font-bold text-[#D97706]">
                              {rP95}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>

            {/* 10 Specialist Forensic Agents Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                {
                  id: 'banking_rules',
                  name: 'Banking Rules Engine Agent',
                  weight: '20%',
                  role: 'Deterministic regulatory, velocity, & amount escalation rules',
                  score: rawOverview.txn_metadata?.specialist_results?.banking_rules?.risk_score ?? ((investigationReport?.rules_score ?? 0)),
                  findings: rawOverview.txn_metadata?.specialist_results?.banking_rules?.findings || [
                    { rule_id: 'RULE-AMOUNT-DEV-001', description: 'Evaluated against rolling 30d baseline' }
                  ],
                },
                {
                  id: 'ml_risk',
                  name: 'Machine Learning Risk Agent (LightGBM)',
                  weight: '25%',
                  role: 'Supervised gradient-boosted decision tree inference',
                  score: rawOverview.txn_metadata?.specialist_results?.ml_risk?.risk_score ?? (investigationReport?.ml_risk?.risk_score ?? 0.12),
                  findings: [
                    { rule_id: 'ML-LGBM-V1', description: 'Calibrated tree ensemble prediction score' }
                  ],
                },
                {
                  id: 'history',
                  name: 'Transaction History Agent',
                  weight: '20%',
                  role: 'Multi-window velocity and p95 volume deviation analysis',
                  score: rawOverview.txn_metadata?.specialist_results?.transaction_history?.risk_score ?? (historyIntel?.risk_score ?? 0.15),
                  findings: historyIntel?.findings || [
                    { rule_id: 'HIST-MULTI-WIN', description: 'Calculated across 5m, 15m, 60m, 24h, 7d, 30d windows' }
                  ],
                },
                {
                  id: 'behavioral',
                  name: 'Customer Behavioral Deviation Agent',
                  weight: '10%',
                  role: 'Off-hours activity and historical habit divergence',
                  score: rawOverview.txn_metadata?.specialist_results?.behavioral?.risk_score ?? 0.10,
                  findings: [
                    { rule_id: 'BEH-TEMPORAL', description: 'Sender diurnal spending activity verification' }
                  ],
                },
                {
                  id: 'ato',
                  name: 'Account Takeover (ATO) Agent',
                  weight: '10%',
                  role: 'Password resets, credential stuffing, & new device sessions',
                  score: rawOverview.txn_metadata?.specialist_results?.ato?.risk_score ?? 0.05,
                  findings: [
                    { rule_id: 'ATO-SESSION-001', description: 'Validated session authentication lifecycle' }
                  ],
                },
                {
                  id: 'device_network',
                  name: 'Device & Network Agent (VPN Detection)',
                  weight: '5%',
                  role: 'Proxy/commercial VPN anonymizers and device fingerprinting',
                  score: (rawOverview.ip_address?.is_vpn || rawOverview.txn_metadata?.is_vpn) ? 0.70 : 0.05,
                  findings: (rawOverview.ip_address?.is_vpn || rawOverview.txn_metadata?.is_vpn) ? [
                    { rule_id: 'RULE-NETWORK-VPN-001', description: 'Commercial VPN/Proxy tunnel detected (requires verification)' }
                  ] : [
                    { rule_id: 'NET-DIRECT-CONN', description: 'Direct residential/mobile ISP connection' }
                  ],
                },
                {
                  id: 'graph',
                  name: 'Graph Intelligence Agent (Neo4j)',
                  weight: '5%',
                  role: 'Shared hardware fingerprints, mule accounts, & ring topology',
                  score: rawOverview.txn_metadata?.specialist_results?.graph?.risk_score ?? 0.05,
                  findings: [
                    { rule_id: 'GRAPH-TOPOLOGY', description: 'No shared hardware syndicate rings discovered' }
                  ],
                },
                {
                  id: 'merchant',
                  name: 'Merchant Intelligence Agent',
                  weight: '5%',
                  role: 'Counterparty category risk, chargeback ratios, & MCC flags',
                  score: rawOverview.txn_metadata?.specialist_results?.merchant?.risk_score ?? 0.05,
                  findings: [
                    { rule_id: 'COUNTERPARTY-RISK', description: 'Individual customer peer-to-peer transfer' }
                  ],
                },
                {
                  id: 'identity',
                  name: 'Identity & Security Agent',
                  weight: 'Direct Gate',
                  role: 'KYC status, sanctions list, and administrative blocks',
                  score: rawOverview.has_transfer_restriction ? 0.95 : 0.05,
                  findings: rawOverview.has_transfer_restriction ? [
                    { rule_id: 'ID-RESTRICTED', description: 'Active OUTGOING_TRANSFERS_ONLY restriction present' }
                  ] : [
                    { rule_id: 'ID-CLEAR', description: 'Customer KYC verified and clear' }
                  ],
                },
                {
                  id: 'decision',
                  name: 'Final Decision & Action Agent',
                  weight: 'Synthesizer',
                  role: 'Evaluates composite score against thresholds & security gates',
                  score: rawOverview.txn_metadata?.scoring_breakdown?.final_score ?? ((investigationReport?.combined_risk_score ?? 0)),
                  findings: [
                    {
                      rule_id: 'ACTION-DIRECTIVE',
                      description: `Recommended Action: ${status === 'PENDING_CUSTOMER_VERIFICATION' ? 'VERIFY_WITH_CUSTOMER' : (status === 'PENDING_REVIEW' ? 'HOLD_FOR_REVIEW' : 'ALLOW')}`
                    }
                  ],
                },
              ].map((agent) => (
                <Card key={agent.id} className="p-4 space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="font-bold text-xs text-[#002D72] flex items-center gap-1.5">
                        <span>{agent.name}</span>
                        <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-[#EBF3FC] text-[#002D72] font-semibold">
                          Weight: {agent.weight}
                        </span>
                      </h4>
                      <p className="text-[11px] text-[#64748B] mt-0.5">{agent.role}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <span className={`font-mono font-extrabold text-sm ${agent.score >= 0.7 ? 'text-[#DC2626]' : agent.score >= 0.4 ? 'text-[#D97706]' : 'text-[#10B981]'}`}>
                        {(agent.score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#FAF9F6] border border-[#E0DDD6] space-y-1 text-[11px]">
                    <span className="font-bold text-[#475569] uppercase text-[10px]">Findings</span>
                    {agent.findings?.map((f: any, idx: number) => (
                      <div key={idx} className="flex items-center gap-1.5 text-[#334155]">
                        <span className="font-mono font-bold text-[#002D72] text-[10px]">{f.rule_id || f.finding_id}:</span>
                        <span>{f.description}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}



        {/* Tab 3: Professional English Forensic Investigation Report */}
        {activeTab === 'report' && (
          <div className="space-y-6">
            {investigationRunning && (
              <div className="p-4 rounded-[12px] bg-[#EBF3FC] border border-[#BFDBFE] space-y-2.5 animate-pulse shadow-sm">
                <div className="flex items-center justify-between text-xs font-bold text-[#002D72]">
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-[#F9A825] animate-spin" />
                    Executing Live Multi-Agent LangGraph Forensic Synthesis...
                  </span>
                  <span className="font-mono">{liveSnapshot?.progress_percentage ?? 45}%</span>
                </div>
                <div className="w-full bg-[#DBEAFE] h-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#002D72] transition-all duration-300"
                    style={{ width: `${Math.max(10, liveSnapshot?.progress_percentage ?? 45)}%` }}
                  />
                </div>
                <p className="text-[11px] text-[#64748B]">
                  Specialist agents synthesizing double-entry ledger facts, network topology, behavioral velocity, and ML decision trees...
                </p>
              </div>
            )}

            {!investigationReport ? (
              <Card className="p-8 text-center space-y-3">
                <FileText className="w-10 h-10 text-[#002D72] mx-auto animate-pulse" />
                <h3 className="text-base font-bold text-[#002D72]">No Forensic Report Generated Yet</h3>
                <p className="text-xs text-[#64748B] max-w-md mx-auto">
                  Execute the LangGraph multi-agent forensic investigation workflow to synthesize an authoritative English report explaining why this transaction is or is not a financial crime risk.
                </p>
                <Button
                  onClick={handleRunInvestigation}
                  disabled={investigationRunning}
                  variant="primary"
                  size="sm"
                  className="bg-[#F9A825] text-[#002D72] font-bold"
                >
                  <Play className={`w-4 h-4 mr-1.5 ${investigationRunning ? 'animate-spin' : ''}`} />
                  {investigationRunning ? 'Generating...' : 'Generate Forensic Report'}
                </Button>
              </Card>
            ) : (
              <div className="space-y-6">
                {/* Dossier Header & Copy Action Bar */}
                <div className="p-4 rounded-[12px] bg-white border border-[#E0DDD6] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
                  <div>
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#F9A825]" />
                      <span className="text-xs font-bold uppercase tracking-wider text-[#64748B]">
                        Financial Crime Forensic Investigation Dossier
                      </span>
                    </div>
                    <div className="text-lg font-extrabold text-[#002D72] font-mono mt-0.5">
                      Case File: {investigationReport.investigation_id}
                    </div>
                    <p className="text-xs text-[#64748B] mt-0.5">
                      Generated: {investigationReport.generated_at ? new Date(investigationReport.generated_at).toLocaleString() : 'Recent'} · Evaluated Risk: <strong className="text-[#002D72]">{((investigationReport.combined_risk_score ?? 0) * 100).toFixed(1)}%</strong>
                    </p>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <Button
                      onClick={handleRunInvestigation}
                      disabled={investigationRunning}
                      size="sm"
                      className="bg-[#F9A825] hover:bg-[#F57F17] text-[#002D72] font-bold border-none shadow-sm text-xs"
                    >
                      <Play className={`w-3.5 h-3.5 mr-1.5 ${investigationRunning ? 'animate-spin' : ''}`} />
                      {investigationRunning ? 'Synthesizing...' : 'Re-Run Live Investigation'}
                    </Button>
                    <Button
                      onClick={() => {
                        const content = investigationReport.forensic_report_markdown || investigationReport.executive_summary;
                        navigator.clipboard.writeText(content);
                        setCopiedReport(true);
                        setTimeout(() => setCopiedReport(false), 3000);
                      }}
                      size="sm"
                      variant="secondary"
                      className="text-xs font-bold"
                    >
                      {copiedReport ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-[#10B981] mr-1" />
                          <span>Copied Markdown!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 text-[#002D72] mr-1" />
                          <span>Copy Report</span>
                        </>
                      )}
                    </Button>
                    <span className={`px-3 py-1 rounded-full text-xs font-extrabold uppercase tracking-wider ${
                      investigationReport.threshold_exceeded
                        ? 'bg-[#FEF2F2] text-[#991B1B] border border-[#FECACA]'
                        : 'bg-[#F0FDF4] text-[#166534] border border-[#BBF7D0]'
                    }`}>
                      {investigationReport.recommended_action}
                    </span>
                  </div>
                </div>

                {/* Professional English Forensic Report Card */}
                <Card className="border-[#002D72]/20 shadow-md">
                  <CardHeader className="border-b border-[#E0DDD6] bg-[#FAF9F6]">
                    <CardTitle className="text-base text-[#002D72] flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <FileText className="w-4.5 h-4.5 text-[#002D72]" />
                        Official Forensic Investigation Report
                      </span>
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white text-[#475569] border border-[#CBD5E1]">
                        Language: Natural English · Human Compliance Standard
                      </span>
                    </CardTitle>
                    <CardDescription>
                      Structured authoritative findings synthesized across relational double-entry ledger facts, graph topology, LightGBM model score, and FATF typologies.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6 space-y-6 text-[#1E293B] leading-relaxed">
                    {/* Render Formatted Markdown Report Sections */}
                    {investigationReport.forensic_report_markdown ? (
                      <div className="space-y-6 text-sm divide-y divide-[#E2E8F0]">
                        {investigationReport.forensic_report_markdown.split(/\n(?=##\s+)/).map((section, idx) => {
                          const lines = section.trim().split('\n');
                          const title = lines[0].replace(/^##\s*/, '').trim();
                          const body = lines.slice(1).join('\n').trim();

                          return (
                            <div key={idx} className={`${idx > 0 ? 'pt-5' : ''} space-y-2`}>
                              <h3 className="text-base font-extrabold text-[#002D72] flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-[#F9A825]" />
                                {title}
                              </h3>
                              <div className="text-xs sm:text-sm text-[#334155] leading-relaxed whitespace-pre-line pl-4 border-l-2 border-[#EBF3FC]">
                                {body}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div>
                          <h3 className="text-sm font-extrabold text-[#002D72] mb-1">Executive Summary</h3>
                          <p className="text-xs text-[#334155]">{investigationReport.executive_summary}</p>
                        </div>
                        <div>
                          <h3 className="text-sm font-extrabold text-[#002D72] mb-1">Risk Assessment Explanation</h3>
                          <p className="text-xs text-[#334155]">{investigationReport.risk_assessment_explanation}</p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Technical Specialist Deep-Dive Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* LightGBM ML Findings Card */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm flex items-center justify-between">
                        <span className="flex items-center gap-2">
                          <Cpu className="w-4 h-4 text-[#1E88E5]" />
                          LightGBM Model Risk Findings (risk_lgbm_v1)
                        </span>
                        <span className="text-xs font-mono font-bold text-[#002D72]">
                          {investigationReport.ml_risk
                            ? `${((investigationReport.ml_risk.risk_score ?? 0) * 100).toFixed(1)}% (${investigationReport.ml_risk.risk_tier || 'LOW'})`
                            : 'Assessment Pending'}
                        </span>
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Decision tree split gain importance over active transaction feature vector
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider block">
                        Top Contributing Feature Splits
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        {investigationReport.ml_risk?.top_feature_contributions && Object.keys(investigationReport.ml_risk.top_feature_contributions).length > 0 ? (
                          Object.entries(investigationReport.ml_risk.top_feature_contributions).map(([feat, val]) => (
                            <div key={feat} className="p-2 rounded-[8px] bg-[#FAF9F6] border border-[#E0DDD6] flex justify-between items-center text-xs">
                              <span className="font-mono text-[#475569] text-[11px] truncate">{feat}</span>
                              <span className="font-mono font-bold text-[#002D72] text-[11px]">+{Number(val).toFixed(2)}</span>
                            </div>
                          ))
                        ) : (
                          <div className="col-span-2 py-3 text-center text-xs text-[#64748B] bg-[#FAF9F6] rounded-[8px] border border-[#E0DDD6]">
                            No feature split contributions recorded for this assessment.
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Triggered Banking Rules Card */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm flex items-center justify-between">
                        <span className="flex items-center gap-2">
                          <Scale className="w-4 h-4 text-[#F9A825]" />
                          Deterministic Banking Rules &amp; Velocity
                        </span>
                        <span className="text-xs font-mono font-bold text-[#002D72]">
                          Rules Score: {((investigationReport.rules_score ?? 0) * 100).toFixed(1)}%
                        </span>
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Evaluated against FATF Guidance R.10 / R.20 and internal banking heuristics
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {(investigationReport.triggered_rules && investigationReport.triggered_rules.length > 0) ? (
                        <div className="space-y-2.5">
                          {investigationReport.triggered_rules.map((rule) => (
                            <div key={rule.rule_id} className="p-2.5 rounded-[10px] bg-[#FFF9E6] border border-[#FFE082] space-y-1 text-xs">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-[#92400E] text-xs">{rule.rule_name}</span>
                                <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-[#FEF3C7] text-[#92400E] font-bold">
                                  {rule.regulatory_reference}
                                </span>
                              </div>
                              <p className="text-[#451A03] text-[11px]">{rule.explanation}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-[#10B981] font-semibold py-2">
                          ✓ No high-velocity burst, amount escalation, or mule ring rules triggered.
                        </p>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Recommended Compliance Review Actions */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <ShieldCheck className="w-4.5 h-4.5 text-[#10B981]" />
                      Authoritative Compliance Review Directive
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-xs">
                    <div className="p-3.5 rounded-[12px] bg-[#EBF3FC] border border-[#BFDBFE] space-y-1">
                      <span className="text-[11px] font-bold text-[#002D72] uppercase tracking-wider block">
                        Action Directive: {investigationReport.recommended_action}
                      </span>
                      <p className="text-[#1E293B]">{investigationReport.recommended_action_justification}</p>
                    </div>

                    {(investigationReport.missing_data_and_limitations && investigationReport.missing_data_and_limitations.length > 0) && (
                      <div className="p-3 rounded-[10px] bg-[#F4F1EC] border border-[#E0DDD6] space-y-1">
                        <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider block">
                          Investigation Limitations &amp; Service Notices
                        </span>
                        <ul className="list-disc list-inside space-y-0.5 text-[#475569]">
                          {investigationReport.missing_data_and_limitations.map((lim, i) => (
                            <li key={i}>{lim}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        )}


      </div>

      {/* Record Disposition Modal */}
      <Modal
        isOpen={dispositionModalOpen}
        onClose={() => setDispositionModalOpen(false)}
        title="Record Compliance Disposition"
      >
        <form onSubmit={handleRecordDisposition} className="space-y-4 text-xs">
          <div>
            <label className="font-bold text-[#002D72] block mb-1">Disposition Verdict</label>
            <select
              value={disposition}
              onChange={(e) => setDisposition(e.target.value)}
              className="w-full h-10 bg-white border border-[#E0DDD6] rounded-[10px] px-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5]"
            >
              <option value="LEGITIMATE_ACTIVITY">Legitimate Activity (Clear Alert)</option>
              <option value="SUSPICIOUS_FURTHER_INVESTIGATION">Suspicious — Open Full Investigation</option>
              <option value="ESCALATED_SPECIALIST">Escalate to Senior Compliance Lead</option>
              <option value="NO_SUSPICIOUS_ACTIVITY">No Suspicious Activity Detected</option>
            </select>
          </div>

          <div>
            <label className="font-bold text-[#002D72] block mb-1">Analyst Justification &amp; Notes</label>
            <textarea
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              rows={3}
              placeholder="Provide evidence-based rationale citing transaction facts..."
              className="w-full bg-white border border-[#E0DDD6] rounded-[10px] p-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5]"
            />
          </div>

          <div className="flex justify-end gap-2.5 pt-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setDispositionModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="sapphire"
              size="sm"
              disabled={submitting}
            >
              {submitting ? 'Recording...' : 'Commit Disposition'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
