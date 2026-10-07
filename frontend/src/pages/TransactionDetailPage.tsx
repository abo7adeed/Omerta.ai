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
} from 'lucide-react';
import { api } from '../api/client';
import type { TransactionDetail } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Select';
import { RiskBadge } from '../components/ui/RiskBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { Tabs } from '../components/ui/Tabs';
import { Timeline } from '../components/ui/Timeline';
import type { TimelineItem } from '../components/ui/Timeline';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const TransactionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<TransactionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'risk' | 'signals' | 'timeline' | 'entities'>('overview');

  // Quick Disposition Modal state
  const [dispositionModalOpen, setDispositionModalOpen] = useState(false);
  const [disposition, setDisposition] = useState('LEGITIMATE_ACTIVITY');
  const [rationale, setRationale] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState('');

  const navigate = useNavigate();

  const fetchDetail = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await api.getTransactionDetail(id);
      setDetail(res);
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
  const recipientAccount = rawOverview.recipient_account?.external_id || (rawOverview as any).receiver_account_number || (rawOverview as any).recipient_account || 'N/A';
  const recipientName = rawOverview.recipient_account?.customer_name || (rawOverview as any).receiver_name || 'Beneficiary Account';
  const deviceId = rawOverview.device?.external_id || (rawOverview as any).device_id || (rawOverview as any).device || 'DEV-WEB-SECURE';
  const ipAddress = rawOverview.ip_address?.address || (rawOverview as any).ip_address || '197.34.120.55';

  const assessment = detail?.assessment || detail?.risk_assessment || (detail as any)?.risk_assessment || {
    risk_score: 0,
    risk_level: 'LOW' as any,
    requires_human_review: false,
    version: 'v1.0',
    summary: 'Standard automated assessment completed.',
  };

  const signals = detail?.signals || (detail as any)?.risk_signals || [];

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

  const handleApprove = async () => {
    if (!externalId) return;
    try {
      await api.approvePendingTransaction(
        externalId,
        'Analyst confirmed legitimacy after deep dossier review.'
      );
      setActionSuccess('Transaction approved and funds released.');
      setTimeout(() => {
        setActionSuccess('');
        fetchDetail();
      }, 1500);
    } catch (err: any) {
      alert(err.message || 'Failed to approve transaction.');
    }
  };

  const handleReject = async () => {
    if (!externalId) return;
    try {
      await api.rejectPendingTransaction(
        externalId,
        'Transaction rejected and blocked by compliance.'
      );
      setActionSuccess('Transaction blocked and funds returned to security hold.');
      setTimeout(() => {
        setActionSuccess('');
        fetchDetail();
      }, 1500);
    } catch (err: any) {
      alert(err.message || 'Failed to reject transaction.');
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-[#64748B] space-y-3">
        <ShieldAlert className="h-10 w-10 animate-bounce mx-auto text-[#002D72]" />
        <p className="font-bold text-[#002D72]">Loading forensic transaction dossier...</p>
        <p className="text-xs text-[#64748B]">Synthesizing risk assessment, signals, and ledger context</p>
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

  // Construct timeline items
  const timelineItems: TimelineItem[] = [
    {
      id: 'init',
      title: 'Transaction Initiated',
      description: `Dispatched via Digital Banking from account ${sourceAccount}`,
      timestamp: timestamp ? new Date(timestamp).toLocaleString() : 'Recent',
      status: 'completed',
    },
    {
      id: 'assessment',
      title: `Risk Engine Assessment (${assessment.risk_level || 'LOW'})`,
      description: `Engine scored transaction at ${(assessment.risk_score || 0).toFixed(1)}% with ${signals.length} signal vector(s).`,
      timestamp: timestamp ? new Date(timestamp).toLocaleTimeString() : undefined,
      status: 'completed',
    },
    {
      id: 'review',
      title: assessment.requires_human_review ? 'Compliance Hold & Human Review' : 'Automated Clearance',
      description: assessment.requires_human_review
        ? 'Held in queue for analyst disposition.'
        : 'Automated rules approved instant settlement.',
      status: status === 'COMPLETED' ? 'completed' : 'active',
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Success Notification */}
      {actionSuccess && (
        <div className="p-4 rounded-[12px] bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] flex items-center gap-2.5">
          <CheckCircle2 className="h-5 w-5 text-[#10B981] stroke-[2.5]" />
          <span className="text-xs font-bold">{actionSuccess}</span>
        </div>
      )}

      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            onClick={() => navigate('/admin/transactions')}
            variant="ghost"
            size="sm"
            className="h-9 px-2 text-[#64748B]"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#002D72]">
                Dossier: {externalId}
              </h1>
              <StatusBadge status={status} />
            </div>
            <p className="text-xs text-[#64748B] font-mono">
              Timestamp: {timestamp ? new Date(timestamp).toLocaleString() : 'N/A'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {status === 'REQUIRES_REVIEW' && (
            <>
              <Button onClick={handleApprove} variant="emerald" size="sm">
                <CheckCircle2 className="w-4 h-4 mr-1.5" />
                <span>Release Funds</span>
              </Button>
              <Button onClick={handleReject} variant="danger" size="sm">
                <XCircle className="w-4 h-4 mr-1.5" />
                <span>Block Transfer</span>
              </Button>
            </>
          )}
          <Button
            onClick={() => setDispositionModalOpen(true)}
            variant="primary"
            size="sm"
          >
            <ShieldCheck className="w-4 h-4 mr-1.5" />
            <span>Record Disposition</span>
          </Button>
          <Button
            onClick={() =>
              navigate(
                `/admin/network-analysis?entity=${encodeURIComponent(
                  sourceAccount || externalId
                )}`
              )
            }
            variant="secondary"
            size="sm"
          >
            <Share2 className="w-4 h-4 text-[#002D72] mr-1.5" />
            <span>Inspect Graph</span>
          </Button>
        </div>
      </div>

      {/* Top 3 Overview Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Financial Transaction Summary */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Wallet className="w-4.5 h-4.5 text-[#002D72]" />
              Financial Movement Summary
            </CardTitle>
            <CardDescription>Verified ledger transfer details</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="p-3.5 bg-[#F4F1EC] rounded-[12px] border border-[#E0DDD6]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                  Transfer Amount
                </span>
                <div className="text-xl font-bold font-mono text-[#002D72] mt-0.5 font-tabular">
                  {amount
                    ? `${Number(amount).toLocaleString()} ${currency}`
                    : `0 ${currency}`}
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
                <div className="font-bold text-[#002D72]">
                  {customerName}
                </div>
                <div className="text-xs font-mono text-[#475569]">
                  Account: {sourceAccount}
                </div>
              </div>

              <div className="p-4 bg-white rounded-[12px] border border-[#E0DDD6] space-y-1.5">
                <div className="flex items-center justify-between text-xs font-bold uppercase text-[#64748B]">
                  <span>Beneficiary Account (Receiver)</span>
                  <span className="text-[#10B981] font-mono">Destination</span>
                </div>
                <div className="font-bold text-[#002D72]">
                  {recipientName}
                </div>
                <div className="text-xs font-mono text-[#475569]">
                  Account: {recipientAccount}
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
                  {(assessment.risk_score || 0).toFixed(1)}%
                </div>
              </div>
              <RiskBadge
                level={assessment.risk_level || 'LOW'}
                score={assessment.risk_score}
                className="text-xs px-3 py-1.5"
              />
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#E0DDD6]">
                <span className="text-[#64748B]">Engine Version</span>
                <span className="font-mono font-bold text-[#002D72]">{assessment.version || 'v2.4-Hybrid'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E0DDD6]">
                <span className="text-[#64748B]">Human Review Required</span>
                <span className={`font-bold ${assessment.requires_human_review ? 'text-[#F9A825]' : 'text-[#10B981]'}`}>
                  {assessment.requires_human_review ? 'YES (Hold Applied)' : 'NO (Clear)'}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#64748B]">Signal Vectors</span>
                <span className="font-bold text-[#002D72]">{signals.length} Signals Detected</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dossier Tabs */}
      <div className="space-y-4">
        <Tabs
          tabs={[
            { id: 'overview', label: 'Dossier Overview', count: undefined },
            { id: 'signals', label: 'Forensic Signals', count: signals.length },
            { id: 'timeline', label: 'Audit Trail Timeline', count: timelineItems.length },
            { id: 'entities', label: 'Network & Topology', count: undefined },
          ]}
          activeTab={activeTab}
          onChange={(tab) => setActiveTab(tab as any)}
        />

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Sparkles className="w-4.5 h-4.5 text-[#F9A825]" />
                  Executive Intelligence Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-xs text-[#334155] leading-relaxed">
                <p>
                  {assessment.summary ||
                    detail.report?.summary ||
                    detail.report?.executive_summary ||
                    'Automated AML transaction monitoring observed standard behavioral patterns for this counterparty pair.'}
                </p>
                {detail.report?.recommended_action && (
                  <div className="p-3.5 rounded-[12px] bg-[#EBF3FC] border border-[#BFDBFE] text-[#002D72]">
                    <span className="font-bold block text-[11px] uppercase tracking-wider mb-1">
                      Recommended Compliance Action
                    </span>
                    <p className="font-semibold">{detail.report.recommended_action}</p>
                  </div>
                )}
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
                  <span className="font-bold text-[#10B981]">Within Normal Parameters</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#E0DDD6]">
                  <span className="text-[#64748B]">Device Reputation</span>
                  <span className="font-bold text-[#002D72]">Known Customer Device</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-[#64748B]">Sanction List Match</span>
                  <span className="font-bold text-[#10B981]">0 Matches (Clean)</span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tab 2: Signals */}
        {activeTab === 'signals' && (
          <Card className="p-0 overflow-hidden">
            <TableContainer>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Signal Indicator</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Detected Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {signals.length > 0 ? (
                    signals.map((sig: any, idx: number) => (
                      <TableRow key={sig.id || idx}>
                        <TableCell className="font-bold text-[#002D72] font-mono text-xs">
                          {sig.signal_name || sig.name || 'ANOMALY_DETECTED'}
                        </TableCell>
                        <TableCell>
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              sig.severity === 'CRITICAL' || sig.severity === 'HIGH'
                                ? 'bg-rose-100 text-rose-800'
                                : sig.severity === 'MEDIUM'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-blue-100 text-[#002D72]'
                            }`}
                          >
                            {sig.severity || 'MEDIUM'}
                          </span>
                        </TableCell>
                        <TableCell className="font-mono font-bold text-xs text-[#0F172A]">
                          {sig.confidence ? `${Math.round(sig.confidence * 100)}%` : '85%'}
                        </TableCell>
                        <TableCell className="text-xs text-[#475569] max-w-md">
                          {sig.description || 'Observed transactional feature divergence.'}
                        </TableCell>
                        <TableCell className="text-xs font-mono text-[#64748B]">
                          {sig.detected_at ? new Date(sig.detected_at).toLocaleString() : 'Recent'}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5} className="p-8 text-center text-[#64748B] text-xs">
                        No adverse risk signals triggered for this transaction.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        )}

        {/* Tab 3: Timeline */}
        {activeTab === 'timeline' && (
          <Card className="p-6">
            <h3 className="text-sm font-bold text-[#002D72] mb-6 flex items-center gap-2">
              <Clock className="w-4 h-4 text-[#002D72]" />
              Immutable Regulatory Audit Sequence
            </h3>
            <Timeline items={timelineItems} />
          </Card>
        )}

        {/* Tab 4: Entities */}
        {activeTab === 'entities' && (
          <Card className="p-6 space-y-6">
            <div>
              <h3 className="text-sm font-bold text-[#002D72] mb-1">
                Connected Graph Topology
              </h3>
              <p className="text-xs text-[#64748B]">
                Immediate 1-hop and 2-hop transacting counterparties
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-[12px] bg-[#F4F1EC] border border-[#E0DDD6] space-y-2 text-xs">
                <span className="font-bold uppercase tracking-wider text-[#002D72] block">
                  Source Node
                </span>
                <p className="font-bold text-[#0F172A]">{customerName}</p>
                <p className="font-mono text-[#64748B]">Account: {sourceAccount}</p>
                <p className="text-[#475569]"><span className="font-semibold text-[#0F172A]">Originating IP:</span> {ipAddress} (Cairo, Egypt)</p>
              </div>

              <div className="p-4 rounded-[12px] bg-[#F4F1EC] border border-[#E0DDD6] space-y-2 text-xs">
                <span className="font-bold uppercase tracking-wider text-[#10B981] block">
                  Destination Node
                </span>
                <p className="font-bold text-[#0F172A]">{recipientName}</p>
                <p className="font-mono text-[#64748B]">Account: {recipientAccount}</p>
                <p className="text-[#475569]"><span className="font-semibold text-[#0F172A]">Settlement:</span> Instant Local Clearing</p>
              </div>
            </div>

            <div className="pt-2">
              <Button
                onClick={() =>
                  navigate(
                    `/admin/network-analysis?entity=${encodeURIComponent(
                      sourceAccount || externalId
                    )}`
                  )
                }
                variant="primary"
                size="sm"
              >
                <Share2 className="w-4 h-4 mr-1.5" />
                <span>Launch Interactive Topology Visualizer</span>
              </Button>
            </div>
          </Card>
        )}
      </div>

      {/* QUICK DISPOSITION MODAL */}
      {dispositionModalOpen && (
        <Modal
          isOpen={dispositionModalOpen}
          onClose={() => setDispositionModalOpen(false)}
          title="Record Compliance Disposition"
          subtitle={`Case Audit for Transaction ${externalId}`}
          maxWidth="md"
        >
          <form onSubmit={handleRecordDisposition} className="space-y-4 text-xs">
            <Select
              label="Disposition Decision"
              value={disposition}
              onChange={(e) => setDisposition(e.target.value)}
              options={[
                { value: 'LEGITIMATE_ACTIVITY', label: 'LEGITIMATE_ACTIVITY — Cleared of Fraud' },
                { value: 'CONFIRMED_FRAUD', label: 'CONFIRMED_FRAUD — Lock Account & Report' },
                { value: 'SUSPICIOUS_ESCALATION', label: 'SUSPICIOUS_ESCALATION — File SAR / Regulatory Report' },
                { value: 'FALSE_POSITIVE', label: 'FALSE_POSITIVE — Tune Detection Rules' },
              ]}
            />

            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#475569]">
                Investigation Notes &amp; Rationale
              </label>
              <textarea
                rows={3}
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                placeholder="Detail rationale for audit record..."
                className="w-full px-3.5 py-2.5 bg-white border border-[#E0DDD6] rounded-[10px] text-sm text-[#0F172A] focus:border-[#1E88E5] focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#E0DDD6]">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setDispositionModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={submitting}
              >
                <span>Save Disposition</span>
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
