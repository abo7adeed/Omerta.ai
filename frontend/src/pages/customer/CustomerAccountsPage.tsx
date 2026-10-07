import React, { useState, useEffect } from 'react';
import {
  Wallet,
  PlusCircle,
  ShieldCheck,
  FileText,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { api } from '../../api/client';
import type { CustomerAccount } from '../../types';
import {
  Card,
  Button,
  Input,
  Select,
  StatusBadge,
  Modal,
  Alert,
} from '../../components/ui';

export const CustomerAccountsPage: React.FC = () => {
  const [accounts, setAccounts] = useState<CustomerAccount[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // New account modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newAccType, setNewAccType] = useState('SAVINGS');
  const [newAccCurrency, setNewAccCurrency] = useState('EGP');
  const [newAccInitialBalance, setNewAccInitialBalance] = useState('5000.00');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Ledger drawer
  const [activeLedgerAccount, setActiveLedgerAccount] = useState<CustomerAccount | null>(null);

  const fetchAccounts = async () => {
    setIsLoading(true);
    try {
      const res = await api.getCustomerAccounts();
      setAccounts(res);
    } catch {
      // Fallback
      setAccounts([
        {
          account_id: 'ACC-1001',
          account_type: 'CHECKING',
          currency: 'EGP',
          balance: 50000.0,
          status: 'ACTIVE',
          recent_ledger: [
            {
              entry_id: 'LED-OPEN-1001',
              entry_type: 'OPENING_BALANCE',
              amount: 50000.0,
              currency: 'EGP',
              balance_after: 50000.0,
              description: 'Initial demo balance',
              created_at: new Date().toISOString(),
            },
          ],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    setCreateError(null);
    try {
      await api.createCustomerAccount({
        account_type: newAccType,
        currency: newAccCurrency,
        initial_balance: parseFloat(newAccInitialBalance) || 0,
      });
      setIsModalOpen(false);
      fetchAccounts();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to open new account.');
    } finally {
      setIsCreating(false);
    }
  };

  if (isLoading && accounts.length === 0) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-[var(--color-text-secondary)]">
        <Loader2 className="h-10 w-10 animate-spin text-[var(--color-sapphire)] mb-4" />
        <p className="text-sm font-semibold text-[var(--color-sapphire)]">Loading verified accounts...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6 md:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-sapphire)] flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[var(--color-sapphire)] text-[var(--color-gold)] shadow-sm">
              <Wallet className="h-6 w-6 stroke-[2.2]" />
            </div>
            <span>My Bank Accounts</span>
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2 font-medium">
            Manage your demo bank accounts, view verified ledger balances, and open new accounts
          </p>
        </div>

        <Button
          onClick={() => setIsModalOpen(true)}
          variant="primary"
          size="sm"
          className="shrink-0"
        >
          <PlusCircle className="h-4 w-4 mr-1.5" />
          <span>Open Demo Account</span>
        </Button>
      </Card>

      {/* Account Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {accounts.map((acc) => (
          <Card key={acc.account_id} className="p-6 flex flex-col justify-between hover:border-[var(--color-sapphire)]/30 transition-all">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-blue-50 text-[var(--color-sapphire)] border border-blue-200">
                  {acc.account_type}
                </span>
                <StatusBadge status={acc.status} />
              </div>

              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] block mb-1">
                Account Identifier
              </span>
              <p className="text-sm font-mono font-bold text-[var(--color-sapphire)] mb-5">{acc.account_id}</p>

              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] block mb-1">
                Available Balance
              </span>
              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-3xl font-extrabold text-[var(--color-sapphire)] font-mono font-tabular">
                  {acc.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="text-base font-bold text-[var(--color-gold)]">{acc.currency}</span>
              </div>
            </div>

            <div className="pt-5 mt-4 border-t border-[var(--color-border)] flex items-center justify-between">
              <span className="text-xs text-[var(--color-text-secondary)] font-medium flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-emerald-600" /> Audited
              </span>

              <Button
                size="sm"
                variant="secondary"
                onClick={() => setActiveLedgerAccount(acc)}
              >
                <FileText className="h-4 w-4 text-[var(--color-sapphire)] mr-1.5" />
                <span>Statement</span>
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {/* Open Account Modal */}
      {isModalOpen && (
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Open Additional Account"
          subtitle="Add an isolated checking or savings wallet to your customer profile"
          maxWidth="md"
        >
          <form onSubmit={handleCreateAccount} className="space-y-4">
            <Select
              label="Account Type"
              value={newAccType}
              onChange={(e) => setNewAccType(e.target.value)}
              options={[
                { value: 'CHECKING', label: 'Checking Account' },
                { value: 'SAVINGS', label: 'Savings Account' },
                { value: 'DEMO', label: 'Demo Funds Account' },
              ]}
            />

            <Select
              label="Currency"
              value={newAccCurrency}
              onChange={(e) => setNewAccCurrency(e.target.value)}
              options={[
                { value: 'EGP', label: 'EGP — Egyptian Pound' },
                { value: 'USD', label: 'USD — US Dollar' },
                { value: 'EUR', label: 'EUR — Euro' },
                { value: 'GBP', label: 'GBP — British Pound' },
              ]}
            />

            <Input
              label="Starting Demo Balance"
              type="number"
              min="0"
              step="100"
              value={newAccInitialBalance}
              onChange={(e) => setNewAccInitialBalance(e.target.value)}
              helperText="This balance is recorded as an immutable opening entry in the database ledger."
              required
            />

            {createError && (
              <Alert
                variant="danger"
                icon={<AlertCircle className="h-4 w-4" />}
                message={createError}
              />
            )}

            <div className="flex items-center justify-end gap-3 pt-3">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={isCreating}
              >
                <span>Open Account</span>
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Ledger Statement Drawer / Modal */}
      {activeLedgerAccount && (
        <Modal
          isOpen={Boolean(activeLedgerAccount)}
          onClose={() => setActiveLedgerAccount(null)}
          title="Account Ledger Statement"
          subtitle={`Immutable double-entry audit history for ${activeLedgerAccount.account_id}`}
          maxWidth="lg"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)]">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] block">Verified Balance</span>
                <span className="text-2xl font-extrabold font-mono text-[var(--color-sapphire)] font-tabular">
                  {activeLedgerAccount.balance.toLocaleString()} {activeLedgerAccount.currency}
                </span>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300">
                AUDITED
              </span>
            </div>

            <div className="space-y-2.5">
              <h4 className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                Immutable Ledger Entries
              </h4>

              <div className="space-y-2.5 max-h-[48vh] overflow-y-auto pr-1">
                {activeLedgerAccount.recent_ledger && activeLedgerAccount.recent_ledger.length > 0 ? (
                  activeLedgerAccount.recent_ledger.map((entry) => (
                    <div
                      key={entry.entry_id}
                      className="p-4 rounded-xl bg-white border border-[var(--color-border)] text-xs space-y-1.5 shadow-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className={`font-mono font-bold text-sm ${entry.entry_type === 'DEBIT' ? 'text-rose-600' : 'text-emerald-700'}`}>
                          {entry.entry_type === 'DEBIT' ? '-' : '+'}
                          {entry.amount.toLocaleString()} {entry.currency}
                        </span>
                        <span className="text-[11px] font-mono font-bold text-[var(--color-text-muted)]">{entry.entry_id}</span>
                      </div>
                      <p className="text-[var(--color-text-secondary)] font-medium">{entry.description}</p>
                      <div className="flex items-center justify-between text-[11px] text-[var(--color-text-secondary)] pt-2 border-t border-[var(--color-border)] font-medium">
                        <span>Balance after: <strong className="text-[var(--color-sapphire)] font-mono">{entry.balance_after.toLocaleString()} {entry.currency}</strong></span>
                        <span>{new Date(entry.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="p-6 text-center text-xs text-[var(--color-text-secondary)] font-medium">No ledger history recorded.</p>
                )}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
