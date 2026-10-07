import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Wallet,
  Send,
  ArrowUpRight,
  ArrowDownLeft,
  Eye,
  EyeOff,
  Copy,
  Check,
  ShieldCheck,
  TrendingUp,
  CreditCard,
  Clock,
  ChevronRight,
  AlertCircle,
  AlertTriangle,
  Loader2,
  LifeBuoy,
  KeyRound,
  Lock,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import {
  Card,
  Button,
  Input,
  StatusBadge,
  Modal,
  Alert,
} from '../../components/ui';

export const CustomerDashboardPage: React.FC = () => {
  const { user, customer } = useAuth();
  const navigate = useNavigate();

  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showBalance, setShowBalance] = useState(true);
  const [copied, setCopied] = useState(false);

  // Transfer Blocked Intercept Modal State
  const [showTransferBlockedModal, setShowTransferBlockedModal] = useState(false);

  // Recovery & Change Transfer Password Modal State
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [newTransferPassword, setNewTransferPassword] = useState('');
  const [confirmTransferPassword, setConfirmTransferPassword] = useState('');
  const [currentTransferPassword, setCurrentTransferPassword] = useState('');
  const [showPasswordText, setShowPasswordText] = useState(false);
  const [passwordModalLoading, setPasswordModalLoading] = useState(false);
  const [passwordModalError, setPasswordModalError] = useState<string | null>(null);
  const [passwordModalSuccess, setPasswordModalSuccess] = useState(false);

  const fetchDashboard = async () => {
    setIsLoading(true);
    try {
      const res = await api.getCustomerDashboard();
      setData(res);
      if (res?.customer?.require_transfer_password_change) {
        setShowPasswordModal(true);
      }
    } catch {
      // Fallback state if server is offline
      setData({
        customer: {
          name: customer?.name || user?.full_name || 'Customer',
          omerta_user_number: customer?.omerta_user_number || 'OMR-1092-4821',
          preferred_currency: 'EGP',
          status: 'ACTIVE',
          transfer_status: customer?.transfer_status || 'ACTIVE',
          identity_status: customer?.identity_status || 'VERIFIED',
          require_transfer_password_change: customer?.require_transfer_password_change || false,
        },
        accounts: [
          { account_id: 'ACC-1001', account_type: 'CHECKING', currency: 'EGP', balance: 50000.0, status: 'ACTIVE' },
        ],
        balances: { EGP: 50000.0 },
        activity: { incoming_volume: 12500.0, outgoing_volume: 1500.0, incoming_count: 3, outgoing_count: 1, total_transactions: 4 },
        recent_transactions: [],
      });
      if (customer?.require_transfer_password_change) {
        setShowPasswordModal(true);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const handleCopyUserNumber = () => {
    const num = data?.customer?.omerta_user_number || customer?.omerta_user_number;
    if (num) {
      navigator.clipboard.writeText(num);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleChangeTransferPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordModalError(null);

    if (!newTransferPassword) {
      setPasswordModalError('Please enter a new transfer password.');
      return;
    }
    if (newTransferPassword.length < 8) {
      setPasswordModalError('Transfer password must be at least 8 characters long.');
      return;
    }
    if (newTransferPassword !== confirmTransferPassword) {
      setPasswordModalError('New transfer password and confirmation do not match.');
      return;
    }

    setPasswordModalLoading(true);
    try {
      await api.changeTransferPassword({
        new_transfer_password: newTransferPassword,
        confirm_transfer_password: confirmTransferPassword,
        current_transfer_password: currentTransferPassword.trim() || undefined,
      });

      setPasswordModalSuccess(true);
      setTimeout(() => {
        setShowPasswordModal(false);
        setPasswordModalSuccess(false);
        setNewTransferPassword('');
        setConfirmTransferPassword('');
        setCurrentTransferPassword('');
        fetchDashboard();
      }, 1800);
    } catch (err: any) {
      setPasswordModalError(err.message || 'Failed to update transfer password. Please try again.');
    } finally {
      setPasswordModalLoading(false);
    }
  };

  const primaryAccount = data?.accounts?.[0] || { balance: 0, currency: 'EGP', account_id: 'ACC-DEMO' };
  const isTransferBlocked = data?.customer?.transfer_status === 'BLOCKED';
  const isPasswordChangeRequired = Boolean(data?.customer?.require_transfer_password_change);

  const handleTransferButtonClick = () => {
    if (isTransferBlocked) {
      setShowTransferBlockedModal(true);
      return;
    }
    if (isPasswordChangeRequired) {
      setShowPasswordModal(true);
      return;
    }
    navigate('/customer/transfer');
  };

  if (isLoading && !data) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-[var(--color-text-secondary)]">
        <Loader2 className="h-10 w-10 animate-spin text-[var(--color-sapphire)] mb-4" />
        <p className="text-sm font-semibold text-[var(--color-sapphire)]">Loading customer dashboard...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome & Status Banner */}
      <Card className="p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-sapphire)]">
              Welcome back, {data?.customer?.name || user?.full_name || 'Customer'}
            </h1>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300">
              Verified Client
            </span>
            {isTransferBlocked ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-rose-100 text-rose-800 border border-rose-300">
                <AlertCircle className="w-3.5 h-3.5" /> Transfer Blocked
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-blue-100 text-[var(--color-sapphire)] border border-blue-200">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Transfer Active
              </span>
            )}
          </div>
          <p className="text-xs text-[var(--color-text-secondary)] font-medium">
            Simulated digital banking overview, support desk &amp; peer-to-peer transfers
          </p>
        </div>

        {/* Shareable Omerta User Number */}
        <div className="flex items-center gap-3 p-3.5 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] shrink-0">
          <div className="flex flex-col">
            <span className="text-[11px] uppercase font-bold tracking-wider text-[var(--color-text-muted)]">Your Omerta User #</span>
            <span className="font-mono text-sm font-extrabold text-[var(--color-sapphire)]">
              {data?.customer?.omerta_user_number || customer?.omerta_user_number || 'OMR-1092-4821'}
            </span>
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={handleCopyUserNumber}
            className="px-3 min-h-[36px]"
            title="Share this unique number with other registered users to receive funds"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-600 mr-1" />
                <span className="text-emerald-700 font-bold">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5 text-[var(--color-sapphire)] mr-1" />
                <span>Copy</span>
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* SECURITY HOLD BANNER (If Transfer Blocked) */}
      {isTransferBlocked && (
        <Card className="p-6 bg-rose-50/90 border-rose-300 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-rose-100 text-rose-700 shrink-0 mt-0.5">
              <AlertTriangle className="h-6 w-6 stroke-[2.2]" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-rose-950">
                Security Hold: Money Transfers Restricted
              </h3>
              <p className="text-xs text-rose-900 leading-relaxed font-medium max-w-2xl">
                Your transfer password was entered incorrectly 3 consecutive times. Your session and dashboard access remain active, but money movement is locked. Please open a support ticket to verify your National ID and restore transfer privileges.
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="danger"
            size="sm"
            onClick={() => navigate('/customer/support?reason=TRANSFER_BLOCKED')}
            className="shrink-0"
          >
            <LifeBuoy className="h-4 w-4 mr-1.5" />
            <span>Open Support Ticket</span>
            <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
          </Button>
        </Card>
      )}

      {/* ACTION REQUIRED: RESTORE PASSWORD CHANGE BANNER */}
      {isPasswordChangeRequired && (
        <Card className="p-6 bg-amber-50/90 border-amber-300 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-amber-100 text-amber-800 shrink-0 mt-0.5">
              <KeyRound className="h-6 w-6 stroke-[2.2]" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-amber-950">
                Action Required: Set New Transfer Password
              </h3>
              <p className="text-xs text-amber-900 leading-relaxed font-medium max-w-2xl">
                Compliance staff has verified your identity and restored your transfer access! To complete account reactivation, please set a new transfer password now.
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => {
              setPasswordModalError(null);
              setShowPasswordModal(true);
            }}
            className="shrink-0"
          >
            <Lock className="h-4 w-4 mr-1.5" />
            <span>Set New Transfer Password</span>
            <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
          </Button>
        </Card>
      )}

      {/* Primary Balance Bento Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Available Balance Card */}
        <Card className="lg:col-span-2 p-6 md:p-8 flex flex-col justify-between min-h-[240px]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-[var(--color-sapphire)] text-[var(--color-gold)] shadow-sm">
                <Wallet className="h-6 w-6 stroke-[2.2]" />
              </div>
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Primary Checking Account</span>
                <p className="text-xs font-mono font-bold text-[var(--color-sapphire)]">{primaryAccount.account_id}</p>
              </div>
            </div>

            <button
              onClick={() => setShowBalance(!showBalance)}
              className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-sapphire)] rounded-lg hover:bg-[var(--color-secondary-surface)] transition-all cursor-pointer"
              title={showBalance ? 'Hide Balance' : 'Show Balance'}
              aria-label={showBalance ? 'Hide Balance' : 'Show Balance'}
            >
              {showBalance ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          {/* Amount Display */}
          <div className="my-5">
            <span className="text-[11px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
              Available Demo Balance
            </span>
            <div className="flex items-baseline gap-2.5">
              {showBalance ? (
                <>
                  <span className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[var(--color-sapphire)] font-mono font-tabular">
                    {primaryAccount.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <span className="text-xl font-bold text-[var(--color-gold)]">{primaryAccount.currency}</span>
                </>
              ) : (
                <span className="text-4xl font-extrabold text-[var(--color-text-muted)] tracking-widest">••••••••••</span>
              )}
            </div>
            <p className="text-xs text-[var(--color-text-secondary)] mt-2 flex items-center gap-1.5 font-medium">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span>Protected with ledger double-entry audit trail</span>
            </p>
          </div>

          {/* Action Row */}
          <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-[var(--color-border)]">
            <Button
              size="sm"
              variant={isTransferBlocked ? 'danger' : 'primary'}
              onClick={handleTransferButtonClick}
            >
              <Send className="h-4 w-4 mr-1.5" />
              <span>{isTransferBlocked ? 'Transfers Blocked (Click for Info)' : 'Send Money'}</span>
            </Button>

            <Button
              size="sm"
              variant="secondary"
              onClick={() => navigate('/customer/accounts')}
            >
              <CreditCard className="h-4 w-4 text-[var(--color-sapphire)] mr-1.5" />
              <span>View All Accounts</span>
            </Button>

            <Button
              size="sm"
              variant="secondary"
              onClick={() => navigate('/customer/support')}
            >
              <LifeBuoy className="h-4 w-4 text-[var(--color-royal-blue)] mr-1.5" />
              <span>Support &amp; Chat</span>
            </Button>

            <Button
              size="sm"
              variant="ghost"
              onClick={() => navigate('/customer/transactions')}
              className="ml-auto"
            >
              <Clock className="h-4 w-4 mr-1.5" />
              <span>History</span>
            </Button>
          </div>
        </Card>

        {/* Activity Summary Card */}
        <Card className="p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-[var(--color-sapphire)] mb-4 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-[var(--color-gold)]" />
              <span>Activity Overview</span>
            </h3>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)]">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700">
                    <ArrowDownLeft className="h-4 w-4 stroke-[2.5]" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-[var(--color-sapphire)] block">Incoming</span>
                    <span className="text-[11px] text-[var(--color-text-muted)] font-medium">{data?.activity?.incoming_count || 0} transfer(s)</span>
                  </div>
                </div>
                <span className="text-sm font-extrabold text-emerald-700 font-mono font-tabular">
                  +{(data?.activity?.incoming_volume || 0).toLocaleString()} {primaryAccount.currency}
                </span>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)]">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-100 text-[var(--color-sapphire)]">
                    <ArrowUpRight className="h-4 w-4 stroke-[2.5]" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-[var(--color-sapphire)] block">Outgoing</span>
                    <span className="text-[11px] text-[var(--color-text-muted)] font-medium">{data?.activity?.outgoing_count || 0} transfer(s)</span>
                  </div>
                </div>
                <span className="text-sm font-extrabold text-[var(--color-sapphire)] font-mono font-tabular">
                  -{(data?.activity?.outgoing_volume || 0).toLocaleString()} {primaryAccount.currency}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[var(--color-border)] flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-semibold">
            <span>Total Transfers</span>
            <span className="font-extrabold text-[var(--color-sapphire)]">{data?.activity?.total_transactions || 0}</span>
          </div>
        </Card>
      </div>

      {/* Recent Customer Transactions */}
      <Card className="p-0 overflow-hidden">
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Clock className="h-5 w-5 text-[var(--color-sapphire)]" />
            <h2 className="text-base font-bold text-[var(--color-sapphire)]">Recent Transactions</h2>
          </div>

          <button
            onClick={() => navigate('/customer/transactions')}
            className="text-xs text-[var(--color-royal-blue)] hover:underline font-semibold flex items-center gap-1 transition-colors cursor-pointer"
          >
            <span>View Full Ledger</span>
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[var(--color-secondary-surface)] border-b border-[var(--color-border)] text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="p-4">Direction</th>
                <th className="p-4">Reference</th>
                <th className="p-4">Counterparty</th>
                <th className="p-4">Amount</th>
                <th className="p-4">Status</th>
                <th className="p-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {data?.recent_transactions?.length > 0 ? (
                data.recent_transactions.map((t: any) => (
                  <tr key={t.transaction_id} className="hover:bg-[var(--color-hover-surface)] transition-colors">
                    <td className="p-4">
                      {t.direction === 'INCOMING' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 font-bold text-[11px] border border-emerald-200">
                          <ArrowDownLeft className="h-3.5 w-3.5 text-emerald-600" /> Incoming
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 text-[var(--color-sapphire)] font-bold text-[11px] border border-blue-200">
                          <ArrowUpRight className="h-3.5 w-3.5 text-[var(--color-royal-blue)]" /> Outgoing
                        </span>
                      )}
                    </td>
                    <td className="p-4 font-mono text-[var(--color-text-secondary)] font-bold">{t.transaction_id}</td>
                    <td className="p-4 font-semibold text-[var(--color-text-primary)]">{t.counterparty}</td>
                    <td className="p-4 font-mono font-bold font-tabular text-[var(--color-sapphire)]">
                      {t.direction === 'INCOMING' ? '+' : '-'}
                      {t.amount?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {t.currency}
                    </td>
                    <td className="p-4">
                      <StatusBadge status={t.status} />
                    </td>
                    <td className="p-4 text-[var(--color-text-secondary)] font-medium whitespace-nowrap">
                      {new Date(t.timestamp).toLocaleDateString()} {new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="p-10 text-center text-[var(--color-text-secondary)] font-medium">
                    No transactions yet. Click &quot;Send Money&quot; to test your first simulated transfer!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* CHANGE / SET NEW TRANSFER PASSWORD MODAL */}
      {showPasswordModal && (
        <Modal
          isOpen={showPasswordModal}
          onClose={() => {
            if (!isPasswordChangeRequired) setShowPasswordModal(false);
          }}
          title={isPasswordChangeRequired ? 'Set New Transfer Password' : 'Change Transfer Password'}
          subtitle={
            isPasswordChangeRequired
              ? 'Compliance Restoration: Please set a new transfer password to complete reactivation'
              : 'Update your dedicated money movement authorization password'
          }
          maxWidth="md"
        >
          <form onSubmit={handleChangeTransferPassword} className="space-y-4 text-xs">
            {passwordModalSuccess ? (
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 flex items-center gap-3">
                <Check className="w-6 h-6 shrink-0 text-emerald-600 stroke-[3]" />
                <div className="space-y-0.5">
                  <p className="font-bold text-emerald-950 text-sm">Transfer Password Updated Successfully!</p>
                  <p className="text-xs text-emerald-800 font-medium">
                    Your transfer access is now ACTIVE. You can make money transfers freely.
                  </p>
                </div>
              </div>
            ) : (
              <>
                {passwordModalError && (
                  <Alert
                    variant="danger"
                    icon={<AlertCircle className="w-4 h-4" />}
                    message={passwordModalError}
                  />
                )}

                {!isPasswordChangeRequired && (
                  <Input
                    label="Current Transfer Password"
                    type={showPasswordText ? 'text' : 'password'}
                    value={currentTransferPassword}
                    onChange={(e) => setCurrentTransferPassword(e.target.value)}
                    placeholder="Enter current transfer password"
                  />
                )}

                <Input
                  label="New Transfer Password (Min 8 Characters)"
                  type={showPasswordText ? 'text' : 'password'}
                  required
                  value={newTransferPassword}
                  onChange={(e) => setNewTransferPassword(e.target.value)}
                  placeholder="Enter new transfer password"
                  icon={
                    <button
                      type="button"
                      onClick={() => setShowPasswordText(!showPasswordText)}
                      className="p-1 hover:text-[var(--color-sapphire)] cursor-pointer"
                    >
                      {showPasswordText ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  }
                />

                <Input
                  label="Confirm New Transfer Password"
                  type={showPasswordText ? 'text' : 'password'}
                  required
                  value={confirmTransferPassword}
                  onChange={(e) => setConfirmTransferPassword(e.target.value)}
                  placeholder="Repeat new transfer password"
                />

                <div className="flex items-center justify-end gap-3 pt-3">
                  {!isPasswordChangeRequired && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowPasswordModal(false)}
                    >
                      Cancel
                    </Button>
                  )}
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={passwordModalLoading}
                  >
                    <ShieldCheck className="w-4 h-4 mr-1.5" />
                    <span>Save Transfer Password</span>
                  </Button>
                </div>
              </>
            )}
          </form>
        </Modal>
      )}

      {/* TRANSFER BLOCKED INTERCEPT MODAL */}
      {showTransferBlockedModal && (
        <Modal
          isOpen={showTransferBlockedModal}
          onClose={() => setShowTransferBlockedModal(false)}
          title="Transfer Access Restricted"
          subtitle="Security Hold Enforced (3 Failed Password Attempts)"
          maxWidth="md"
        >
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-rose-950 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 shrink-0 text-rose-600 mt-0.5" />
              <div className="space-y-1">
                <p className="font-bold text-rose-950 text-sm">Transfers Locked Due to 3 Incorrect Attempts</p>
                <p className="text-rose-900 leading-relaxed text-xs font-medium">
                  You entered your transfer password incorrectly 3 times. For your security, money movement is locked. Your account login remains active.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-2">
              <span className="text-[11px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">How to Restore Privileges</span>
              <ul className="list-disc pl-4 space-y-1.5 text-xs text-[var(--color-text-secondary)] font-medium">
                <li>Open a support ticket with the Helpdesk.</li>
                <li>Upload a clear photo of your National ID or Passport (Front &amp; Back).</li>
                <li>Compliance officers will verify your account ownership and restore your transfer access.</li>
              </ul>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setShowTransferBlockedModal(false)}
              >
                Close
              </Button>
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={() => {
                  setShowTransferBlockedModal(false);
                  navigate('/customer/support?reason=TRANSFER_BLOCKED');
                }}
              >
                <LifeBuoy className="w-4 h-4 mr-1.5" />
                <span>Go to Support &amp; Verify ID</span>
                <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Demo Disclaimer Footer */}
      <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 flex items-center gap-3 text-xs text-[var(--color-text-secondary)]">
        <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
        <span className="font-medium">
          <strong className="text-[var(--color-sapphire)]">Demo Banking Environment:</strong> Omerta.ai is a simulation environment for financial crime intelligence and compliance testing. Balances and transfers do not represent real funds.
        </span>
      </div>
    </div>
  );
};
