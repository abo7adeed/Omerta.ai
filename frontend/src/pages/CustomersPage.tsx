import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  Search,
  UserPlus,
  CheckCircle2,
  Mail,
  Key,
  PhoneCall,
  Unlock,
  Trash2,
  ShieldAlert,
  ArrowUpRight,
  Wallet,
  Bot,
} from 'lucide-react';
import { api } from '../api/client';
import type { CustomerItem } from '../types';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { RiskBadge } from '../components/ui/RiskBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { Tabs } from '../components/ui/Tabs';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

interface StaffUser {
  id: string;
  user_id: number;
  full_name: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  is_super_admin?: boolean;
  can_delete?: boolean;
  privileges: string[];
  created_at: string | null;
}

const PRIVILEGE_DEFINITIONS: Record<string, { label: string; desc: string }> = {
  manage_users: {
    label: 'User Management',
    desc: 'Activate, suspend, and manage customer profiles',
  },
  review_flagged_transactions: {
    label: 'Flagged Reviews',
    desc: 'Review transactions exceeding risk threshold (> 40.00)',
  },
  adjust_balances: {
    label: 'Balance Adjustments',
    desc: 'Execute ledger-backed balance adjustments',
  },
  view_audit_logs: {
    label: 'Audit & Telemetry',
    desc: 'Inspect security sessions and immutable audit events',
  },
  export_reports: {
    label: 'Compliance Reports',
    desc: 'Generate & export regulatory SAR / AML reports',
  },
  manage_staff: {
    label: 'Staff Administration',
    desc: 'Create and assign privileges to sub-admin accounts',
  },
};

