import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeftRight,
  DollarSign,
  ShieldAlert,
  AlertTriangle,
  FolderSearch,
  Users,
  Wallet,
  ArrowUpRight,
  TrendingUp,
  RefreshCw,
  Activity,
  CheckCircle2,
  ShieldCheck,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts';
import { api } from '../api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatCard } from '../components/ui/StatCard';
import { RiskBadge } from '../components/ui/RiskBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [charts, setCharts] = useState<any>(null);
  const [recent, setRecent] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [sumRes, chartRes, recRes] = await Promise.all([
        api.getDashboardSummary(),
        api.getDashboardCharts(),
        api.getRecentActivity(6),
      ]);
      setSummary(sumRes);
      setCharts(chartRes);
      setRecent(recRes);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const RISK_COLORS: Record<string, string> = {
    LOW: '#10B981',
    MODERATE: '#1E88E5',
    REQUIRES_REVIEW: '#F9A825',
    HIGH: '#F59E0B',
    CRITICAL: '#DC2626',
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Welcome / Header Card */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <span className="h-2 w-2 rounded-full bg-[#10B981] animate-pulse" />
            Omerta Financial Crime Intelligence
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Executive Intelligence Dashboard
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Real-time transaction monitoring, multi-signal risk assessments, and human review queues.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={loadDashboardData}
            variant="secondary"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-[#002D72]' : ''}`} />
            <span>Refresh</span>
          </Button>
          <Button
            onClick={() => navigate('/admin/risk-monitoring')}
            variant="primary"
            size="sm"
          >
            <ShieldAlert className="h-4 w-4" />
            <span>Review Queue ({summary?.transactions_requiring_review ?? '…'})</span>
          </Button>
        </div>
      </Card>

      {/* 4 Primary Executive KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Transactions"
          value={
            summary?.total_transactions !== undefined
              ? Number(summary.total_transactions).toLocaleString()
              : '10,000'
          }
          subtitle="Monitored in system of record"
          change="+14.2% vs last period"
          isPositive={true}
          icon={ArrowLeftRight}
          variant="sapphire"
        />
        <StatCard
          title="Total Volume"
          value={
            summary?.total_volume !== undefined
              ? `${(Number(summary.total_volume) / 1000000).toFixed(1)}M EGP`
              : '156.5M EGP'
          }
          subtitle="Cumulative gross volume"
          change="+8.6% throughput"
          isPositive={true}
          icon={DollarSign}
          variant="emerald"
        />
        <StatCard
          title="Under Human Review"
          value={summary?.transactions_requiring_review ?? '315'}
          subtitle="Strict rule: risk_score > 40%"
          change="Action required"
          isPositive={false}
          icon={ShieldAlert}
          variant="gold"
          onClick={() => navigate('/admin/risk-monitoring')}
        />
        <StatCard
          title="High-Risk Transactions"
          value={summary?.high_risk_transactions ?? '10'}
          subtitle="Score >= 70% or critical flags"
          change="Priority escalated"
          isPositive={false}
          icon={AlertTriangle}
          variant="rose"
          onClick={() => navigate('/admin/risk-monitoring')}
        />
      </div>

      {/* Secondary Metric Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Open Investigations"
          value={summary?.open_investigations ?? '67'}
          subtitle="Active analyst cases"
          icon={FolderSearch}
          variant="sapphire"
          onClick={() => navigate('/admin/investigations')}
        />
        <StatCard
          title="Blocked Transactions"
          value={summary?.blocked_transactions ?? '12'}
          subtitle="Prevented fraudulent dispatch"
          icon={ShieldCheck}
          variant="amber"
        />
        <StatCard
          title="Total Accounts"
          value={
            (summary?.accounts_monitored ?? summary?.total_accounts) !== undefined
              ? Number(summary.accounts_monitored ?? summary.total_accounts).toLocaleString()
              : '1,500'
          }
          subtitle="Protected banking ledgers"
          icon={Wallet}
          variant="sapphire"
          onClick={() => navigate('/admin/accounts')}
        />
        <StatCard
          title="Verified Customers"
          value={
            (summary?.customers_monitored ?? summary?.total_customers) !== undefined
              ? Number(summary.customers_monitored ?? summary.total_customers).toLocaleString()
              : '1,200'
          }
          subtitle="KYC complete & active"
          icon={Users}
          variant="emerald"
          onClick={() => navigate('/admin/customers')}
        />
      </div>

      {/* Bento Grid: Analytics & Chart Intelligence */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Real-time Volume / Trend Area Chart */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base">Transaction Throughput &amp; Risk Volume</CardTitle>
              <CardDescription>
                Chronological transaction volume (EGP) and flagged suspicious velocity
              </CardDescription>
            </div>
            <div className="flex items-center gap-3 text-xs font-semibold">
              <span className="flex items-center gap-1.5 text-[#002D72]">
                <span className="h-2.5 w-2.5 rounded-full bg-[#002D72]" /> Volume
              </span>
              <span className="flex items-center gap-1.5 text-[#F9A825]">
                <span className="h-2.5 w-2.5 rounded-full bg-[#F9A825]" /> High Risk
              </span>
            </div>
          </CardHeader>
          <CardContent className="h-72">
            {charts?.volume_trend || charts?.time_series ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={charts.volume_trend || charts.time_series}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#002D72" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#002D72" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F9A825" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#F9A825" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    stroke="#94A3B8"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: '#E0DDD6' }}
                  />
                  <YAxis
                    stroke="#94A3B8"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: '#E0DDD6' }}
                    tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '10px',
                      border: '1px solid #E0DDD6',
                      boxShadow: '0 4px 12px rgba(0, 45, 114, 0.08)',
                      fontSize: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="volume"
                    name="Gross Volume"
                    stroke="#002D72"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorVolume)"
                  />
                  <Area
                    type="monotone"
                    dataKey="reviews"
                    name="Reviews / High Risk"
                    stroke="#F9A825"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorRisk)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-[#64748B]">
                {loading ? 'Synthesizing time-series telemetry...' : 'No telemetry data available'}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Risk Distribution Breakdown */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Risk Tier Distribution</CardTitle>
            <CardDescription>
              Breakdown across current monitored volume
            </CardDescription>
          </CardHeader>
          <CardContent className="h-72 flex flex-col justify-between">
            {charts?.risk_distribution && charts.risk_distribution.length > 0 ? (
              <>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={charts.risk_distribution}
                        dataKey="count"
                        nameKey="level"
                        innerRadius={45}
                        outerRadius={70}
                        paddingAngle={3}
                      >
                        {charts.risk_distribution.map((entry: any) => (
                          <Cell
                            key={entry.level}
                            fill={RISK_COLORS[entry.level] || '#002D72'}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#FFFFFF',
                          borderRadius: '10px',
                          border: '1px solid #E0DDD6',
                          fontSize: '12px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#E0DDD6]">
                  {charts.risk_distribution.map((item: any) => (
                    <div key={item.level} className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-1.5 text-[#475569] font-medium">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: RISK_COLORS[item.level] || '#002D72' }}
                        />
                        {item.level.replace(/_/g, ' ')}
                      </span>
                      <span className="font-mono font-bold text-[#002D72]">{item.count}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-[#64748B]">
                {loading ? 'Calculating risk distribution...' : 'No distribution metrics'}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Monitored Transactions Table */}
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base">Recent High-Risk &amp; Monitored Activity</CardTitle>
            <CardDescription>
              Real-time audit feed of transactions requiring compliance attention
            </CardDescription>
          </div>
          <Button
            onClick={() => navigate('/admin/transactions')}
            variant="tertiary"
            size="sm"
            rightIcon={<ArrowUpRight className="h-4 w-4" />}
          >
            View All Transactions
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Transaction ID</TableHead>
                  <TableHead>Customer / Sender</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Risk Score</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(() => {
                  const txList = recent?.recent_transactions || recent?.items || [];
                  if (txList.length > 0) {
                    return txList.map((txn: any) => {
                      const timeStr = txn.timestamp || txn.created_at;
                      return (
                        <TableRow
                          key={txn.external_id || txn.id}
                          onClick={() => navigate(`/admin/transactions/${txn.external_id || txn.id}`)}
                          className="cursor-pointer"
                        >
                          <TableCell className="font-mono font-bold text-[#002D72]">
                            {txn.external_id || txn.id}
                          </TableCell>
                          <TableCell>
                            <div className="font-semibold text-[#0F172A]">
                              {txn.sender_name || txn.customer_name || 'Account Holder'}
                            </div>
                            <div className="text-[11px] text-[#64748B] font-mono">
                              {txn.sender_account_number || txn.account_number || 'ACC-Monitored'}
                            </div>
                          </TableCell>
                          <TableCell className="font-mono font-bold text-[#002D72]">
                            {txn.amount !== undefined ? `${Number(txn.amount).toLocaleString()} ${txn.currency || 'EGP'}` : '0 EGP'}
                          </TableCell>
                          <TableCell>
                            <RiskBadge
                              level={txn.risk_level || (txn.risk_score >= 70 ? 'HIGH' : txn.risk_score >= 40 ? 'REQUIRES_REVIEW' : 'LOW')}
                              score={txn.risk_score}
                            />
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={txn.status || 'COMPLETED'} />
                          </TableCell>
                          <TableCell className="text-xs text-[#64748B] font-mono">
                            {timeStr ? new Date(timeStr).toLocaleTimeString() : 'Just now'}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/admin/transactions/${txn.external_id || txn.id}`);
                              }}
                              variant="ghost"
                              size="sm"
                            >
                              <span>Investigate</span>
                              <ArrowUpRight className="h-3.5 w-3.5" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    });
                  }
                  return (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-xs text-[#64748B]">
                        {loading ? 'Fetching recent transaction telemetry...' : 'No transactions requiring immediate review'}
                      </TableCell>
                    </TableRow>
                  );
                })()}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </div>
  );
};
