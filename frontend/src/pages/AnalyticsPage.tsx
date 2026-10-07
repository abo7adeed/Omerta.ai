import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatCard } from '../components/ui/StatCard';
import {
  TrendingUp,
  Activity,
  ShieldAlert,
  Globe2,
  Cpu,
  BarChart2,
  RefreshCw,
  Zap,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

const CORPORATE_COLORS = ['#002D72', '#F9A825', '#10B981', '#1E88E5', '#64748B'];

const TYPOLOGY_DATA = [
  { typology: 'Multi-Account Hardware', risk_weight: 85, occurrences: 42 },
  { typology: 'Commercial VPN / Proxy', risk_weight: 65, occurrences: 68 },
  { typology: 'Virtualized Emulator', risk_weight: 90, occurrences: 29 },
  { typology: 'Account Takeover Pattern', risk_weight: 78, occurrences: 35 },
  { typology: 'Rapid Mule Pass-Through', risk_weight: 95, occurrences: 18 },
  { typology: 'High Velocity Spike (>5x)', risk_weight: 60, occurrences: 84 },
];

const CURRENCY_DATA = [
  { name: 'EGP (Egyptian Pound)', value: 68, amount: '42.1M EGP' },
  { name: 'USD (US Dollar)', value: 18, amount: '$11.2M' },
  { name: 'EUR (Euro)', value: 9, amount: '€5.6M' },
  { name: 'GBP (British Pound)', value: 5, amount: '£3.1M' },
];

export const AnalyticsPage: React.FC = () => {
  const [charts, setCharts] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const data = await api.getDashboardCharts();
      setCharts(data);
    } catch (err: any) {
      console.error('Failed to load analytics charts', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <TrendingUp className="w-4 h-4" />
            Machine Learning Intelligence
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Advanced Risk &amp; Fraud Analytics
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Cross-entity statistical distributions, typology concentrations, and currency volatility monitoring.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={loadAnalytics}
            disabled={loading}
            variant="primary"
            size="sm"
            leftIcon={<RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Analytics
          </Button>
        </div>
      </Card>

      {/* Analytics KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Monitored Entities"
          value="14,280"
          subtitle="Customer & account nodes"
          icon={Cpu}
          variant="sapphire"
        />
        <StatCard
          title="Active Fraud Rules"
          value="48 Rules"
          subtitle="Real-time ML inference"
          icon={Zap}
          variant="gold"
        />
        <StatCard
          title="Daily Scan Rate"
          value="99.98%"
          subtitle="Sub-12ms latency SLA"
          icon={Activity}
          variant="emerald"
        />
        <StatCard
          title="Global Corridors"
          value="18 Jurisdictions"
          subtitle="Cross-border settlement"
          icon={Globe2}
          variant="sapphire"
        />
      </div>

      {/* Bento Grid Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Typology Radar / Distribution */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Typology Concentration &amp; Risk Weight</CardTitle>
            <CardDescription>Frequency vs risk weight across flagged alerts</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={TYPOLOGY_DATA}>
                <PolarGrid stroke="#E0DDD6" />
                <PolarAngleAxis dataKey="typology" stroke="#64748B" fontSize={10} />
                <PolarRadiusAxis stroke="#64748B" fontSize={10} />
                <Radar name="Risk Weight" dataKey="risk_weight" stroke="#002D72" fill="#002D72" fillOpacity={0.4} />
                <Radar name="Occurrences" dataKey="occurrences" stroke="#F9A825" fill="#F9A825" fillOpacity={0.3} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderRadius: '10px',
                    border: '1px solid #E0DDD6',
                    fontSize: '12px',
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Currency Distribution */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Currency Volume Distribution</CardTitle>
            <CardDescription>Monitored transaction settlement volume by denomination</CardDescription>
          </CardHeader>
          <CardContent className="h-72 flex flex-col justify-between">
            <div className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={CURRENCY_DATA}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                  >
                    {CURRENCY_DATA.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CORPORATE_COLORS[index % CORPORATE_COLORS.length]} />
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
              {CURRENCY_DATA.map((item, idx) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-[#475569] font-medium truncate">
                    <span
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ backgroundColor: CORPORATE_COLORS[idx % CORPORATE_COLORS.length] }}
                    />
                    <span className="truncate">{item.name.split(' ')[0]}</span>
                  </span>
                  <span className="font-mono font-bold text-[#002D72]">{item.amount}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
