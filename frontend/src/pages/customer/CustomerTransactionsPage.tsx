import React, { useState, useEffect } from 'react';
import {
  ArrowLeftRight,
  ArrowUpRight,
  ArrowDownLeft,
  Search,
  FileText,
} from 'lucide-react';
import { api } from '../../api/client';
import type { CustomerTransaction } from '../../types';
import {
  Card,
  Button,
  Input,
  Select,
  StatusBadge,
  Modal,
} from '../../components/ui';

export const CustomerTransactionsPage: React.FC = () => {
  const [transactions, setTransactions] = useState<CustomerTransaction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [direction, setDirection] = useState('ALL');
  const [status, setStatus] = useState('ALL');
  const [isLoading, setIsLoading] = useState(true);

  // Receipt Modal
  const [selectedTxn, setSelectedTxn] = useState<CustomerTransaction | null>(null);

  const fetchTransactions = async () => {
    setIsLoading(true);
    try {
      const res = await api.getCustomerTransactions({
        search: search.trim() || undefined,
        direction: direction !== 'ALL' ? direction : undefined,
        status: status !== 'ALL' ? status : undefined,
        page,
        page_size: pageSize,
      });
      setTransactions(res.items || []);
      setTotal(res.total || 0);
    } catch {
      setTransactions([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [page, direction, status]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchTransactions();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6 md:p-8">
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-sapphire)] flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-[var(--color-sapphire)] text-[var(--color-gold)] shadow-sm">
            <ArrowLeftRight className="h-6 w-6 stroke-[2.2]" />
          </div>
          <span>My Transactions</span>
        </h1>
        <p className="text-xs text-[var(--color-text-secondary)] mt-2 font-medium">
          Historical record of all incoming and outgoing transfers scoped to your accounts
        </p>
      </Card>

      {/* Filter Bar */}
      <Card className="p-5">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3 items-center">
          <div className="flex-1 w-full">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search reference, counterparty..."
              icon={<Search className="h-4 w-4 text-[var(--color-sapphire)]" />}
            />
          </div>

          <div className="flex items-center gap-2.5 flex-wrap w-full sm:w-auto">
            <Select
              value={direction}
              onChange={(e) => {
                setDirection(e.target.value);
                setPage(1);
              }}
              options={[
                { value: 'ALL', label: 'All Directions' },
                { value: 'INCOMING', label: 'Incoming Transfers' },
                { value: 'OUTGOING', label: 'Outgoing Transfers' },
              ]}
            />

            <Select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
              options={[
                { value: 'ALL', label: 'All Statuses' },
                { value: 'COMPLETED', label: 'Completed' },
                { value: 'PENDING', label: 'Pending' },
                { value: 'REJECTED', label: 'Rejected' },
              ]}
            />

            <Button
              type="submit"
              variant="primary"
              size="sm"
            >
              Filter
            </Button>
          </div>
        </form>
      </Card>

      {/* Table */}
      <Card className="p-0 overflow-hidden">
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
                <th className="p-4 text-right">Receipt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {transactions.length > 0 ? (
                transactions.map((t) => (
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
                    <td className="p-4 font-mono font-bold text-[var(--color-text-secondary)]">{t.transaction_id}</td>
                    <td className="p-4 font-semibold text-[var(--color-text-primary)]">{t.counterparty}</td>
                    <td className="p-4 font-mono font-bold font-tabular text-[var(--color-sapphire)]">
                      {t.direction === 'INCOMING' ? '+' : '-'}
                      {t.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {t.currency}
                    </td>
                    <td className="p-4">
                      <StatusBadge status={t.status} />
                    </td>
                    <td className="p-4 text-[var(--color-text-secondary)] font-medium whitespace-nowrap">
                      {new Date(t.timestamp).toLocaleDateString()} {new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="p-4 text-right">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setSelectedTxn(t)}
                        title="View Customer Receipt"
                        aria-label="View Receipt"
                        className="px-2.5 min-h-[36px]"
                      >
                        <FileText className="h-4 w-4 text-[var(--color-sapphire)]" />
                      </Button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="p-10 text-center text-[var(--color-text-secondary)] font-medium">
                    {isLoading ? 'Loading transaction history...' : 'No transactions matching your criteria.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > pageSize && (
          <div className="p-4 border-t border-[var(--color-border)] flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-semibold">
            <span>Showing {transactions.length} of {total} entries</span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={page * pageSize >= total}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Customer Receipt Modal */}
      {selectedTxn && (
        <Modal
          isOpen={Boolean(selectedTxn)}
          onClose={() => setSelectedTxn(null)}
          title="Transfer Receipt"
          subtitle="Verified transaction ledger entry"
          maxWidth="md"
        >
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-3">
              <div className="flex justify-between items-center pb-2 border-b border-[var(--color-border)]">
                <span className="text-[var(--color-text-muted)] font-bold">Transaction Ref</span>
                <span className="font-mono font-extrabold text-[var(--color-sapphire)]">{selectedTxn.transaction_id}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[var(--color-text-muted)] font-bold">Direction</span>
                <span className="font-bold text-[var(--color-text-primary)]">{selectedTxn.direction}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[var(--color-text-muted)] font-bold">Counterparty</span>
                <span className="font-semibold text-[var(--color-text-primary)]">{selectedTxn.counterparty}</span>
              </div>
              <div className="flex justify-between items-center border-t border-[var(--color-border)] pt-2">
                <span className="text-[var(--color-text-muted)] font-bold">Amount</span>
                <span className="font-mono font-extrabold text-base text-emerald-700 font-tabular">
                  {selectedTxn.amount.toLocaleString()} {selectedTxn.currency}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[var(--color-text-muted)] font-bold">Status</span>
                <StatusBadge status={selectedTxn.status} />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[var(--color-text-muted)] font-bold">Date &amp; Time</span>
                <span className="text-[var(--color-text-secondary)] font-medium">{new Date(selectedTxn.timestamp).toLocaleString()}</span>
              </div>
            </div>

            <Button
              variant="primary"
              size="sm"
              onClick={() => setSelectedTxn(null)}
              className="w-full"
            >
              Close Receipt
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
};
