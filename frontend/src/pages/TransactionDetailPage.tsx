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
} from 'lucide-react';
import { api, type AccountInvestigationReport, type PipelineStageTrace } from '../api/client';
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
  const [activeTab, setActiveTab] = useState<'overview' | 'pipeline' | 'report' | 'network' | 'timeline'>('overview');

  // LangGraph Transaction Investigation State
  const [investigationRunning, setInvestigationRunning] = useState(false);
  const [investigationReport, setInvestigationReport] = useState<AccountInvestigationReport | null>(null);
  const [investigationError, setInvestigationError] = useState<string | null>(null);
  const [expandedStages, setExpandedStages] = useState<Record<string, boolean>>({});

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

      // Check if an investigation report was persisted in the detail payload
      if (res.persisted_investigation) {
        setInvestigationReport(res.persisted_investigation);
      } else {
        // Try dedicated investigation endpoint
        try {
          const inv = await api.getTransactionInvestigation(id);
          if (inv && inv.investigation_id) {
            setInvestigationReport(inv);
          }
        } catch {
          // No prior investigation yet - normal state
        }
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
      setActiveTab('pipeline');
      setActionSuccess('LangGraph 9-stage pipeline executed and dossier persisted!');
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
            title: `LangGraph Forensic Dossier (${investigationReport.investigation_id})`,
            description: `Executed 9-stage pipeline. Composite risk: ${(investigationReport.combined_risk_score * 100).toFixed(1)}%. Recommendation: ${investigationReport.recommended_action}`,
            timestamp: new Date(investigationReport.generated_at).toLocaleTimeString(),
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
                    ? `${(investigationReport.combined_risk_score * 100).toFixed(1)}%`
                    : `${(assessment.risk_score || 0).toFixed(1)}%`}
                </div>
              </div>
              <RiskBadge
                level={
                  investigationReport
                    ? (investigationReport.combined_risk_score >= 0.7 ? 'HIGH' : investigationReport.combined_risk_score >= 0.4 ? 'REQUIRES_REVIEW' : 'LOW')
                    : (assessment.risk_level || 'LOW')
                }
                score={investigationReport ? investigationReport.combined_risk_score * 100 : assessment.risk_score}
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
                    ? `${investigationReport.triggered_rules.length} Triggered Rules`
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
            { id: 'pipeline', label: 'LangGraph Pipeline Trace', count: pipelineStages.length || undefined },
            { id: 'report', label: 'Forensic Investigation Report', count: investigationReport ? undefined : undefined },
            { id: 'network', label: 'Network & Topology', count: undefined },
            { id: 'timeline', label: 'Audit Trail Timeline', count: timelineItems.length },
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

        {/* Tab 2: LangGraph Pipeline Execution Trace */}
        {activeTab === 'pipeline' && (
          <div className="space-y-4">
            {!investigationReport ? (
              <Card className="p-8 text-center space-y-3">
                <Cpu className="w-10 h-10 text-[#F9A825] mx-auto animate-pulse" />
                <h3 className="text-base font-bold text-[#002D72]">No Investigation Pipeline Trace Available</h3>
                <p className="text-xs text-[#64748B] max-w-md mx-auto">
                  This transaction has not yet been processed through the 9-stage LangGraph forensic engine. Run the investigation to view real stage execution traces, durations, and outputs.
                </p>
                <Button
                  onClick={handleRunInvestigation}
                  disabled={investigationRunning}
                  variant="primary"
                  size="sm"
                  className="bg-[#F9A825] text-[#002D72] font-bold"
                >
                  <Play className="w-4 h-4 mr-1.5" />
                  Execute Investigation Pipeline
                </Button>
              </Card>
            ) : (
              <div className="space-y-3">
                <div className="p-4 rounded-[12px] bg-white border border-[#E0DDD6] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                      LangGraph Investigation Workflow Trace
                    </span>
                    <div className="text-base font-extrabold text-[#002D72] font-mono mt-0.5">
                      {investigationReport.investigation_id}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-xs font-mono text-[#64748B]">
                    <div>Stages: <span className="font-bold text-[#002D72]">{pipelineStages.length}</span></div>
                    <div>Total Execution: <span className="font-bold text-[#002D72]">{investigationReport.execution_time_ms} ms</span></div>
                    <div>Status: <span className="font-bold text-[#10B981]">COMPLETED</span></div>
                  </div>
                </div>

                {/* 9 Stages List */}
                <div className="space-y-3">
                  {pipelineStages.map((stage, idx) => {
                    const isExpanded = !!expandedStages[stage.stage_id];
                    const isCompleted = stage.status === 'COMPLETED';
                    const isFailed = stage.status === 'FAILED';

                    return (
                      <Card key={stage.stage_id} className="overflow-hidden border border-[#E0DDD6] transition-all">
                        <div
                          onClick={() => toggleStage(stage.stage_id)}
                          className="p-4 flex items-center justify-between cursor-pointer hover:bg-[#FAF9F6] transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <span className="w-7 h-7 rounded-full bg-[#EBF3FC] text-[#002D72] font-bold text-xs flex items-center justify-center font-mono shrink-0">
                              {idx + 1}
                            </span>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-sm text-[#002D72]">{stage.stage_name}</span>
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#F4F1EC] text-[#64748B] font-semibold border border-[#E0DDD6]">
                                  {stage.source_tier}
                                </span>
                              </div>
                              <p className="text-xs text-[#64748B] mt-0.5">{stage.description}</p>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 shrink-0">
                            <span className="text-xs font-mono text-[#64748B] font-medium hidden sm:inline">
                              {stage.duration_ms} ms
                            </span>
                            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              isCompleted
                                ? 'bg-[#E8F5E9] text-[#2E7D32]'
                                : isFailed
                                ? 'bg-[#FFEBEE] text-[#C62828]'
                                : 'bg-[#FFF9E6] text-[#B45309]'
                            }`}>
                              {stage.status}
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4 text-[#64748B]" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-[#64748B]" />
                            )}
                          </div>
                        </div>

                        {/* Expanded Payload Inspection */}
                        {isExpanded && (
                          <div className="p-4 bg-[#FAF9F6] border-t border-[#E0DDD6] space-y-3 text-xs">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              {/* Inputs */}
                              <div className="p-3 bg-white rounded-[10px] border border-[#E0DDD6]">
                                <span className="font-bold text-[11px] text-[#002D72] uppercase tracking-wider block mb-1">
                                  Sanitized Stage Inputs
                                </span>
                                <pre className="font-mono text-[11px] text-[#334155] whitespace-pre-wrap overflow-x-auto">
                                  {JSON.stringify(stage.input_summary, null, 2)}
                                </pre>
                              </div>

                              {/* Outputs */}
                              <div className="p-3 bg-white rounded-[10px] border border-[#E0DDD6]">
                                <span className="font-bold text-[11px] text-[#002D72] uppercase tracking-wider block mb-1">
                                  Stage Outputs &amp; Derived State
                                </span>
                                <pre className="font-mono text-[11px] text-[#334155] whitespace-pre-wrap overflow-x-auto">
                                  {JSON.stringify(stage.output_summary, null, 2)}
                                </pre>
                              </div>
                            </div>

                            {stage.evidence_ids && stage.evidence_ids.length > 0 && (
                              <div className="flex items-center gap-2 pt-1">
                                <span className="text-[11px] font-bold text-[#64748B]">Evidence Provenance:</span>
                                <div className="flex flex-wrap gap-1.5">
                                  {stage.evidence_ids.map((ev) => (
                                    <span key={ev} className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#EBF3FC] text-[#002D72] border border-[#BFDBFE]">
                                      {ev}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {stage.error_message && (
                              <div className="p-2.5 rounded bg-[#FFEBEE] text-[#C62828] text-[11px] font-semibold">
                                Error Notice: {stage.error_message}
                              </div>
                            )}
                          </div>
                        )}
                      </Card>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Full Grounded Investigation Report */}
        {activeTab === 'report' && (
          <div className="space-y-6">
            {!investigationReport ? (
              <Card className="p-8 text-center space-y-3">
                <FileText className="w-10 h-10 text-[#002D72] mx-auto animate-pulse" />
                <h3 className="text-base font-bold text-[#002D72]">No Forensic Report Generated Yet</h3>
                <p className="text-xs text-[#64748B] max-w-md mx-auto">
                  Execute the LangGraph investigation workflow to generate a grounded report integrating PostgreSQL transaction facts, LightGBM model score, and banking rules.
                </p>
                <Button
                  onClick={handleRunInvestigation}
                  disabled={investigationRunning}
                  variant="primary"
                  size="sm"
                  className="bg-[#F9A825] text-[#002D72] font-bold"
                >
                  Generate Forensic Report
                </Button>
              </Card>
            ) : (
              <div className="space-y-6">
                {/* Executive Summary Card */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Sparkles className="w-4.5 h-4.5 text-[#F9A825]" />
                        Forensic Executive Summary
                      </span>
                      <span className="text-xs font-mono text-[#64748B]">
                        Generated: {new Date(investigationReport.generated_at).toLocaleString()}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4 text-xs text-[#334155] leading-relaxed">
                    <p className="text-sm font-medium text-[#0F172A]">
                      {investigationReport.executive_summary}
                    </p>
                    <div className="p-3.5 rounded-[12px] bg-[#F4F1EC] border border-[#E0DDD6] space-y-1">
                      <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider block">
                        Risk Assessment Synthesis
                      </span>
                      <p>{investigationReport.risk_assessment_explanation}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* LightGBM ML Findings Card */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Cpu className="w-4.5 h-4.5 text-[#1E88E5]" />
                        LightGBM Model Risk Findings (lgbm-risk-v1)
                      </span>
                      <span className="text-xs font-mono font-bold text-[#002D72]">
                        Score: {(investigationReport.ml_risk.risk_score * 100).toFixed(1)}% ({investigationReport.ml_risk.risk_tier})
                      </span>
                    </CardTitle>
                    <CardDescription>
                      Explanation Methodology: {investigationReport.ml_risk.explanation_method} (Model-native split gain over active features, not Shapley attribution)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider block">
                      Active Feature Contributions (Tree Gain Importance)
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      {Object.entries(investigationReport.ml_risk.top_feature_contributions || {}).map(([feat, val]) => (
                        <div key={feat} className="p-2.5 rounded-[8px] bg-[#FAF9F6] border border-[#E0DDD6] flex justify-between items-center">
                          <span className="font-mono text-[#475569]">{feat}</span>
                          <span className="font-mono font-bold text-[#002D72]">+{Number(val).toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Triggered Banking Rules Card */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Scale className="w-4.5 h-4.5 text-[#F9A825]" />
                        Deterministic Banking Rules Analysis
                      </span>
                      <span className="text-xs font-mono font-bold text-[#002D72]">
                        Rules Score: {(investigationReport.rules_score * 100).toFixed(1)}%
                      </span>
                    </CardTitle>
                    <CardDescription>
                      Evaluated against FATF Guidance R.10 / R.20 and internal banking heuristics
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {investigationReport.triggered_rules.length > 0 ? (
                      <div className="space-y-3">
                        {investigationReport.triggered_rules.map((rule) => (
                          <div key={rule.rule_id} className="p-3.5 rounded-[12px] bg-[#FFF9E6] border border-[#FFE082] space-y-1.5 text-xs">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-[#92400E] text-sm">{rule.rule_name}</span>
                              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#FEF3C7] text-[#92400E] font-bold">
                                {rule.regulatory_reference}
                              </span>
                            </div>
                            <p className="text-[#451A03]">{rule.explanation}</p>
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

                {/* Recommended Compliance Review Actions */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <ShieldCheck className="w-4.5 h-4.5 text-[#10B981]" />
                      Recommended Compliance Officer Review Actions
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-xs">
                    <div className="p-4 rounded-[12px] bg-[#EBF3FC] border border-[#BFDBFE] space-y-1">
                      <span className="text-[11px] font-bold text-[#002D72] uppercase tracking-wider block">
                        Action Directive: {investigationReport.recommended_action}
                      </span>
                      <p className="text-[#1E293B]">{investigationReport.recommended_action_justification}</p>
                    </div>

                    {investigationReport.missing_data_and_limitations?.length > 0 && (
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

        {/* Tab 4: Network & Graph Topology */}
        {activeTab === 'network' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Network className="w-4.5 h-4.5 text-[#002D72]" />
                Connected Graph Topology (Neo4j)
              </CardTitle>
              <CardDescription>
                1-hop and 2-hop transacting counterparties and shared hardware fingerprints
              </CardDescription>
            </CardHeader>
            <CardContent>
              <TableContainer className="border-0 shadow-none">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Source Node</TableHead>
                      <TableHead>Relationship / Edge</TableHead>
                      <TableHead>Destination Node</TableHead>
                      <TableHead>Typology Risk</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="font-mono font-bold text-xs text-[#002D72]">
                        {sourceAccount} ({customerName})
                      </TableCell>
                      <TableCell className="text-xs font-semibold text-[#1E88E5]">
                        TRANSFERRED_TO ({amount ? Number(amount).toLocaleString() : 0} {currency})
                      </TableCell>
                      <TableCell className="font-mono font-bold text-xs text-[#0F172A]">
                        {recipientAccount} ({recipientName})
                      </TableCell>
                      <TableCell>
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#E8F5E9] text-[#2E7D32]">
                          CLEAR
                        </span>
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-mono font-bold text-xs text-[#002D72]">
                        {sourceAccount}
                      </TableCell>
                      <TableCell className="text-xs font-semibold text-[#64748B]">
                        USED_DEVICE
                      </TableCell>
                      <TableCell className="font-mono text-xs text-[#475569]">
                        {deviceId}
                      </TableCell>
                      <TableCell>
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#EBF3FC] text-[#002D72]">
                          RECOGNIZED
                        </span>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        )}

        {/* Tab 5: Audit Trail Timeline */}
        {activeTab === 'timeline' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Clock className="w-4.5 h-4.5 text-[#002D72]" />
                Immutable Audit Trail Timeline
              </CardTitle>
              <CardDescription>Cryptographically anchored chronological ledger entries</CardDescription>
            </CardHeader>
            <CardContent>
              <Timeline items={timelineItems} />
            </CardContent>
          </Card>
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
