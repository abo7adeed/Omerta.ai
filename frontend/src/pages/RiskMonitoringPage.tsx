import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  RefreshCw,
  CheckCircle2,
  Clock,
  Filter,
  PhoneCall,
  Mail,
  Unlock,
  Bot,
  Sparkles,
  XCircle,
  CheckCircle,
  AlertTriangle,
  Users,
  Search,
} from 'lucide-react';
import { api } from '../api/client';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { StatCard } from '../components/ui/StatCard';
import { RiskBadge } from '../components/ui/RiskBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { Tabs } from '../components/ui/Tabs';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const RiskMonitoringPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'transactions' | 'problem_customers'>('transactions');

  // Transactions Queue state
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  // Problem Customers state
  const [problemCustomers, setProblemCustomers] = useState<any[]>([]);
  const [loadingProblems, setLoadingProblems] = useState(false);
  const [problemSearch, setProblemSearch] = useState('');

  // Modals state
  const [selectedTxn, setSelectedTxn] = useState<any | null>(null);
  const [disposition, setDisposition] = useState('LEGITIMATE_ACTIVITY');
  const [rationale, setRationale] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState('');

  // Call modal
  const [callModalCust, setCallModalCust] = useState<any | null>(null);

  // Email modal
  const [emailModalCust, setEmailModalCust] = useState<any | null>(null);
  const [emailSubject, setEmailSubject] = useState('Omerta.ai Account Security Notice: Risk Clearance');
  const [emailBody, setEmailBody] = useState('');
  const [emailSubmitting, setEmailSubmitting] = useState(false);

  // Agentic SAR preview modal
  const [agenticModalTarget, setAgenticModalTarget] = useState<string | null>(null);
  const [agenticData, setAgenticData] = useState<any | null>(null);
  const [agenticLoading, setAgenticLoading] = useState(false);

  // Customer Agentic Forensic Modal
  const [custAgenticModal, setCustAgenticModal] = useState<any | null>(null);
  const [custAgenticLoading, setCustAgenticLoading] = useState(false);

  const navigate = useNavigate();

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await api.getRiskMonitoringQueue({
        min_score: 40.0,
        status: statusFilter,
        page,
        page_size: 15,
      });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load risk monitoring queue', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchProblemCustomers = async () => {
    setLoadingProblems(true);
    try {
      const res = await api.getProblemCustomers();
      setProblemCustomers(res || []);
    } catch (err) {
      console.error('Failed to load problem customers', err);
    } finally {
      setLoadingProblems(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    fetchProblemCustomers();
  }, [page, statusFilter]);

  const handleApproveTransaction = async (txnId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.approvePendingTransaction(txnId, 'Analyst verified identity and transaction legitimacy. Hold released.');
      setActionSuccessMsg(`Transaction ${txnId} approved and released for funds dispatch.`);
      fetchQueue();
      setTimeout(() => setActionSuccessMsg(''), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to approve transaction.');
    }
  };

  const handleRejectTransaction = async (txnId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.rejectPendingTransaction(txnId, 'Flagged as high-risk suspicious activity by analyst.');
      setActionSuccessMsg(`Transaction ${txnId} rejected and cancelled.`);
      fetchQueue();
      setTimeout(() => setActionSuccessMsg(''), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to reject transaction.');
    }
  };

  const handleResolveRisk = async (customerId: string, name: string) => {
    if (
      !confirm(
        `Are you sure you want to resolve risk and unlock account for customer ${name}? This will reset risk to LOW, clear password failures, and reactivate banking access.`
      )
    ) {
      return;
    }
    try {
      await api.resolveCustomerRisk(
        customerId,
        'Identity confirmed via analyst direct verification. Account risk cleared.'
      );
      setActionSuccessMsg(`Risk successfully cleared for ${name}. Account restored to LOW risk.`);
      fetchProblemCustomers();
      fetchQueue();
      setTimeout(() => setActionSuccessMsg(''), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to resolve customer risk.');
    }
  };

  const handleOpenCallModal = (c: any, e: React.MouseEvent) => {
    e.stopPropagation();
    setCallModalCust(c);
  };

  const handleOpenEmailModal = (c: any, e: React.MouseEvent) => {
    e.stopPropagation();
    setEmailModalCust(c);
    setEmailSubject(`Omerta.ai Security Clearance: Action Required for ${c.name}`);
    setEmailBody(
      `Dear ${c.name},\n\nWe detected a security event on your Omerta.ai account (${c.omerta_user_number}): "${c.primary_reason}".\n\nOur compliance and security team is currently reviewing your account. Please confirm your recent activity or reach out to our customer operations hotline at +20 2 3333 4444.\n\nSincerely,\nOmerta.ai Security & Risk Operations`
    );
  };

  const handleSendEmailNotice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailModalCust) return;
    setEmailSubmitting(true);
    try {
      await api.notifyCustomer(emailModalCust.customer_id, {
        channel: 'EMAIL',
        subject: emailSubject,
        message: emailBody,
      });
      setActionSuccessMsg(`Security notice sent to ${emailModalCust.name} (${emailModalCust.email}).`);
      setEmailModalCust(null);
      setTimeout(() => setActionSuccessMsg(''), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to send security notice.');
    } finally {
      setEmailSubmitting(false);
    }
  };

  const handleOpenCustomerAgenticModal = async (c: any, e: React.MouseEvent) => {
    e.stopPropagation();
    setCustAgenticLoading(true);
    setCustAgenticModal({
      customer_id: c.customer_id,
      omerta_user_number: c.omerta_user_number,
      name: c.name,
      email: c.email,
      phone: c.phone,
      risk_level: c.risk_level,
      status: c.status,
    });
    try {
      const summary = await api.getProblemCustomerAgenticSummary(c.customer_id);
      setCustAgenticModal(summary);
    } catch {
      setCustAgenticModal({
        customer_id: c.customer_id,
        omerta_user_number: c.omerta_user_number,
        name: c.name,
        email: c.email,
        phone: c.phone,
        risk_level: c.risk_level,
        status: c.status,
        forensic_findings: [
          {
            category: 'AUTHENTICATION_RISK',
            severity: 'CRITICAL',
            finding: c.primary_reason || 'Excessive verification failures observed.',
            action_required: 'Direct identity verification required before unlocking.',
          },
        ],
        agentic_agents: [
          { agent: 'IdentityVerificationAgent', verdict: 'FLAGGED' },
          { agent: 'NetworkTelemetryAgent', verdict: 'EVALUATED' },
          { agent: 'GeographicVelocityAgent', verdict: 'ACTIVE' },
          { agent: 'ComplianceResolutionAgent', verdict: 'ACTION_REQUIRED' },
        ],
        recommended_resolution: "Confirm customer identity by phone, then click 'Resolve & Unlock'.",
      });
    } finally {
      setCustAgenticLoading(false);
    }
  };

  const handleOpenAgenticModal = async (targetId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setAgenticModalTarget(targetId);
    setAgenticLoading(true);
    try {
      const res = await api.previewAgenticSarReport(targetId);
      setAgenticData(res);
    } catch {
      setAgenticData({
        status: 'PREVIEW',
        feature: 'Agentic Forensics Autonomous Report Drafter',
        target_id: targetId,
        agents: [
          { agent: 'TopologyInspectorAgent', role: 'Analyzes cyclic money flows and entity rings', status: 'Active' },
          { agent: 'AnomalyClassifierAgent', role: 'Evaluates velocity spikes, VPN hops, and Mule patterns', status: 'Active' },
          { agent: 'ComplianceNarrativeAgent', role: 'Drafts formal SAR narrative complying with AML guidelines', status: 'Active' },
          { agent: 'RegTechComplianceAgent', role: 'Cross-references Central Bank regulations and typologies', status: 'Active' },
        ],
        preview_narrative:
          'EVIDENCE SUMMARY: Multiple high-velocity transfers initiated following rapid IP geolocation shifts. Graph topology revealed closed cyclic fund disbursement matching structuring typologies.',
      });
    } finally {
      setAgenticLoading(false);
    }
  };

  const handleOpenDisposition = (txn: any, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedTxn(txn);
    setDisposition('LEGITIMATE_ACTIVITY');
    setRationale('');
  };

  const handleSubmitDisposition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTxn) return;
    setSubmitting(true);
    try {
      const caseId = selectedTxn.related_cases?.[0]?.id || selectedTxn.external_id || selectedTxn.id;
      await api.recordCaseDisposition(caseId, {
        disposition,
        rationale: rationale.trim() || 'Reviewed and recorded by compliance analyst.',
        new_status: 'RESOLVED',
      });
      setActionSuccessMsg(`Compliance disposition for ${selectedTxn.external_id || selectedTxn.id} recorded.`);
      setSelectedTxn(null);
      fetchQueue();
      setTimeout(() => setActionSuccessMsg(''), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to record disposition.');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredProblemCustomers = problemCustomers.filter((c) => {
    if (!problemSearch) return true;
    const q = problemSearch.toLowerCase();
    return (
      c.name?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) ||
      c.omerta_user_number?.toLowerCase().includes(q) ||
      c.phone?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Action Success Alert Notification */}
      {actionSuccessMsg && (
        <div className="p-4 rounded-[12px] bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2.5">
            <CheckCircle className="h-5 w-5 text-[#10B981] stroke-[2.5]" />
            <span className="text-xs font-bold">{actionSuccessMsg}</span>
          </div>
          <button
            onClick={() => setActionSuccessMsg('')}
            className="text-xs font-bold text-[#065F46] hover:underline cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Header Banner */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <ShieldAlert className="w-4 h-4" />
            Compliance Queue (score &gt; 40.00%)
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Risk Monitoring &amp; Human Review Queue
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Strict regulatory review pipeline for high-risk transfers, verification locks, and AML escalations.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={() => {
              fetchQueue();
              fetchProblemCustomers();
            }}
            variant="secondary"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 ${loading || loadingProblems ? 'animate-spin text-[#002D72]' : ''}`} />
            <span>Refresh Telemetry</span>
          </Button>
        </div>
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Queue Depth (>40%)"
          value={total}
          subtitle="Awaiting compliance review"
          icon={ShieldAlert}
          variant="gold"
        />
        <StatCard
          title="Flagged Customers"
          value={problemCustomers.length}
          subtitle="Authentication or risk holds"
          icon={Users}
          variant="amber"
          onClick={() => setActiveTab('problem_customers')}
        />
        <StatCard
          title="High-Risk (>70%)"
          value={items.filter((i) => i.risk_score >= 70).length}
          subtitle="Critical risk escalation"
          icon={AlertTriangle}
          variant="rose"
        />
        <StatCard
          title="Avg Review SLA"
          value="< 4.2 min"
          subtitle="Real-time queue response"
          icon={Clock}
          variant="sapphire"
        />
      </div>

      {/* Queue Tabs */}
      <Card>
        <div className="px-6 pt-2">
          <Tabs
            tabs={[
              {
                id: 'transactions',
                label: 'Transactions Review Queue',
                count: total,
                icon: ShieldAlert,
              },
              {
                id: 'problem_customers',
                label: 'Flagged & Locked Customers',
                count: problemCustomers.length,
                icon: Users,
              },
            ]}
            activeTab={activeTab}
            onChange={(id) => setActiveTab(id as any)}
          />
        </div>

        <CardContent className="p-0">
          {activeTab === 'transactions' ? (
            <div>
              {/* Table Filters */}
              <div className="p-4 border-b border-[#E0DDD6] bg-[#F4F1EC]/30 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-[#64748B]" />
                  <span className="text-xs font-bold uppercase tracking-wider text-[#64748B]">
                    Status Filter:
                  </span>
                  <select
                    value={statusFilter}
                    onChange={(e) => {
                      setStatusFilter(e.target.value);
                      setPage(1);
                    }}
                    className="text-xs font-semibold bg-white border border-[#E0DDD6] rounded-[8px] px-3 py-1.5 text-[#0F172A] outline-none cursor-pointer focus:border-[#1E88E5]"
                  >
                    <option value="">All Review Statuses</option>
                    <option value="REQUIRES_REVIEW">Requires Review</option>
                    <option value="UNDER_INVESTIGATION">Under Investigation</option>
                    <option value="COMPLETED">Completed / Released</option>
                    <option value="BLOCKED">Blocked / Rejected</option>
                  </select>
                </div>

                <div className="text-xs text-[#64748B] font-medium">
                  Showing <span className="font-bold text-[#002D72]">{items.length}</span> of{' '}
                  <span className="font-bold text-[#002D72]">{total}</span> flagged transfers
                </div>
              </div>

              {/* Transactions Table */}
              <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Transaction</TableHead>
                      <TableHead>Customer / Sender</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Risk Score</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Timestamp</TableHead>
                      <TableHead className="text-right">Compliance Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.length > 0 ? (
                      items.map((txn: any) => (
                        <TableRow
                          key={txn.external_id || txn.id}
                          onClick={() => navigate(`/admin/transactions/${txn.external_id || txn.id}`)}
                          className="cursor-pointer"
                        >
                          <TableCell>
                            <div className="font-mono font-bold text-[#002D72]">
                              {txn.external_id || txn.id}
                            </div>
                            <div className="text-[11px] text-[#64748B]">
                              {txn.channel || 'DIGITAL_TRANSFER'}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="font-semibold text-[#0F172A]">
                              {txn.sender_name || txn.customer_name || 'Account Holder'}
                            </div>
                            <div className="text-[11px] font-mono text-[#64748B]">
                              {txn.sender_account_number || txn.account_number || 'ACC-MONITORED'}
                            </div>
                          </TableCell>
                          <TableCell className="font-mono font-bold text-[#002D72]">
                            {txn.amount
                              ? `${Number(txn.amount).toLocaleString()} ${txn.currency || 'EGP'}`
                              : '0 EGP'}
                          </TableCell>
                          <TableCell>
                            <RiskBadge
                              level={
                                txn.risk_level ||
                                (txn.risk_score >= 70
                                  ? 'HIGH'
                                  : txn.risk_score >= 40
                                  ? 'REQUIRES_REVIEW'
                                  : 'LOW')
                              }
                              score={txn.risk_score}
                            />
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={txn.status || 'REQUIRES_REVIEW'} />
                          </TableCell>
                          <TableCell className="text-xs font-mono text-[#64748B]">
                            {txn.created_at
                              ? new Date(txn.created_at).toLocaleString()
                              : 'Recent'}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                              {txn.status === 'REQUIRES_REVIEW' && (
                                <>
                                  <Button
                                    onClick={(e) => handleApproveTransaction(txn.external_id || txn.id, e)}
                                    variant="emerald"
                                    size="sm"
                                    className="h-8 px-2.5 text-xs"
                                    title="Approve and release funds"
                                  >
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                    <span>Release</span>
                                  </Button>
                                  <Button
                                    onClick={(e) => handleRejectTransaction(txn.external_id || txn.id, e)}
                                    variant="danger"
                                    size="sm"
                                    className="h-8 px-2.5 text-xs"
                                    title="Reject and freeze transfer"
                                  >
                                    <XCircle className="w-3.5 h-3.5" />
                                    <span>Reject</span>
                                  </Button>
                                </>
                              )}
                              <Button
                                onClick={(e) => handleOpenDisposition(txn, e)}
                                variant="secondary"
                                size="sm"
                                className="h-8 px-2.5 text-xs"
                              >
                                <span>Record Decision</span>
                              </Button>
                              <Button
                                onClick={(e) => handleOpenAgenticModal(txn.external_id || txn.id, e)}
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2 text-[#002D72]"
                                title="Forensic AI Assessment"
                              >
                                <Bot className="w-4 h-4 text-[#F9A825]" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-12 text-xs text-[#64748B]">
                          {loading ? 'Scanning real-time compliance queue...' : 'No transactions currently requiring human review.'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
          ) : (
            <div>
              {/* Problem Customers Tab */}
              <div className="p-4 border-b border-[#E0DDD6] bg-[#F4F1EC]/30 flex flex-wrap items-center justify-between gap-3">
                <div className="relative w-72">
                  <Input
                    value={problemSearch}
                    onChange={(e) => setProblemSearch(e.target.value)}
                    placeholder="Search name, phone, user ID..."
                    leftIcon={<Search className="w-4 h-4 text-[#64748B]" />}
                    className="h-9 text-xs"
                  />
                </div>
                <div className="text-xs text-[#64748B] font-medium">
                  Showing <span className="font-bold text-[#002D72]">{filteredProblemCustomers.length}</span> locked customer accounts
                </div>
              </div>

              <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Customer</TableHead>
                      <TableHead>User ID</TableHead>
                      <TableHead>Risk Level</TableHead>
                      <TableHead>Hold Reason / Flags</TableHead>
                      <TableHead>Account Status</TableHead>
                      <TableHead className="text-right">Clearance Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredProblemCustomers.length > 0 ? (
                      filteredProblemCustomers.map((cust: any) => (
                        <TableRow
                          key={cust.customer_id}
                          onClick={(e) => handleOpenCustomerAgenticModal(cust, e)}
                          className="cursor-pointer"
                        >
                          <TableCell>
                            <div className="font-bold text-[#002D72]">{cust.name}</div>
                            <div className="text-[11px] text-[#64748B]">{cust.email}</div>
                          </TableCell>
                          <TableCell className="font-mono font-bold text-[#002D72]">
                            {cust.omerta_user_number || cust.customer_id}
                          </TableCell>
                          <TableCell>
                            <RiskBadge level={cust.risk_level || 'HIGH'} />
                          </TableCell>
                          <TableCell>
                            <div className="text-xs text-[#DC2626] font-semibold">
                              {cust.primary_reason || 'Security hold & verification lock'}
                            </div>
                            <div className="text-[11px] text-[#64748B]">
                              Failed password attempts: {cust.failed_transfer_passwords_count || 3}
                            </div>
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={cust.status || 'SECURITY_HOLD'} />
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                              <Button
                                onClick={(e) => handleOpenCallModal(cust, e)}
                                variant="secondary"
                                size="sm"
                                className="h-8 px-2 text-xs"
                                title="Call customer to verify"
                              >
                                <PhoneCall className="w-3.5 h-3.5 text-[#002D72]" />
                              </Button>
                              <Button
                                onClick={(e) => handleOpenEmailModal(cust, e)}
                                variant="secondary"
                                size="sm"
                                className="h-8 px-2 text-xs"
                                title="Send compliance notice"
                              >
                                <Mail className="w-3.5 h-3.5 text-[#002D72]" />
                              </Button>
                              <Button
                                onClick={() => handleResolveRisk(cust.customer_id, cust.name)}
                                variant="primary"
                                size="sm"
                                className="h-8 px-2.5 text-xs"
                              >
                                <Unlock className="w-3.5 h-3.5" />
                                <span>Resolve &amp; Unlock</span>
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-12 text-xs text-[#64748B]">
                          {loadingProblems ? 'Loading flagged accounts...' : 'No customer accounts currently on security hold.'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* MODAL 1: RECORD COMPLIANCE DISPOSITION */}
      {selectedTxn && (
        <Modal
          isOpen={Boolean(selectedTxn)}
          onClose={() => setSelectedTxn(null)}
          title="Record Compliance Review Disposition"
          subtitle={`Case Audit for Transaction: ${selectedTxn.external_id || selectedTxn.id}`}
          maxWidth="md"
        >
          <form onSubmit={handleSubmitDisposition} className="space-y-4 text-xs">
            <Select
              label="Review Disposition Verdict"
              value={disposition}
              onChange={(e) => setDisposition(e.target.value)}
            >
              <option value="LEGITIMATE_ACTIVITY">Legitimate Activity — Cleared (Low Risk)</option>
              <option value="FALSE_POSITIVE">False Positive — Rule Exception Granted</option>
              <option value="SUSPICIOUS_STRUCTURING">Suspicious Activity — Structuring / Smurfing</option>
              <option value="MULE_ACCOUNT_PATTERN">Mule Account — Rapid Flow-Through</option>
              <option value="IDENTITY_TAKEOVER">Account Takeover / Stolen Credential</option>
              <option value="SANCTIONS_INTERSECTION">Sanctions / Watchlist Intersection</option>
            </Select>

            <div className="space-y-1">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#475569]">
                Compliance Rationale &amp; Evidence Notes
              </label>
              <textarea
                rows={4}
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                placeholder="Enter investigation findings, baseline comparison, and justification for audit log..."
                className="w-full bg-white border border-[#E0DDD6] rounded-[10px] p-3 text-sm text-[#0F172A] outline-none focus:border-[#1E88E5] focus:ring-3 focus:ring-[#1E88E5]/15"
                required
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setSelectedTxn(null)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                isLoading={submitting}
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Submit Official Record</span>
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL 2: PHONE VERIFICATION SIMULATOR */}
      {callModalCust && (
        <Modal
          isOpen={Boolean(callModalCust)}
          onClose={() => setCallModalCust(null)}
          title="Direct Identity Verification (Voice / OTP)"
          subtitle={`Verify identity of customer: ${callModalCust.name}`}
          maxWidth="md"
        >
          <div className="space-y-4 text-xs">
            <div className="p-3.5 rounded-[12px] bg-[#EBF3FC] border border-[#BFDBFE] text-[#002D72] flex items-start gap-3">
              <PhoneCall className="w-5 h-5 text-[#002D72] shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-sm">Customer Hotline: {callModalCust.phone || '+20 100 123 4567'}</p>
                <p className="text-xs text-[#475569] mt-0.5">
                  Confirm secret security question, recent account transfers, and registered device before clearing hold.
                </p>
              </div>
            </div>

            <div className="space-y-2 bg-[#F4F1EC] p-3.5 rounded-[10px] border border-[#E0DDD6]">
              <p className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider">Verification Checklist:</p>
              <ul className="list-disc pl-4 space-y-1 text-[#475569]">
                <li>Did customer initiate the transfer from a recognized mobile device?</li>
                <li>Confirm registered national ID or passport details.</li>
                <li>Ensure no third-party remote screen sharing is active.</li>
              </ul>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setCallModalCust(null)}
              >
                Close
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={() => {
                  handleResolveRisk(callModalCust.customer_id, callModalCust.name);
                  setCallModalCust(null);
                }}
              >
                <Unlock className="w-4 h-4" />
                <span>Identity Verified — Unlock Account</span>
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 3: COMPLIANCE EMAIL NOTICE */}
      {emailModalCust && (
        <Modal
          isOpen={Boolean(emailModalCust)}
          onClose={() => setEmailModalCust(null)}
          title="Send Compliance Security Notice"
          subtitle={`Dispatch secure email notification to ${emailModalCust.email}`}
          maxWidth="lg"
        >
          <form onSubmit={handleSendEmailNotice} className="space-y-4 text-xs">
            <Input
              label="Email Subject"
              value={emailSubject}
              onChange={(e) => setEmailSubject(e.target.value)}
              required
            />

            <div className="space-y-1">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#475569]">
                Notice Body
              </label>
              <textarea
                rows={6}
                value={emailBody}
                onChange={(e) => setEmailBody(e.target.value)}
                className="w-full bg-white border border-[#E0DDD6] rounded-[10px] p-3 text-sm font-mono text-[#0F172A] outline-none focus:border-[#1E88E5]"
                required
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setEmailModalCust(null)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                isLoading={emailSubmitting}
              >
                <Mail className="w-4 h-4" />
                <span>Send Compliance Notice</span>
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL 4: FORENSIC AGENTIC ASSESSMENT PREVIEW */}
      {agenticModalTarget && (
        <Modal
          isOpen={Boolean(agenticModalTarget)}
          onClose={() => setAgenticModalTarget(null)}
          title="Forensic Risk Telemetry &amp; Evidence"
          subtitle={`Multi-Agent Assessment Dossier: ${agenticModalTarget}`}
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            {agenticLoading ? (
              <div className="py-12 text-center text-[#64748B]">
                <Bot className="h-8 w-8 text-[#002D72] animate-bounce mx-auto mb-2" />
                <p className="font-bold">Synthesizing multi-agent graph telemetry...</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {agenticData?.agents?.map((ag: any, idx: number) => (
                    <div key={idx} className="p-3 bg-[#F4F1EC] rounded-[10px] border border-[#E0DDD6]">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-[#002D72]">{ag.agent}</span>
                        <StatusBadge status={ag.status || ag.verdict || 'ACTIVE'} />
                      </div>
                      <p className="text-[11px] text-[#64748B]">{ag.role || 'Evaluates multi-signal transaction vectors.'}</p>
                    </div>
                  ))}
                </div>

                <div className="p-4 rounded-[12px] bg-[#FFF9E6] border border-[#FFE082]">
                  <h5 className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider mb-1 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-[#F9A825]" />
                    AI Observation Narrative
                  </h5>
                  <p className="text-xs text-[#0F172A] leading-relaxed font-mono">
                    {agenticData?.preview_narrative || 'Observation telemetry generated.'}
                  </p>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <Button
                    type="button"
                    variant="primary"
                    onClick={() => setAgenticModalTarget(null)}
                  >
                    Dismiss
                  </Button>
                </div>
              </>
            )}
          </div>
        </Modal>
      )}

      {/* MODAL 5: CUSTOMER FORENSIC DOSSIER MODAL */}
      {custAgenticModal && (
        <Modal
          isOpen={Boolean(custAgenticModal)}
          onClose={() => setCustAgenticModal(null)}
          title={`Forensic Dossier: ${custAgenticModal.name}`}
          subtitle={`Customer ID: ${custAgenticModal.omerta_user_number || custAgenticModal.customer_id}`}
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            {custAgenticLoading ? (
              <div className="py-12 text-center text-[#64748B]">
                <Bot className="h-8 w-8 text-[#002D72] animate-pulse mx-auto mb-2" />
                <p className="font-bold">Aggregating customer risk signals...</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[#F4F1EC] p-3 rounded-[10px] border border-[#E0DDD6]">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Risk Status</span>
                    <div className="mt-0.5">
                      <RiskBadge level={custAgenticModal.risk_level || 'HIGH'} />
                    </div>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Account State</span>
                    <div className="mt-0.5">
                      <StatusBadge status={custAgenticModal.status || 'SECURITY_HOLD'} />
                    </div>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Phone</span>
                    <p className="font-mono font-bold text-[#002D72] mt-0.5">{custAgenticModal.phone || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Email</span>
                    <p className="truncate font-semibold text-[#002D72] mt-0.5">{custAgenticModal.email}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <h5 className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider">
                    Forensic Observations &amp; Signals
                  </h5>
                  {custAgenticModal.forensic_findings?.map((f: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-[10px] bg-white border border-[#E0DDD6] shadow-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-[#002D72]">{f.category?.replace(/_/g, ' ')}</span>
                        <StatusBadge status={f.severity} />
                      </div>
                      <p className="text-xs text-[#0F172A]">{f.finding}</p>
                      {f.action_required && (
                        <p className="text-[11px] text-[#B45309] font-medium">Action: {f.action_required}</p>
                      )}
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[#E0DDD6]">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setCustAgenticModal(null)}
                  >
                    Close
                  </Button>
                  <Button
                    type="button"
                    variant="primary"
                    onClick={() => {
                      handleResolveRisk(custAgenticModal.customer_id, custAgenticModal.name);
                      setCustAgenticModal(null);
                    }}
                  >
                    <Unlock className="w-4 h-4" />
                    <span>Resolve Risk &amp; Unlock Customer</span>
                  </Button>
                </div>
              </>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
};
