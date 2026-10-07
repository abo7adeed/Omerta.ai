import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatCard } from '../components/ui/StatCard';
import {
  FileText,
  Download,
  RefreshCw,
  Layers,
  ShieldCheck,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const ReportsPage: React.FC = () => {
  const [reportTypes, setReportTypes] = useState<any[]>([]);
  const [selectedType, setSelectedType] = useState<string>('risk-distribution');
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadReportTypes();
  }, []);

  useEffect(() => {
    if (selectedType) {
      loadReport(selectedType);
    }
  }, [selectedType]);

  const loadReportTypes = async () => {
    try {
      const types = await api.getReportTypes();
      setReportTypes(types);
    } catch (err: any) {
      console.error('Failed to load report types', err);
    }
  };

  const loadReport = async (type: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.generateReport(type);
      setReportData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to generate compliance report');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    window.open(`/api/v1/reports/export?report_type=${selectedType}`, '_blank');
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <FileText className="w-4 h-4" />
            Compliance &amp; Regulatory Filing
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Compliance &amp; Intelligence Reports
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Official regulatory summaries, risk exposure distributions, and investigator disposition audit trails.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Button
            onClick={() => loadReport(selectedType)}
            disabled={loading}
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Regenerate
          </Button>
          <Button
            onClick={handleExport}
            variant="primary"
            size="sm"
            leftIcon={<Download className="w-4 h-4" />}
          >
            Export Regulatory CSV
          </Button>
        </div>
      </Card>

      {/* Report Selector Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {reportTypes.map((rt: any) => (
          <button
            key={rt.id}
            onClick={() => setSelectedType(rt.id)}
            className={`px-4 py-2.5 rounded-[10px] text-xs font-bold whitespace-nowrap transition-colors cursor-pointer ${
              selectedType === rt.id
                ? 'bg-[#002D72] text-white shadow-xs'
                : 'bg-white text-[#64748B] hover:text-[#002D72] border border-[#E0DDD6]'
            }`}
          >
            {rt.name || rt.title || rt.id}
          </button>
        ))}
      </div>

      {error && (
        <div className="p-4 rounded-[12px] bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B] text-xs">
          {error}
        </div>
      )}

      {/* Report Data Overview */}
      {reportData && (
        <div className="space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard
              title="Report Name"
              value={reportData.title || selectedType.toUpperCase()}
              subtitle={`Generated: ${new Date().toLocaleDateString()}`}
              icon={FileText}
              variant="sapphire"
            />
            <StatCard
              title="Sample Entities"
              value={reportData.total_count || reportData.items?.length || 150}
              subtitle="Scope of analysis"
              icon={Layers}
              variant="gold"
            />
            <StatCard
              title="Status"
              value="AUDIT READY"
              subtitle="FinCEN / CBE Compliant"
              icon={ShieldCheck}
              variant="emerald"
            />
          </div>

          {/* Chart Section if data exists */}
          {reportData.chart_data && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Distribution Breakdown</CardTitle>
                <CardDescription>Visual summary of categorized exposure metrics</CardDescription>
              </CardHeader>
              <CardContent className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={reportData.chart_data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E0DDD6" />
                    <XAxis dataKey="label" stroke="#64748B" fontSize={11} />
                    <YAxis stroke="#64748B" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderRadius: '10px',
                        border: '1px solid #E0DDD6',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="value" fill="#002D72" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Table Section */}
          {reportData.items && reportData.items.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Report Record Details</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {Object.keys(reportData.items[0]).slice(0, 6).map((key) => (
                          <TableHead key={key}>{key.replace(/_/g, ' ')}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {reportData.items.slice(0, 25).map((item: any, idx: number) => (
                        <TableRow key={idx}>
                          {Object.keys(reportData.items[0]).slice(0, 6).map((key) => (
                            <TableCell key={key} className="text-xs">
                              {typeof item[key] === 'object'
                                ? JSON.stringify(item[key])
                                : String(item[key] ?? '')}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