export const CustomersPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'customers' | 'problem_customers' | 'staff'>('customers');

  // Customers state
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedCustomer, setSelectedCustomer] = useState<any | null>(null);

  // Problem customers state
  const [problemCustomers, setProblemCustomers] = useState<any[]>([]);
  const [loadingProblems, setLoadingProblems] = useState(false);
  const [problemSearch, setProblemSearch] = useState('');
  const [callModalCust, setCallModalCust] = useState<any | null>(null);
  const [emailModalCust, setEmailModalCust] = useState<any | null>(null);
  const [emailSubject, setEmailSubject] = useState('Omerta.ai Security Clearance: Action Required');
  const [emailBody, setEmailBody] = useState('');
  const [emailSubmitting, setEmailSubmitting] = useState(false);
  const [custAgenticModal, setCustAgenticModal] = useState<any | null>(null);
  const [custAgenticLoading, setCustAgenticLoading] = useState(false);

  // Staff state
  const [staffList, setStaffList] = useState<StaffUser[]>([]);
  const [staffLoading, setStaffLoading] = useState(false);
  const [createStaffOpen, setCreateStaffOpen] = useState(false);
  const [staffSuccess, setStaffSuccess] = useState<string | null>(null);
  const [staffError, setStaffError] = useState<string | null>(null);
  const [isSubmittingStaff, setIsSubmittingStaff] = useState(false);

  const navigate = useNavigate();

  // New staff form data
  const [newStaff, setNewStaff] = useState({
    full_name: '',
    email: '',
    username: '',
    password: '',
    role: 'ADMINISTRATOR',
    privileges: [
      'manage_users',
      'review_flagged_transactions',
      'adjust_balances',
      'view_audit_logs',
      'export_reports',
      'manage_staff',
    ],
  });

  const fetchCustomers = async () => {
    setLoading(true);
    try {
      const res = await api.getCustomers({
        search,
        customer_type: typeFilter,
        risk_level: riskFilter,
        page,
        page_size: 20,
      });
      setCustomers(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load customers', err);
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

  const fetchStaff = async () => {
    setStaffLoading(true);
    try {
      const res = await api.getAdminStaff();
      setStaffList(res || []);
    } catch {
      setStaffList([
        {
          id: 'USR-ADMIN',
          user_id: 1,
          full_name: 'Dr. Sarah Al-Rashid',
          email: 'admin@omerta.ai',
          username: 'admin@omerta.ai',
          role: 'ADMINISTRATOR',
          is_active: true,
          is_super_admin: true,
          can_delete: false,
          privileges: [
            'manage_users',
            'review_flagged_transactions',
            'adjust_balances',
            'view_audit_logs',
            'export_reports',
            'manage_staff',
          ],
          created_at: new Date().toISOString(),
        },
        {
          id: 'USR-ANALYST',
          user_id: 2,
          full_name: 'Tariq Mansour',
          email: 'analyst@omerta.ai',
          username: 'analyst@omerta.ai',
          role: 'FRAUD_ANALYST',
          is_active: true,
          is_super_admin: false,
          can_delete: true,
          privileges: ['review_flagged_transactions', 'view_audit_logs', 'export_reports'],
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setStaffLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'customers') {
      fetchCustomers();
    } else if (activeTab === 'problem_customers') {
      fetchProblemCustomers();
    } else {
      fetchStaff();
    }
  }, [activeTab, page, typeFilter, riskFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchCustomers();
  };

  const handleOpen360 = async (c: CustomerItem) => {
    try {
      const res = await api.getCustomer360(c.external_id);
      setSelectedCustomer(res);
    } catch (err) {
      console.error('Failed to load customer 360', err);
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
      setStaffSuccess(`Risk successfully cleared for ${name}. Account restored to LOW risk.`);
      fetchProblemCustomers();
    } catch (err: any) {
      alert(err.message || 'Failed to resolve customer risk.');
    }
  };

  const handleOpenCallModal = (c: any) => {
    setCallModalCust(c);
  };

  const handleOpenEmailModal = (c: any) => {
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
      setStaffSuccess(`Security notice sent to ${emailModalCust.name} (${emailModalCust.email}).`);
      setEmailModalCust(null);
    } catch (err: any) {
      alert(err.message || 'Failed to send security notice.');
    } finally {
      setEmailSubmitting(false);
    }
  };

  const handleOpenCustomerAgenticModal = async (c: any) => {
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

  const handleDeleteStaff = async (userId: string, fullName: string) => {
    if (
      !confirm(
        `Are you sure you want to revoke and delete staff account for ${fullName}? This will immediately terminate all active sessions.`
      )
    ) {
      return;
    }
    try {
      await api.deleteAdminStaff(userId);
      setStaffSuccess(`Staff account for '${fullName}' has been revoked and deactivated.`);
      fetchStaff();
    } catch (err: any) {
      alert(err.message || 'Failed to revoke staff account.');
    }
  };

  const handleTogglePrivilege = (priv: string) => {
    setNewStaff((prev) => {
      const exists = prev.privileges.includes(priv);
      return {
        ...prev,
        privileges: exists ? prev.privileges.filter((p) => p !== priv) : [...prev.privileges, priv],
      };
    });
  };

  const handleCreateStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStaff.full_name || !newStaff.email || !newStaff.username || !newStaff.password) {
      setStaffError('Please complete all required fields.');
      return;
    }
    if (newStaff.password.length < 8) {
      setStaffError('Password must be at least 8 characters long.');
      return;
    }

    setIsSubmittingStaff(true);
    setStaffError(null);
    setStaffSuccess(null);

    try {
      await api.createAdminStaff(newStaff);
      setStaffSuccess(`Staff account '${newStaff.full_name}' (${newStaff.role}) created successfully.`);
      setCreateStaffOpen(false);
      setNewStaff({
        full_name: '',
        email: '',
        username: '',
        password: '',
        role: 'ADMINISTRATOR',
        privileges: [
          'manage_users',
          'review_flagged_transactions',
          'adjust_balances',
          'view_audit_logs',
          'export_reports',
          'manage_staff',
        ],
      });
      fetchStaff();
    } catch (err: any) {
      setStaffError(err.message || 'Failed to create staff account.');
    } finally {
      setIsSubmittingStaff(false);
    }
  };

  const filteredProblems = problemCustomers.filter(
    (c) =>
      c.name.toLowerCase().includes(problemSearch.toLowerCase()) ||
      c.omerta_user_number.toLowerCase().includes(problemSearch.toLowerCase()) ||
      c.email.toLowerCase().includes(problemSearch.toLowerCase()) ||
      c.phone.includes(problemSearch)
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Banner / Tab header */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <Users className="w-4 h-4" />
            Identity &amp; Entity Directory
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Customer &amp; Staff Administration
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Manage monitored banking customers, security hold clearances, and provision institutional staff RBAC.
          </p>
        </div>

        {activeTab === 'staff' && (
          <Button
            onClick={() => {
              setStaffError(null);
              setCreateStaffOpen(true);
            }}
            variant="primary"
            size="sm"
            leftIcon={<UserPlus className="h-4 w-4" />}
          >
            Provision New Staff
          </Button>
        )}
      </Card>

      {/* Success Notification */}
      {staffSuccess && (
        <div className="p-4 rounded-[12px] bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="h-5 w-5 text-[#10B981] stroke-[2.5]" />
            <span className="text-xs font-bold">{staffSuccess}</span>
          </div>
          <button
            onClick={() => setStaffSuccess(null)}
            className="text-xs font-bold text-[#065F46] hover:underline cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Tabs Container */}
      <Card>
        <div className="px-6 pt-2">
          <Tabs
            tabs={[
              { id: 'customers', label: 'Monitored Customers', count: total, icon: Users },
              { id: 'problem_customers', label: 'Flagged & Locked Accounts', count: problemCustomers.length, icon: ShieldAlert },
              { id: 'staff', label: 'Staff & Roles (RBAC)', count: staffList.length, icon: Key },
            ]}
            activeTab={activeTab}
            onChange={(id) => setActiveTab(id as any)}
          />
        </div>

        <CardContent className="p-0">
          {/* TAB 1: MONITORED CUSTOMERS */}
          {activeTab === 'customers' && (
            <div>
              {/* Search & Filter bar */}
              <div className="p-4 border-b border-[#E0DDD6] bg-[#F4F1EC]/30">
                <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  <div className="lg:col-span-2">
                    <Input
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search customer name, national ID, email, user ID..."
                      leftIcon={<Search className="h-4 w-4 text-[#64748B]" />}
                      className="h-10 text-xs"
                    />
                  </div>
                  <div>
                    <select
                      value={riskFilter}
                      onChange={(e) => {
                        setRiskFilter(e.target.value);
                        setPage(1);
                      }}
                      className="w-full h-10 bg-white border border-[#E0DDD6] rounded-[10px] px-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
                    >
                      <option value="">All Risk Tiers</option>
                      <option value="LOW">Low Risk</option>
                      <option value="MODERATE">Moderate Risk</option>
                      <option value="HIGH">High Risk</option>
                      <option value="CRITICAL">Critical</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button type="submit" variant="sapphire" size="sm" className="h-10 flex-1 text-xs">
                      Search
                    </Button>
                    {(search || riskFilter) && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-10 px-3 text-xs text-[#64748B]"
                        onClick={() => {
                          setSearch('');
                          setRiskFilter('');
                          setPage(1);
                        }}
                      >
                        Reset
                      </Button>
                    )}
                  </div>
                </form>
              </div>

              {/* Customers Table */}
              <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Customer / Entity</TableHead>
                      <TableHead>User Number</TableHead>
                      <TableHead>Type / KYC</TableHead>
                      <TableHead>Risk Score</TableHead>
                      <TableHead>Account Status</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {customers.length > 0 ? (
                      customers.map((c) => (
                        <TableRow
                          key={c.external_id}
                          onClick={() => handleOpen360(c)}
                          className="cursor-pointer"
                        >
                          <TableCell>
                            <div className="font-bold text-[#002D72]">
                              {c.name || `${(c as any).first_name || ''} ${(c as any).last_name || ''}`}
                            </div>
                            <div className="text-[11px] text-[#64748B]">{c.email}</div>
                          </TableCell>
                          <TableCell className="font-mono font-bold text-[#002D72]">
                            {c.omerta_user_number || c.external_id}
                          </TableCell>
                          <TableCell>
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#F4F1EC] text-[#002D72] border border-[#E0DDD6]">
                              {c.customer_type || 'INDIVIDUAL'}
                            </span>
                          </TableCell>
                          <TableCell>
                            <RiskBadge level={c.risk_level || 'LOW'} score={(c as any).risk_score} />
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={c.status || 'ACTIVE'} />
                          </TableCell>
                          <TableCell className="text-xs font-mono text-[#64748B]">
                            {c.created_at ? new Date(c.created_at).toLocaleDateString() : 'N/A'}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpen360(c);
                              }}
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2 text-[#002D72]"
                              title="Inspect Customer 360 Profile"
                            >
                              <ArrowUpRight className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-12 text-xs text-[#64748B]">
                          {loading ? 'Scanning customer database...' : 'No customers matching filters.'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
          )}

          {/* TAB 2: PROBLEM CUSTOMERS */}
          {activeTab === 'problem_customers' && (
            <div>
              <div className="p-4 border-b border-[#E0DDD6] bg-[#F4F1EC]/30 flex flex-wrap items-center justify-between gap-3">
                <div className="relative w-72">
                  <Input
                    value={problemSearch}
                    onChange={(e) => setProblemSearch(e.target.value)}
                    placeholder="Search name, phone, user number..."
                    leftIcon={<Search className="w-4 h-4 text-[#64748B]" />}
                    className="h-9 text-xs"
                  />
                </div>
                <div className="text-xs text-[#64748B] font-medium">
                  Showing <span className="font-bold text-[#002D72]">{filteredProblems.length}</span> locked customer accounts
                </div>
              </div>

              <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Customer</TableHead>
                      <TableHead>User Number</TableHead>
                      <TableHead>Risk Level</TableHead>
                      <TableHead>Hold Trigger</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredProblems.length > 0 ? (
                      filteredProblems.map((cust) => (
                        <TableRow
                          key={cust.customer_id}
                          onClick={() => handleOpenCustomerAgenticModal(cust)}
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
                              {cust.primary_reason || 'Verification threshold breached'}
                            </div>
                            <div className="text-[11px] text-[#64748B]">
                              Failed passwords: {cust.failed_transfer_passwords_count || 3}
                            </div>
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={cust.status || 'SECURITY_HOLD'} />
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                              <Button
                                onClick={() => handleOpenCallModal(cust)}
                                variant="secondary"
                                size="sm"
                                className="h-8 px-2 text-xs"
                                title="Call customer to verify identity"
                              >
                                <PhoneCall className="w-3.5 h-3.5 text-[#002D72]" />
                              </Button>
                              <Button
                                onClick={() => handleOpenEmailModal(cust)}
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
                                <span>Resolve Risk</span>
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-12 text-xs text-[#64748B]">
                          {loadingProblems ? 'Loading accounts on hold...' : 'No customer accounts on security hold.'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
          )}

          {/* TAB 3: STAFF & RBAC MANAGEMENT */}
          {activeTab === 'staff' && (
            <div>
              <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Staff Member</TableHead>
                      <TableHead>Institutional Role</TableHead>
                      <TableHead>Active Privileges</TableHead>
                      <TableHead>Session Status</TableHead>
                      <TableHead className="text-right">Revoke / Manage</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {staffList.map((staff) => (
                      <TableRow key={staff.id || staff.user_id}>
                        <TableCell>
                          <div className="font-bold text-[#002D72]">{staff.full_name}</div>
                          <div className="text-[11px] text-[#64748B] font-mono">{staff.email}</div>
                        </TableCell>
                        <TableCell>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#EBF3FC] text-[#002D72] border border-[#BFDBFE]">
                            {staff.role?.replace(/_/g, ' ')}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1 max-w-sm">
                            {staff.privileges?.map((priv) => (
                              <span
                                key={priv}
                                className="text-[10px] font-semibold bg-[#F4F1EC] text-[#475569] border border-[#E0DDD6] px-1.5 py-0.5 rounded"
                              >
                                {PRIVILEGE_DEFINITIONS[priv]?.label || priv}
                              </span>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={staff.is_active ? 'ACTIVE' : 'INACTIVE'} />
                        </TableCell>
                        <TableCell className="text-right">
                          {staff.can_delete !== false ? (
                            <Button
                              onClick={() => handleDeleteStaff(staff.id, staff.full_name)}
                              variant="danger"
                              size="sm"
                              className="h-8 px-2 text-xs"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              <span>Revoke</span>
                            </Button>
                          ) : (
                            <span className="text-[11px] font-bold text-[#64748B] uppercase">Primary Admin</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* MODAL 1: CUSTOMER 360 DOSSIER */}
      {selectedCustomer && (
        <Modal
          isOpen={Boolean(selectedCustomer)}
          onClose={() => setSelectedCustomer(null)}
          title={`Customer 360: ${selectedCustomer.first_name || ''} ${selectedCustomer.last_name || ''}`}
          subtitle={`User ID: ${selectedCustomer.omerta_user_number || selectedCustomer.external_id}`}
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-[#F4F1EC] p-3.5 rounded-[12px] border border-[#E0DDD6]">
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Risk Status</span>
                <div className="mt-0.5">
                  <RiskBadge level={selectedCustomer.risk_level || 'LOW'} score={selectedCustomer.risk_score} />
                </div>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Account State</span>
                <div className="mt-0.5">
                  <StatusBadge status={selectedCustomer.status || 'ACTIVE'} />
                </div>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Phone</span>
                <p className="font-mono font-bold text-[#002D72] mt-0.5">{selectedCustomer.phone || 'N/A'}</p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Email</span>
                <p className="truncate font-semibold text-[#002D72] mt-0.5">{selectedCustomer.email}</p>
              </div>
            </div>

            {/* Linked Accounts */}
            <div className="space-y-2">
              <h5 className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider">
                Linked Banking Accounts
              </h5>
              {selectedCustomer.accounts?.length > 0 ? (
                <div className="space-y-1.5">
                  {selectedCustomer.accounts.map((acc: any) => (
                    <div
                      key={acc.account_id || acc.account_number}
                      className="p-3 bg-white rounded-[10px] border border-[#E0DDD6] flex items-center justify-between shadow-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <Wallet className="h-4 w-4 text-[#002D72]" />
                        <div>
                          <p className="font-mono font-bold text-[#002D72]">{acc.account_number}</p>
                          <p className="text-[11px] text-[#64748B]">{acc.account_type || 'CURRENT'}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-mono font-bold text-[#002D72]">
                          {Number(acc.balance || 0).toLocaleString()} {acc.currency || 'EGP'}
                        </p>
                        <StatusBadge status={acc.status || 'ACTIVE'} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[#64748B]">No registered bank accounts.</p>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-[#E0DDD6]">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setSelectedCustomer(null)}
              >
                Close
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  const id = selectedCustomer.omerta_user_number || selectedCustomer.external_id;
                  setSelectedCustomer(null);
                  navigate(`/admin/network-analysis?entity=${encodeURIComponent(id)}`);
                }}
              >
                <span>Inspect Entity Graph</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 2: PROVISION NEW STAFF */}
      {createStaffOpen && (
        <Modal
          isOpen={createStaffOpen}
          onClose={() => setCreateStaffOpen(false)}
          title="Provision Institutional Staff User (RBAC)"
          subtitle="Create new sub-administrator, fraud analyst, or compliance auditor"
          maxWidth="lg"
        >
          <form onSubmit={handleCreateStaff} className="space-y-4 text-xs">
            {staffError && (
              <div className="p-3 rounded-[10px] bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B]">
                {staffError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Full Name"
                required
                value={newStaff.full_name}
                onChange={(e) => setNewStaff({ ...newStaff, full_name: e.target.value })}
                placeholder="e.g. Omar Hassan"
              />
              <Input
                label="Corporate Email"
                type="email"
                required
                value={newStaff.email}
                onChange={(e) => setNewStaff({ ...newStaff, email: e.target.value, username: e.target.value })}
                placeholder="e.g. omar@omerta.ai"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Initial Password (Min 8 Chars)"
                type="password"
                required
                value={newStaff.password}
                onChange={(e) => setNewStaff({ ...newStaff, password: e.target.value })}
                placeholder="••••••••••••"
              />
              <Select
                label="System Role"
                value={newStaff.role}
                onChange={(e) => setNewStaff({ ...newStaff, role: e.target.value })}
              >
                <option value="ADMINISTRATOR">Administrator</option>
                <option value="SUB_ADMINISTRATOR">Sub-Administrator</option>
                <option value="SENIOR_INVESTIGATOR">Senior Investigator</option>
                <option value="FRAUD_ANALYST">Fraud Analyst</option>
                <option value="COMPLIANCE_AUDITOR">Compliance Auditor</option>
              </Select>
            </div>

            {/* Privilege Checkboxes */}
            <div className="space-y-2 pt-2 border-t border-[#E0DDD6]">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#475569]">
                Assign RBAC Functional Privileges
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {Object.entries(PRIVILEGE_DEFINITIONS).map(([key, def]) => {
                  const checked = newStaff.privileges.includes(key);
                  return (
                    <label
                      key={key}
                      onClick={() => handleTogglePrivilege(key)}
                      className={`p-2.5 rounded-[10px] border cursor-pointer flex items-start gap-2.5 transition-colors ${
                        checked
                          ? 'bg-[#FFF9E6] border-[#FFE082]'
                          : 'bg-white border-[#E0DDD6] hover:bg-[#F4F1EC]'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {}}
                        className="mt-0.5 rounded text-[#002D72] focus:ring-[#1E88E5]"
                      />
                      <div>
                        <p className="font-bold text-[#002D72] text-xs">{def.label}</p>
                        <p className="text-[10px] text-[#64748B] leading-tight">{def.desc}</p>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setCreateStaffOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                isLoading={isSubmittingStaff}
              >
                <UserPlus className="w-4 h-4" />
                <span>Create Staff User</span>
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL 3: PHONE VERIFICATION */}
      {callModalCust && (
        <Modal
          isOpen={Boolean(callModalCust)}
          onClose={() => setCallModalCust(null)}
          title="Direct Identity Verification"
          subtitle={`Verify identity for ${callModalCust.name}`}
          maxWidth="md"
        >
          <div className="space-y-4 text-xs">
            <div className="p-3.5 rounded-[12px] bg-[#EBF3FC] border border-[#BFDBFE] text-[#002D72] flex items-start gap-3">
              <PhoneCall className="w-5 h-5 text-[#002D72] shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-sm">Customer Hotline: {callModalCust.phone || '+20 100 123 4567'}</p>
                <p className="text-xs text-[#475569] mt-0.5">
                  Confirm secret security question and registered device before unlocking access.
                </p>
              </div>
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
                <span>Identity Verified — Unlock</span>
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 4: SEND EMAIL NOTICE */}
      {emailModalCust && (
        <Modal
          isOpen={Boolean(emailModalCust)}
          onClose={() => setEmailModalCust(null)}
          title="Send Compliance Notice"
          subtitle={`Send to ${emailModalCust.email}`}
          maxWidth="lg"
        >
          <form onSubmit={handleSendEmailNotice} className="space-y-4 text-xs">
            <Input
              label="Subject"
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
                <span>Send Notice</span>
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL 5: CUSTOMER AGENTIC FORENSIC MODAL */}
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
