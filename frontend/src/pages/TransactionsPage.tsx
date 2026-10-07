import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Search,
  Download,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ArrowLeftRight,
  ArrowUpRight,
  Smartphone,
  Globe,
} from 'lucide-react';
import { api } from '../api/client';
import type { TransactionItem } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { RiskBadge } from '../components/ui/RiskBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const TransactionsPage: React.FC = () => {
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Filters state
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [currency, setCurrency] = useState('');
  const [transactionType] = useState('');
  const [riskLevel, setRiskLevel] = useState('');
  const [reviewStatus, setReviewStatus] = useState('');
  const [page, setPage] = useState(1);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const res = await api.getTransactions({
        search,
        currency,
        transaction_type: transactionType,
        risk_level: riskLevel,
        review_status: reviewStatus,
        page,
        page_size: 20,
      });
      setTransactions(res.items || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err) {
      console.error('Failed to fetch transactions', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [page, currency, transactionType, riskLevel, reviewStatus]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchTransactions();
  };

  const handleExportCSV = () => {
    const q = new URLSearchParams();
    if (search) q.append('search', search);
    if (currency) q.append('currency', currency);
    if (riskLevel) q.append('risk_level', riskLevel);
    if (reviewStatus) q.append('review_status', reviewStatus);
    window.open(`/api/v1/transactions/export?${q.toString()}`, '_blank');
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Page Header */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <ArrowLeftRight className="w-4 h-4" />
            Banking Transaction Ledger
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Transaction Directory &amp; Risk Intelligence
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Inspect transactions across all customer accounts with multi-signal risk assessments and velocity signals.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Button
            onClick={handleExportCSV}
            variant="secondary"
            size="sm"
            leftIcon={<Download className="h-4 w-4 text-[#002D72]" />}
          >
            Export CSV
          </Button>
          <Button
            onClick={fetchTransactions}
            variant="primary"
            size="sm"
            leftIcon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
        </div>
      </Card>

      {/* Filter Control Bar */}
      <Card className="p-5">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
          <div className="lg:col-span-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search TXN-ID, account #, sender or receiver..."
              leftIcon={<Search className="h-4 w-4 text-[#64748B]" />}
              className="h-10 text-xs"
            />
          </div>

          <div>
            <select
              value={riskLevel}
              onChange={(e) => {
                setRiskLevel(e.target.value);
                setPage(1);
              }}
              className="w-full h-10 bg-white border border-[#E0DDD6] rounded-[10px] px-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
            >
              <option value="">All Risk Tiers</option>
              <option value="LOW">Low Risk</option>
              <option value="MODERATE">Moderate Risk</option>
              <option value="REQUIRES_REVIEW">Requires Review</option>
              <option value="HIGH">High Risk</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>

          <div>
            <select
              value={reviewStatus}
              onChange={(e) => {
                setReviewStatus(e.target.value);
                setPage(1);
              }}
              className="w-full h-10 bg-white border border-[#E0DDD6] rounded-[10px] px-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="REQUIRES_REVIEW">Requires Review</option>
              <option value="UNDER_INVESTIGATION">Under Investigation</option>
              <option value="BLOCKED">Blocked</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Button
              type="submit"
              variant="sapphire"
              size="sm"
              className="h-10 flex-1 text-xs"
            >
              Filter
            </Button>
            {(search || currency || riskLevel || reviewStatus) && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-10 px-3 text-xs text-[#64748B]"
                onClick={() => {
                  setSearch('');
                  setCurrency('');
                  setRiskLevel('');
                  setReviewStatus('');
                  setPage(1);
                }}
              >
                Reset
              </Button>
            )}
          </div>
        </form>
      </Card>

      {/* Main Transactions Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base">Ledger Entries</CardTitle>
            <CardDescription>
              Showing <span className="font-bold text-[#002D72]">{transactions.length}</span> of{' '}
              <span className="font-bold text-[#002D72]">{total.toLocaleString()}</span> records
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Transaction ID</TableHead>
                  <TableHead>Sender &amp; Account</TableHead>
                  <TableHead>Recipient</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Risk Score</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead className="text-right">Dossier</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.length > 0 ? (
                  transactions.map((txn: any) => {
                    const devId = txn.device || txn.device_id || 'WEB-CLIENT';
                    const sAccount = txn.source_account || txn.sender_account_number || txn.account_number || 'ACC-Monitored';
                    const sName = txn.customer_name || txn.sender_name || 'Account Holder';
                    const rAccount = txn.recipient_account || txn.receiver_account_number || 'Beneficiary Account';
                    const rName = txn.receiver_name || 'Beneficiary';
                    const txTime = txn.timestamp || txn.created_at;

                    return (
                      <TableRow
                        key={txn.external_id || txn.id}
                        onClick={() => navigate(`/admin/transactions/${txn.external_id || txn.id}`)}
                        className="cursor-pointer"
                      >
                        <TableCell>
                          <div className="font-mono font-bold text-[#002D72]">
                            {txn.external_id || txn.id}
                          </div>
                          <div className="text-[11px] text-[#64748B] flex items-center gap-1 mt-0.5">
                            {devId ? (
                              <span className="flex items-center gap-1" title={devId}>
                                <Smartphone className="h-3 w-3 text-[#1E88E5]" />
                                <span className="truncate max-w-[80px] font-mono">{devId}</span>
                              </span>
                            ) : (
                              <span className="flex items-center gap-1">
                                <Globe className="h-3 w-3 text-[#64748B]" />
                                <span>ONLINE</span>
                              </span>
                            )}
                          </div>
                        </TableCell>

                        <TableCell>
                          <div className="font-bold text-[#0F172A] truncate max-w-[150px]">
                            {sName}
                          </div>
                          <div className="text-[11px] font-mono text-[#64748B]">
                            {sAccount}
                          </div>
                        </TableCell>

                        <TableCell>
                          <div className="font-medium text-[#0F172A] truncate max-w-[150px]">
                            {rName}
                          </div>
                          <div className="text-[11px] font-mono text-[#64748B]">
                            {rAccount}
                          </div>
                        </TableCell>

                        <TableCell>
                          <div className="font-mono font-bold text-[#002D72]">
                            {txn.amount ? `${Number(txn.amount).toLocaleString()} ${txn.currency || 'EGP'}` : '0 EGP'}
                          </div>
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
                          <StatusBadge status={txn.status || 'COMPLETED'} />
                        </TableCell>

                        <TableCell className="text-xs font-mono text-[#64748B]">
                          {txTime ? new Date(txTime).toLocaleString() : 'Recent'}
                        </TableCell>

                        <TableCell className="text-right">
                          <Button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/admin/transactions/${txn.external_id || txn.id}`);
                            }}
                            variant="ghost"
                            size="sm"
                            className="h-8 px-2 text-[#002D72]"
                          >
                            <ArrowUpRight className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={8} className="p-12 text-center text-[#64748B]">
                      {loading ? 'Querying transaction database...' : 'No transactions matched your search criteria.'}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-[#E0DDD6] flex items-center justify-between text-xs text-[#64748B]">
              <span>
                Page <strong className="text-[#002D72]">{page}</strong> of{' '}
                <strong className="text-[#002D72]">{totalPages}</strong>
              </span>
              <div className="flex gap-2">
                <Button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  variant="secondary"
                  size="sm"
                  leftIcon={<ChevronLeft className="h-4 w-4" />}
                >
                  Previous
                </Button>
                <Button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  variant="secondary"
                  size="sm"
                  rightIcon={<ChevronRight className="h-4 w-4" />}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
