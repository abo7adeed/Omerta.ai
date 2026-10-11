import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
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
  Sparkles,
  ShieldCheck,
  Activity,
  TrendingUp,
  Wallet,
  Send,
  Layers,
  Scale,
  Network,
  Info,
  XCircle,
  Search,
  RotateCcw,
  ExternalLink,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  CaseItem,
  AccountInvestigationReport,
  SimulatedWithdrawalResponse,
} from '../api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { RiskBadge } from '../components/ui/RiskBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const InvestigationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [page, setPage] = useState(1);

  // Case Dossier Modal state
  const [selectedCase, setSelectedCase] = useState<any | null>(null);
  const [dossierLoading, setDossierLoading] = useState(false);

  // Direct Transaction Investigation input
  const [directTxnInput, setDirectTxnInput] = useState('');

  // Account Forensic Investigation State (LangGraph)
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
  const [accountTarget, setAccountTarget] = useState('ACC-6001');
  const [timeRangeDays, setTimeRangeDays] = useState(30);
  const [investigationReason, setInvestigationReason] = useState('AMOUNT_ESCALATION');
  const [accountReport, setAccountReport] = useState<AccountInvestigationReport | null>(null);
  const [investigationRunning, setInvestigationRunning] = useState(false);
  const [investigationError, setInvestigationError] = useState<string | null>(null);
  const [activeReportTab, setActiveReportTab] = useState<'report' | 'ml_graph' | 'transactions' | 'simulation'>('report');

  // Sandbox Withdrawal Simulation State
  const [simAccount, setSimAccount] = useState('ACC-SIM-TEST1');
  const [simAmount, setSimAmount] = useState('500.00');
  const [simRunning, setSimRunning] = useState(false);
  const [simResult, setSimResult] = useState<SimulatedWithdrawalResponse | null>(null);
  const [simError, setSimError] = useState<string | null>(null);
  const [sandboxFixtures, setSandboxFixtures] = useState<any[]>([]);
  const [scenarioStatus, setScenarioStatus] = useState<string | null>(null);

  useEffect(() => {
    api.getSandboxFixtures().then((fixtures) => {
      if (fixtures && fixtures.length > 0) {
        setSandboxFixtures(fixtures);
      }
    }).catch(() => {});
  }, []);

  const handleRunAccountInvestigation = async (targetId?: string) => {
    const accId = (targetId || accountTarget).trim();
    if (!accId) return;
    setAccountTarget(accId);
    setInvestigationRunning(true);
    setInvestigationError(null);
    try {
      const res = await api.investigateAccount({
        account_id: accId,
        time_range_days: timeRangeDays,
        investigation_reason: investigationReason,
        persist: false,
      });
      setAccountReport(res);
      setIsAccountModalOpen(true);
    } catch (err: any) {
      console.error('Account investigation failed:', err);
      setInvestigationError(err?.message || 'Failed to complete LangGraph account investigation.');
    } finally {
      setInvestigationRunning(false);
    }
  };

  const handleExecuteSimulation = async (customAmt?: number, customNote?: string) => {
    setSimRunning(true);
    setSimError(null);
    setScenarioStatus(null);
    try {
      const amt = customAmt !== undefined ? customAmt : (parseFloat(simAmount) || 500);
      const res = await api.simulateWithdrawal({
        account_id: simAccount.trim(),
        amount: amt,
        currency: 'EGP',
        idempotency_key: `IDEMP-SIM-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        is_sandbox_confirmed: true,
        note: customNote || `Simulated test withdrawal of ${amt} EGP`,
      });
      setSimResult(res);
      return res;
    } catch (err: any) {
      console.error('Simulation failed:', err);
      setSimError(err?.message || 'Simulated withdrawal failed.');
      throw err;
    } finally {
      setSimRunning(false);
    }
  };

  const handleRunScenario = async (scenario: 'normal' | 'burst' | 'escalation' | 'insufficient') => {
    setSimError(null);
    setScenarioStatus(`Running scenario: ${scenario}...`);
    try {
      if (scenario === 'normal') {
        setSimAmount('500.00');
        await handleExecuteSimulation(500, 'Scenario Normal: standard test withdrawal');
        setScenarioStatus('Scenario Normal: 500.00 EGP executed successfully.');
      } else if (scenario === 'burst') {
        setScenarioStatus('Executing rapid burst: 3 withdrawals in sub-minute interval...');
        const r1 = await handleExecuteSimulation(500, 'Burst step 1/3 (500 EGP)');
        await new Promise((r) => setTimeout(r, 600));
        const r2 = await handleExecuteSimulation(500, 'Burst step 2/3 (500 EGP)');
        await new Promise((r) => setTimeout(r, 600));
        const r3 = await handleExecuteSimulation(500, 'Burst step 3/3 (500 EGP)');
        setScenarioStatus(`Burst complete: 3 simulated withdrawals submitted. Latest: ${r3.transaction_id}`);
      } else if (scenario === 'escalation') {
        setScenarioStatus('Executing escalation sequence: 100 -> 500 -> 5,000 EGP...');
        await handleExecuteSimulation(100, 'Escalation step 1 (100 EGP)');
        await new Promise((r) => setTimeout(r, 600));
        await handleExecuteSimulation(500, 'Escalation step 2 (500 EGP)');
        await new Promise((r) => setTimeout(r, 600));
        const r3 = await handleExecuteSimulation(5000, 'Escalation step 3 (5,000 EGP)');
        setScenarioStatus(`Escalation completed! Final high-value transfer: ${r3.transaction_id} (Triggered velocity/escalation rules)`);
      } else if (scenario === 'insufficient') {
        setSimAmount('99999999.00');
        try {
          await handleExecuteSimulation(99999999, 'Scenario: Insufficient funds boundary test');
        } catch {
          setScenarioStatus('Insufficient funds rejection verified as expected.');
        }
      }
    } catch (e: any) {
      setScenarioStatus(`Scenario aborted: ${e?.message || 'Error'}`);
    }
  };

  const handleResetSandbox = async () => {
    if (!window.confirm('Reset sandbox test accounts and balances back to initial synthetic values? (Production accounts are completely untouched).')) {
      return;
    }
    try {
      const res = await api.resetSandbox();
      alert(`Sandbox Reset: ${res.message}`);
      setSimResult(null);
      setScenarioStatus('Sandbox state safely reset.');
    } catch (e: any) {
      alert(`Sandbox reset failed: ${e?.message || 'Error'}`);
    }
  };

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
            onClick={() => handleRunAccountInvestigation()}
            variant="primary"
            size="sm"
            disabled={investigationRunning}
            leftIcon={<Sparkles className={`h-4 w-4 text-[#F9A825] ${investigationRunning ? 'animate-spin' : ''}`} />}
            className="bg-[#002D72] hover:bg-[#001D4D] text-white"
          >
            {investigationRunning ? 'Running LangGraph...' : 'Investigate Account (LangGraph)'}
          </Button>
          <Button
            onClick={fetchCases}
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Cases
          </Button>
        </div>
      </Card>

      {/* Account Forensic Investigation Workbench Quick Launch */}
      <Card className="p-5 border-[#002D72]/20 bg-gradient-to-r from-[#F8FAFC] via-[#F1F5F9] to-[#E2E8F0]/40">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[#002D72]">
              <Sparkles className="w-3.5 h-3.5 text-[#F9A825]" />
              Evidence-Based Forensic Investigation Engine
            </div>
            <h3 className="text-base font-bold text-[#002D72] mt-0.5">
              Multi-Source Account Dossier &amp; Risk Analytics
            </h3>
            <p className="text-xs text-[#64748B] mt-0.5">
              Integrates PostgreSQL ledger facts, LightGBM model (<span className="font-mono text-[#002D72]">lgbm-risk-v1</span>), Neo4j topology, and banking velocity rules.
            </p>

            {/* Quick User Chips */}
            <div className="flex items-center gap-1.5 mt-2 flex-wrap">
              <span className="text-[10px] uppercase font-bold text-[#64748B] mr-1">Quick Target:</span>
              {[
                { id: 'ACC-90953F44', label: 'Abdo Haaland' },
                { id: 'ACC-1001', label: 'Ziad Karim' },
                { id: 'ACC-679B566D', label: 'Abdo Belli' },
                { id: 'ACC-0001', label: 'Mohamed El-Sayed' },
                { id: 'ACC-6001', label: 'Syndicate (ACC-6001)' },
              ].map((chip) => (
                <button
                  key={chip.id}
                  type="button"
                  onClick={() => {
                    setAccountTarget(chip.id);
                    handleRunAccountInvestigation(chip.id);
                  }}
                  className={`text-[11px] px-2 py-0.5 rounded-full font-medium transition-colors ${
                    accountTarget === chip.id
                      ? 'bg-[#002D72] text-white shadow-sm'
                      : 'bg-white border border-[#CBD5E1] text-[#002D72] hover:bg-[#F1F5F9]'
                  }`}
                >
                  {chip.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-1.5 bg-white border border-[#CBD5E1] rounded-[10px] px-2.5 py-1.5 text-xs shadow-sm">
              <span className="text-[#64748B] text-[11px] font-medium">Target:</span>
              <select
                value={accountTarget}
                onChange={(e) => setAccountTarget(e.target.value)}
                className="font-mono font-bold text-[#002D72] bg-transparent outline-none cursor-pointer"
              >
                <option value="ACC-90953F44">ACC-90953F44 (Abdo Haaland)</option>
                <option value="ACC-1001">ACC-1001 (Ziad Karim)</option>
                <option value="ACC-679B566D">ACC-679B566D (Abdo Belli)</option>
                <option value="ACC-0001">ACC-0001 (Mohamed El-Sayed)</option>
                <option value="ACC-6001">ACC-6001 (Structuring / Syndicate)</option>
                <option value="ACC-3001">ACC-3001 (Standard Checking)</option>
                <option value="ACC-SIM-TEST1">ACC-SIM-TEST1 (Sandbox Test 1)</option>
                <option value="ACC-SIM-TEST2">ACC-SIM-TEST2 (Sandbox Test 2)</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 bg-white border border-[#CBD5E1] rounded-[10px] px-2.5 py-1.5 text-xs shadow-sm">
              <span className="text-[#64748B] text-[11px] font-medium">Window:</span>
              <select
                value={timeRangeDays}
                onChange={(e) => setTimeRangeDays(Number(e.target.value))}
                className="font-medium text-[#002D72] bg-transparent outline-none cursor-pointer"
              >
                <option value={7}>7 Days</option>
                <option value={30}>30 Days</option>
                <option value={90}>90 Days</option>
              </select>
            </div>

            <Button
              onClick={() => handleRunAccountInvestigation()}
              variant="primary"
              size="sm"
              disabled={investigationRunning}
              leftIcon={<Activity className={`w-3.5 h-3.5 ${investigationRunning ? 'animate-spin' : ''}`} />}
            >
              {investigationRunning ? 'Analyzing...' : 'Run Investigation'}
            </Button>

            {accountReport && (
              <Button
                onClick={() => setIsAccountModalOpen(true)}
                variant="outline"
                size="sm"
                className="border-[#002D72] text-[#002D72]"
              >
                View Dossier ({accountReport.investigation_id.slice(-8)})
              </Button>
            )}
          </div>
        </div>

        {/* Transaction Quick Launch Bar */}
        <div className="mt-4 pt-3 border-t border-[#E2E8F0] flex flex-col sm:flex-row items-center justify-between gap-3 bg-white/70 p-3 rounded-[10px]">
          <div className="flex items-center gap-2 text-xs text-[#002D72] font-semibold">
            <Search className="w-4 h-4 text-[#F9A825]" />
            <span>Investigate Individual Transaction:</span>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <input
              type="text"
              placeholder="e.g. TXN-SIM-A141F922 or TXN-010"
              value={directTxnInput}
              onChange={(e) => setDirectTxnInput(e.target.value)}
              className="font-mono text-xs px-3 py-1.5 border border-[#CBD5E1] rounded-[8px] bg-white outline-none focus:border-[#002D72] w-full sm:w-64"
            />
            <Button
              size="sm"
              variant="secondary"
              disabled={!directTxnInput.trim()}
              onClick={() => {
                if (directTxnInput.trim()) {
                  navigate(`/admin/transactions/${directTxnInput.trim()}`);
                }
              }}
              className="shrink-0 text-xs text-[#002D72] font-bold"
            >
              Open Workbench
            </Button>
          </div>
        </div>

        {investigationError && (
          <div className="mt-3 p-3 bg-[#FEE2E2] border border-[#FECACA] rounded-[8px] text-xs text-[#DC2626] flex items-center gap-2">
            <XCircle className="w-4 h-4 shrink-0" />
            <span>{investigationError}</span>
          </div>
        )}
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

      {/* LangGraph Account Forensic Investigation Report Modal */}
      {isAccountModalOpen && accountReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-[16px] shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-[#CBD5E1]">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-[#E2E8F0] bg-[#002D72] text-white flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
                  <Sparkles className="w-5 h-5 text-[#F9A825]" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-base tracking-tight text-white">
                      Forensic Investigation Dossier
                    </h3>
                    <span className="font-mono text-[11px] bg-white/20 px-2 py-0.5 rounded text-white font-medium">
                      {accountReport.investigation_id}
                    </span>
                  </div>
                  <p className="text-xs text-white/80 mt-0.5">
                    Account: <strong>{accountReport.account_id}</strong> ({accountReport.account_facts?.customer_name || 'Account Holder'}) • Lookback: {accountReport.time_range_days} Days
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsAccountModalOpen(false)}
                  className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors cursor-pointer"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center gap-2 px-6 pt-3 border-b border-[#E2E8F0] bg-[#F8FAFC] shrink-0 text-xs font-medium">
              <button
                onClick={() => setActiveReportTab('report')}
                className={`pb-2.5 px-3 border-b-2 transition-all cursor-pointer ${
                  activeReportTab === 'report'
                    ? 'border-[#002D72] text-[#002D72] font-bold'
                    : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
                }`}
              >
                Forensic Report &amp; Rules
              </button>
              <button
                onClick={() => setActiveReportTab('ml_graph')}
                className={`pb-2.5 px-3 border-b-2 transition-all cursor-pointer ${
                  activeReportTab === 'ml_graph'
                    ? 'border-[#002D72] text-[#002D72] font-bold'
                    : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
                }`}
              >
                LightGBM ML &amp; Neo4j Topology
              </button>
              <button
                onClick={() => setActiveReportTab('transactions')}
                className={`pb-2.5 px-3 border-b-2 transition-all cursor-pointer ${
                  activeReportTab === 'transactions'
                    ? 'border-[#002D72] text-[#002D72] font-bold'
                    : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
                }`}
              >
                Transaction Facts ({accountReport.transaction_facts_count})
              </button>
              <button
                onClick={() => setActiveReportTab('simulation')}
                className={`pb-2.5 px-3 border-b-2 transition-all cursor-pointer ${
                  activeReportTab === 'simulation'
                    ? 'border-[#002D72] text-[#002D72] font-bold'
                    : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
                }`}
              >
                Sandbox Withdrawal Simulator
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs text-[#0F172A]">
              {/* TAB 1: Main Forensic Report & Banking Rules */}
              {activeReportTab === 'report' && (
                <>
                  {/* Executive Summary & Composite Risk Header */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Left: Composite Score Gauge */}
                    <div className="p-4 rounded-xl border border-[#CBD5E1] bg-white flex flex-col justify-between">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">Composite Risk Score</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          accountReport.threshold_exceeded ? 'bg-[#FEE2E2] text-[#DC2626]' : 'bg-[#DCFCE7] text-[#15803D]'
                        }`}>
                          {accountReport.threshold_exceeded ? 'THRESHOLD EXCEEDED' : 'NORMAL RANGE'}
                        </span>
                      </div>
                      <div className="my-3 flex items-baseline gap-2">
                        <span className="text-3xl font-extrabold text-[#002D72]">
                          {(accountReport.combined_risk_score * 100).toFixed(1)}%
                        </span>
                        <span className="text-[11px] text-[#64748B]">/ 100%</span>
                      </div>
                      <div className="space-y-1 text-[11px] text-[#64748B]">
                        <div className="flex justify-between">
                          <span>LightGBM ML Model (55%):</span>
                          <strong className="text-[#002D72]">{(accountReport.ml_risk.risk_score * 100).toFixed(1)}%</strong>
                        </div>
                        <div className="flex justify-between">
                          <span>Deterministic Rules (45%):</span>
                          <strong className="text-[#002D72]">{(accountReport.rules_score * 100).toFixed(1)}%</strong>
                        </div>
                        <div className="flex justify-between border-t border-[#E2E8F0] pt-1">
                          <span>App Alert Threshold:</span>
                          <span className="font-mono text-[#DC2626]">{(accountReport.operational_alert_threshold * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    </div>

                    {/* Middle & Right: Executive Summary & Recommendation */}
                    <div className="md:col-span-2 p-4 rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] flex flex-col justify-between space-y-3">
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-[#002D72]">Executive Summary</span>
                          <span className="text-[10px] font-mono text-[#64748B]">{accountReport.execution_time_ms} ms</span>
                        </div>
                        <p className="text-xs leading-relaxed text-[#334155] font-normal">
                          {accountReport.executive_summary}
                        </p>
                      </div>

                      <div className="p-3 bg-white rounded-lg border border-[#E2E8F0] space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-bold uppercase text-[#64748B]">Compliance Recommendation:</span>
                          <span className="px-2 py-0.5 rounded text-[11px] font-extrabold bg-[#002D72] text-white">
                            {accountReport.recommended_action}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#475569]">
                          {accountReport.recommended_action_justification}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Triggered Banking Rules Section */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-[#002D72] text-xs uppercase tracking-wider flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4 text-[#DC2626]" />
                        Triggered Behavioral Rules &amp; FATF Directives ({accountReport.triggered_rules.length})
                      </h4>
                    </div>

                    {accountReport.triggered_rules.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {accountReport.triggered_rules.map((rule, idx) => (
                          <div
                            key={idx}
                            className={`p-3.5 rounded-xl border ${
                              rule.severity === 'CRITICAL'
                                ? 'bg-[#FFF1F2] border-[#FECDD3]'
                                : rule.severity === 'HIGH'
                                ? 'bg-[#FEF2F2] border-[#FCA5A5]'
                                : 'bg-[#FFFBEB] border-[#FDE68A]'
                            } space-y-1.5`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-[#0F172A] text-xs">{rule.rule_name}</span>
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${
                                    rule.reference_type === 'STATUTORY_REGULATION'
                                      ? 'bg-purple-100 text-purple-700 border border-purple-200'
                                      : rule.reference_type === 'INTERNAL_BANKING_HEURISTIC'
                                      ? 'bg-slate-100 text-slate-700 border border-slate-200'
                                      : 'bg-blue-100 text-blue-700 border border-blue-200'
                                  }`}
                                >
                                  {rule.reference_type === 'STATUTORY_REGULATION'
                                    ? 'Statutory Law'
                                    : rule.reference_type === 'INTERNAL_BANKING_HEURISTIC'
                                    ? 'Bank Policy Heuristic'
                                    : 'FATF Guidance'}
                                </span>
                              </div>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  rule.severity === 'CRITICAL'
                                    ? 'bg-[#E11D48] text-white'
                                    : rule.severity === 'HIGH'
                                    ? 'bg-[#DC2626] text-white'
                                    : 'bg-[#D97706] text-white'
                                }`}
                              >
                                {rule.severity}
                              </span>
                            </div>
                            <p className="text-[11px] text-[#475569] leading-relaxed">
                              {rule.explanation}
                            </p>
                            <div className="text-[10px] text-[#64748B] pt-1 border-t border-black/5 flex items-center justify-between">
                              <span className="truncate max-w-md">Ref: {rule.regulatory_reference}</span>
                              <span className="font-mono shrink-0">{rule.applicable_window}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-4 bg-[#F0FDF4] border border-[#BBF7D0] rounded-xl text-xs text-[#15803D] flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        <span>No high-risk velocity, structuring, or hardware syndicate rules triggered. Account behavior conforms to normal baseline.</span>
                      </div>
                    )}
                  </div>

                  {/* Generated Dynamic Visualizations */}
                  {accountReport.charts && accountReport.charts.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="font-bold text-[#002D72] text-xs uppercase tracking-wider flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-[#F9A825]" />
                        Forensic Visual Analytics (Evidence Grounded)
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {accountReport.charts.map((chart, idx) => (
                          <div key={idx} className="p-3 bg-white rounded-xl border border-[#CBD5E1] shadow-sm">
                            <h5 className="font-bold text-[#002D72] text-xs mb-2 text-center">{chart.title}</h5>
                            <img
                              src={chart.artifact_url}
                              alt={chart.title}
                              className="w-full h-auto rounded-lg border border-[#E2E8F0] object-contain max-h-[260px]"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Behavioral Metrics Grid */}
                  <div className="space-y-2">
                    <h4 className="font-bold text-[#002D72] text-xs uppercase tracking-wider">
                      Audited Behavioral Metrics
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                      <div className="p-3 bg-white border border-[#E2E8F0] rounded-lg">
                        <span className="text-[10px] text-[#64748B] uppercase font-bold">5m Velocity Peak</span>
                        <p className="text-base font-bold text-[#002D72] mt-0.5">
                          {accountReport.behavioral_metrics.velocity_5m_max_count} txns
                        </p>
                        <span className="text-[10px] text-[#64748B]">
                          Vol: {Number(accountReport.behavioral_metrics.velocity_5m_max_volume).toLocaleString()} EGP
                        </span>
                      </div>
                      <div className="p-3 bg-white border border-[#E2E8F0] rounded-lg">
                        <span className="text-[10px] text-[#64748B] uppercase font-bold">15m Velocity Peak</span>
                        <p className="text-base font-bold text-[#002D72] mt-0.5">
                          {accountReport.behavioral_metrics.velocity_15m_max_count} txns
                        </p>
                        <span className="text-[10px] text-[#64748B]">
                          Vol: {Number(accountReport.behavioral_metrics.velocity_15m_max_volume).toLocaleString()} EGP
                        </span>
                      </div>
                      <div className="p-3 bg-white border border-[#E2E8F0] rounded-lg">
                        <span className="text-[10px] text-[#64748B] uppercase font-bold">Amount Escalation</span>
                        <p className={`text-base font-bold mt-0.5 ${
                          accountReport.behavioral_metrics.has_amount_escalation ? 'text-[#DC2626]' : 'text-[#15803D]'
                        }`}>
                          {accountReport.behavioral_metrics.has_amount_escalation ? 'DETECTED' : 'CLEAR'}
                        </p>
                        <span className="text-[10px] text-[#64748B]">
                          {accountReport.behavioral_metrics.escalation_sequences.length} sequence(s)
                        </span>
                      </div>
                      <div className="p-3 bg-white border border-[#E2E8F0] rounded-lg">
                        <span className="text-[10px] text-[#64748B] uppercase font-bold">Ledger Reconciled</span>
                        <p className="text-base font-bold text-[#15803D] mt-0.5">
                          {accountReport.behavioral_metrics.ledger_reconciled ? 'VERIFIED' : 'DISCREPANCY'}
                        </p>
                        <span className="text-[10px] text-[#64748B]">Double-entry clear</span>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* TAB 2: LightGBM ML & Neo4j Topology */}
              {activeReportTab === 'ml_graph' && (
                <div className="space-y-6">
                  {/* ML Section */}
                  <div className="p-4 bg-white rounded-xl border border-[#CBD5E1] space-y-4">
                    <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-[#002D72]" />
                        <h4 className="font-bold text-[#002D72] text-xs uppercase tracking-wider">
                          LightGBM Classifier Risk Signal ({accountReport.ml_risk.model_version})
                        </h4>
                      </div>
                      <span className="text-[10px] font-mono bg-[#E2E8F0] px-2 py-0.5 rounded text-[#334155]">
                        ROC-AUC: 0.9979 • PR-AUC: 0.9886
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <span className="text-[11px] font-bold text-[#475569]">Feature Space &amp; Architecture:</span>
                        <ul className="mt-2 space-y-1 text-[11px] text-[#64748B]">
                          <li>• Native LightGBM GBDT (13 verified tabular banking features)</li>
                          <li>• Features Version: <strong className="text-[#002D72]">{accountReport.ml_risk.feature_version}</strong></li>
                          <li>• Model Artifact: <span className="font-mono text-[#002D72]">models/risk_lgbm_v1.json</span></li>
                          <li>• Evaluation Status: <strong className="text-[#15803D]">Trained &amp; Calibrated</strong></li>
                        </ul>
                      </div>

                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-bold text-[#475569]">
                            Active Input Feature Importance:
                          </span>
                          <span className="text-[9px] font-mono uppercase bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                            Model-Native Gain
                          </span>
                        </div>
                        <p className="text-[10px] text-[#64748B] italic mt-0.5 mb-2 leading-tight">
                          Renormalized global tree split gain across active inputs (model-native architecture importance; not local Shapley attributions).
                        </p>
                        <div className="space-y-1.5">
                          {Object.entries(accountReport.ml_risk.top_feature_contributions || {}).map(([feat, val], i) => (
                            <div key={i} className="flex items-center justify-between text-[11px]">
                              <span className="font-mono text-[#334155]">{feat}</span>
                              <span className="font-bold text-[#002D72]">{(val * 100).toFixed(1)}%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Neo4j Section */}
                  <div className="p-4 bg-white rounded-xl border border-[#CBD5E1] space-y-4">
                    <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2">
                      <div className="flex items-center gap-2">
                        <Network className="w-4 h-4 text-[#002D72]" />
                        <h4 className="font-bold text-[#002D72] text-xs uppercase tracking-wider">
                          Neo4j Graph Topology &amp; Multi-Hop Syndicate Intelligence
                        </h4>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        accountReport.graph_intelligence.available ? 'bg-[#DCFCE7] text-[#15803D]' : 'bg-[#FEE2E2] text-[#DC2626]'
                      }`}>
                        {accountReport.graph_intelligence.available ? 'GRAPH ONLINE' : 'GRAPH OFFLINE'}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="p-3 bg-[#F8FAFC] rounded-lg border border-[#E2E8F0]">
                        <span className="text-[10px] uppercase font-bold text-[#64748B]">Shared Devices</span>
                        <p className="text-xl font-bold text-[#002D72] mt-0.5">{accountReport.graph_intelligence.shared_device_count}</p>
                        <span className="text-[10px] text-[#64748B]">Hardware fingerprint links</span>
                      </div>
                      <div className="p-3 bg-[#F8FAFC] rounded-lg border border-[#E2E8F0]">
                        <span className="text-[10px] uppercase font-bold text-[#64748B]">Shared IP Addresses</span>
                        <p className="text-xl font-bold text-[#002D72] mt-0.5">{accountReport.graph_intelligence.shared_ip_count}</p>
                        <span className="text-[10px] text-[#64748B]">Network subnets</span>
                      </div>
                      <div className="p-3 bg-[#F8FAFC] rounded-lg border border-[#E2E8F0]">
                        <span className="text-[10px] uppercase font-bold text-[#64748B]">Connected Accounts</span>
                        <p className="text-xl font-bold text-[#002D72] mt-0.5">{accountReport.graph_intelligence.connected_accounts_count}</p>
                        <span className="text-[10px] text-[#64748B]">Transfer counter-parties</span>
                      </div>
                    </div>

                    <p className="text-[11px] text-[#64748B] italic bg-[#F1F5F9] p-2.5 rounded-lg border border-[#E2E8F0]">
                      {accountReport.graph_intelligence.graph_disclaimer}
                    </p>
                  </div>
                </div>
              )}

              {/* TAB 3: Transaction Facts */}
              {activeReportTab === 'transactions' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-[#002D72] text-xs uppercase tracking-wider">
                      Verified Ledger Transactions ({accountReport.transaction_facts_count} in period)
                    </h4>
                  </div>
                  <div className="border border-[#CBD5E1] rounded-xl overflow-hidden">
                    <TableContainer>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Transaction ID</TableHead>
                            <TableHead>Timestamp</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Amount</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Risk Score</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {accountReport.recent_transactions.map((t, idx) => (
                            <TableRow key={idx}>
                              <TableCell className="font-mono font-bold text-[#002D72]">{t.external_id}</TableCell>
                              <TableCell className="font-mono text-xs text-[#64748B]">
                                {new Date(t.timestamp).toLocaleString()}
                              </TableCell>
                              <TableCell className="text-xs font-medium text-[#0F172A]">{t.transaction_type}</TableCell>
                              <TableCell className="font-mono font-bold text-[#0F172A]">
                                {Number(t.amount).toLocaleString()} {t.currency}
                              </TableCell>
                              <TableCell>
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  t.status === 'COMPLETED' ? 'bg-[#DCFCE7] text-[#15803D]' : 'bg-[#FEE2E2] text-[#DC2626]'
                                }`}>
                                  {t.status}
                                </span>
                              </TableCell>
                              <TableCell className="font-mono text-xs">
                                {t.risk_score ? `${t.risk_score.toFixed(1)}%` : 'N/A'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </div>
                </div>
              )}

              {/* TAB 4: Sandbox Withdrawal Simulator */}
              {activeReportTab === 'simulation' && (
                <div className="space-y-4">
                  <div className="p-4 bg-gradient-to-r from-[#EFF6FF] to-[#DBEAFE]/40 border border-[#BFDBFE] rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <h4 className="font-bold text-[#1E40AF] text-xs uppercase tracking-wider flex items-center gap-2">
                        <Wallet className="w-4 h-4 text-[#2563EB]" />
                        Safe Withdrawal Simulation Sandbox
                      </h4>
                      <p className="text-xs text-[#3B82F6] mt-1">
                        Simulate atomic withdrawals on synthetic test accounts to evaluate 5-minute velocity bursts,
                        amount escalation detection, ledger consistency, and idempotency protection in real time.
                      </p>
                    </div>
                    <Button
                      onClick={handleResetSandbox}
                      variant="outline"
                      size="sm"
                      className="border-[#DC2626] text-[#DC2626] hover:bg-[#FEF2F2] shrink-0 text-xs"
                      leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                    >
                      Reset Sandbox
                    </Button>
                  </div>

                  {/* Preset Scenarios */}
                  <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                    <span className="text-[11px] font-bold text-[#002D72] block mb-2">Preset Test Typologies:</span>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={simRunning}
                        onClick={() => handleRunScenario('normal')}
                        className="text-xs"
                      >
                        1. Normal Withdrawal (500 EGP)
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={simRunning}
                        onClick={() => handleRunScenario('burst')}
                        className="text-xs text-[#B45309]"
                      >
                        2. 5-Min Velocity Burst (3x Rapid)
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={simRunning}
                        onClick={() => handleRunScenario('escalation')}
                        className="text-xs text-[#DC2626]"
                      >
                        3. Amount Escalation (100 → 500 → 5,000)
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={simRunning}
                        onClick={() => handleRunScenario('insufficient')}
                        className="text-xs text-[#64748B]"
                      >
                        4. Insufficient Balance Check
                      </Button>
                    </div>
                    {scenarioStatus && (
                      <p className="mt-2 text-xs font-mono font-medium text-[#1E40AF] bg-[#EFF6FF] p-2 rounded-lg border border-[#DBEAFE]">
                        {scenarioStatus}
                      </p>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="text-[11px] font-bold text-[#475569]">Target Sandbox Account</label>
                      <input
                        type="text"
                        value={simAccount}
                        onChange={(e) => setSimAccount(e.target.value)}
                        className="mt-1 w-full font-mono text-xs p-2 border border-[#CBD5E1] rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-bold text-[#475569]">Withdrawal Amount (EGP)</label>
                      <input
                        type="number"
                        value={simAmount}
                        onChange={(e) => setSimAmount(e.target.value)}
                        className="mt-1 w-full font-mono text-xs p-2 border border-[#CBD5E1] rounded-lg"
                      />
                    </div>
                    <div className="flex items-end">
                      <Button
                        onClick={() => handleExecuteSimulation()}
                        disabled={simRunning}
                        variant="primary"
                        className="w-full h-[38px] text-xs"
                      >
                        {simRunning ? 'Simulating...' : 'Execute Custom Withdrawal'}
                      </Button>
                    </div>
                  </div>

                  {simError && (
                    <div className="p-3 bg-[#FEE2E2] border border-[#FECACA] rounded-lg text-xs text-[#DC2626] flex items-center gap-2">
                      <XCircle className="w-4 h-4 shrink-0" />
                      <span>{simError}</span>
                    </div>
                  )}

                  {simResult && (
                    <div className="p-4 bg-white border border-[#CBD5E1] rounded-xl space-y-3 shadow-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-[#002D72] text-xs">Simulation Succeeded</span>
                        <span className="font-mono text-[11px] bg-[#DCFCE7] text-[#15803D] px-2 py-0.5 rounded font-bold">
                          {simResult.status}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                        <div>
                          <span className="text-[10px] text-[#64748B]">Transaction ID:</span>
                          <p className="font-mono font-bold text-[#002D72]">{simResult.transaction_id}</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-[#64748B]">New Ledger Balance:</span>
                          <p className="font-mono font-bold text-[#0F172A]">{Number(simResult.new_balance).toLocaleString()} EGP</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-[#64748B]">Audit Event ID:</span>
                          <p className="font-mono text-[11px] text-[#475569]">{simResult.audit_event_id}</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-[#64748B]">Triggered Rules:</span>
                          <p className="font-bold text-[#DC2626]">{simResult.triggered_rules.length} rule(s)</p>
                        </div>
                      </div>

                      {/* Direct Action: Investigate in Forensic Workbench */}
                      <div className="pt-2 border-t border-[#E2E8F0] flex items-center justify-between">
                        <span className="text-[11px] text-[#64748B]">
                          Synthetic transaction registered in database.
                        </span>
                        <Button
                          size="sm"
                          variant="primary"
                          className="bg-[#002D72] hover:bg-[#001D4D] text-white text-xs"
                          leftIcon={<ExternalLink className="w-3.5 h-3.5 text-[#F9A825]" />}
                          onClick={() => {
                            setIsAccountModalOpen(false);
                            navigate(`/admin/transactions/${simResult.transaction_id}`);
                          }}
                        >
                          Investigate in Forensic Workbench
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between shrink-0">
              <span className="text-[11px] text-[#64748B]">
                Cryptographic Provenance Verified • SHA-256 Locators Enforced
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAccountModalOpen(false)}
              >
                Close Dossier
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
