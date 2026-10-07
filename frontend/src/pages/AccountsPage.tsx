import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Wallet,
  Search,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ArrowRightLeft,
  ArrowUpRight,
  ShieldCheck,
  Building2,
  DollarSign,
} from 'lucide-react';
import { api } from '../api/client';
import type { AccountItem } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { RiskBadge } from '../components/ui/RiskBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const AccountsPage: React.FC = () => {
  const [accounts, setAccounts] = useState<AccountItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [currencyFilter, setCurrencyFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(1);

  // Account detail modal state
  const [selectedAccount, setSelectedAccount] = useState<any | null>(null);

  const navigate = useNavigate();

  const fetchAccounts = async () => {
    setLoading(true);
    try {
      const res = await api.getAccounts({
        search,
        currency: currencyFilter,
        account_type: typeFilter,
        page,
        page_size: 20,
      });
      setAccounts(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load accounts', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, [page, currencyFilter, typeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchAccounts();
  };

  const handleOpenDetail = async (a: AccountItem) => {
    try {
      const res = await api.getAccountDetail(a.external_id);
      setSelectedAccount(res);
    } catch (err) {
      console.error('Failed to load account detail', err);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Page Header */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <Wallet className="w-4 h-4" />
            Banking Ledgers
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Bank Accounts &amp; Balance Ledgers
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Explore multi-currency customer accounts, available balances, and counterparty connections.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={fetchAccounts}
            variant="primary"
            size="sm"
            leftIcon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
        </div>
      </Card>

      {/* Search & Filters */}
      <Card className="p-5">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-3.5">
          <div className="sm:col-span-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search account number, IBAN, customer name..."
              leftIcon={<Search className="h-4 w-4 text-[#64748B]" />}
              className="h-10 text-xs"
            />
          </div>

          <div>
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              className="w-full h-10 bg-white border border-[#E0DDD6] rounded-[10px] px-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
            >
              <option value="">All Account Types</option>
              <option value="CHECKING">Checking</option>
              <option value="SAVINGS">Savings</option>
              <option value="CURRENT">Current</option>
              <option value="BUSINESS">Business</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Button type="submit" variant="sapphire" size="sm" className="h-10 flex-1 text-xs">
              Filter
            </Button>
            {(search || typeFilter) && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-10 px-3 text-xs text-[#64748B]"
                onClick={() => {
                  setSearch('');
                  setTypeFilter('');
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
            <CardTitle className="text-base">Registered Account Ledgers</CardTitle>
            <CardDescription>
              Showing <span className="font-bold text-[#002D72]">{accounts.length}</span> of{' '}
              <span className="font-bold text-[#002D72]">{total.toLocaleString()}</span> accounts
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account Number</TableHead>
                  <TableHead>Customer / Entity</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Available Balance</TableHead>
                  <TableHead>Risk Score</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts.length > 0 ? (
                  accounts.map((a) => (
                    <TableRow
                      key={a.external_id}
                      onClick={() => handleOpenDetail(a)}
                      className="cursor-pointer"
                    >
                      <TableCell>
                        <div className="font-mono font-bold text-[#002D72]">
                          {a.external_id}
                        </div>
                        <div className="text-[11px] text-[#64748B] font-mono">
                          {(a as any).iban || a.account_type || 'CHECKING'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="font-bold text-[#0F172A]">
                          {a.customer_name || 'Account Holder'}
                        </div>
                        <div className="text-[11px] text-[#64748B] font-mono">
                          {a.customer_id || 'CUST-REF'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#F4F1EC] text-[#002D72] border border-[#E0DDD6]">
                          {a.account_type || 'CHECKING'}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono font-bold text-[#002D72] text-sm">
                        {Number(a.balance || 0).toLocaleString()} {a.currency || 'EGP'}
                      </TableCell>
                      <TableCell>
                        <RiskBadge level={a.risk_level || 'LOW'} score={(a as any).risk_score} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={a.status || 'ACTIVE'} />
                      </TableCell>
                      <TableCell className="text-xs font-mono text-[#64748B]">
                        {a.created_at ? new Date(a.created_at).toLocaleDateString() : 'Recent'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenDetail(a);
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
                      {loading ? 'Retrieving bank accounts...' : 'No accounts matching filters.'}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Account Detail Modal */}
      {selectedAccount && (
        <Modal
          isOpen={Boolean(selectedAccount)}
          onClose={() => setSelectedAccount(null)}
          title={`Account Ledger: ${selectedAccount.external_id}`}
          subtitle={`Customer: ${selectedAccount.customer_name || 'Account Holder'}`}
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-[#F4F1EC] p-3.5 rounded-[12px] border border-[#E0DDD6]">
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Available Balance</span>
                <p className="font-mono font-bold text-sm text-[#002D72] mt-0.5">
                  {Number(selectedAccount.balance || 0).toLocaleString()} {selectedAccount.currency || 'EGP'}
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Account Type</span>
                <p className="font-bold text-[#002D72] mt-0.5">{selectedAccount.account_type || 'CHECKING'}</p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Risk Level</span>
                <div className="mt-0.5">
                  <RiskBadge level={selectedAccount.risk_level || 'LOW'} score={(selectedAccount as any).risk_score} />
                </div>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Status</span>
                <div className="mt-0.5">
                  <StatusBadge status={selectedAccount.status || 'ACTIVE'} />
                </div>
              </div>
            </div>

            {/* Recent Account Activity */}
            <div className="space-y-2">
              <h5 className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider">
                Recent Ledger Activity
              </h5>
              {selectedAccount.recent_transactions?.length > 0 ? (
                <div className="space-y-1.5">
                  {selectedAccount.recent_transactions.map((tx: any) => (
                    <div
                      key={tx.id || tx.external_id}
                      className="p-3 bg-white rounded-[10px] border border-[#E0DDD6] flex items-center justify-between shadow-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <ArrowRightLeft className="h-4 w-4 text-[#002D72]" />
                        <div>
                          <p className="font-mono font-bold text-[#002D72]">{tx.external_id || tx.id}</p>
                          <p className="text-[11px] text-[#64748B]">{tx.receiver_name || 'Counterparty'}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-mono font-bold text-[#002D72]">
                          {Number(tx.amount || 0).toLocaleString()} {tx.currency || 'EGP'}
                        </p>
                        <StatusBadge status={tx.status || 'COMPLETED'} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[#64748B] py-4 text-center">No recent transactions recorded for this account.</p>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-[#E0DDD6]">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setSelectedAccount(null)}
              >
                Close
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  const accNum = selectedAccount.external_id;
                  setSelectedAccount(null);
                  navigate(`/admin/network-analysis?entity=${encodeURIComponent(accNum)}`);
                }}
              >
                <span>Inspect Entity Network</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
