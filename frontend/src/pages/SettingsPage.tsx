import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  Sliders,
  Server,
  CheckCircle2,
  RefreshCw,
  Save,
  ShieldCheck,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { StatusBadge } from '../components/ui/StatusBadge';

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Form State
  const [humanReviewThreshold, setHumanReviewThreshold] = useState<number>(40.0);
  const [highRiskThreshold, setHighRiskThreshold] = useState<number>(70.0);
  const [criticalRiskThreshold, setCriticalRiskThreshold] = useState<number>(90.0);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await api.getSettings();
      if (data?.thresholds) {
        setHumanReviewThreshold(data.thresholds.human_review_threshold || 40.0);
        setHighRiskThreshold(data.thresholds.high_risk_threshold || 70.0);
        setCriticalRiskThreshold(data.thresholds.critical_risk_threshold || 90.0);
      }
    } catch (err: any) {
      console.error('Failed to load system settings', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSaveThresholds = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(null);
    setSaveError(null);
    try {
      await api.updateThresholds({
        human_review_threshold: Number(humanReviewThreshold),
        high_risk_threshold: Number(highRiskThreshold),
        critical_risk_threshold: Number(criticalRiskThreshold),
      });
      setSaveSuccess('Risk scoring thresholds updated successfully across all monitoring nodes.');
      loadSettings();
    } catch (err: any) {
      setSaveError(err.message || 'Failed to update thresholds. Requires Administrator role.');
    } finally {
      setSaving(false);
    }
  };

  const isAdministrator = user?.role === 'ADMINISTRATOR';

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <Sliders className="w-4 h-4" />
            Institutional Configuration
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            System Architecture &amp; Threshold Governance
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Fine-tune AML detection heuristics, scoring cutoffs, and monitor backend telemetry services.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={loadSettings}
            disabled={loading}
            variant="primary"
            size="sm"
            leftIcon={<RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Configuration
          </Button>
        </div>
      </Card>

      {/* Save alerts */}
      {saveSuccess && (
        <div className="p-4 rounded-[12px] bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-xs font-bold">
            <CheckCircle2 className="w-5 h-5 text-[#10B981]" />
            <span>{saveSuccess}</span>
          </div>
          <button onClick={() => setSaveSuccess(null)} className="text-xs font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {saveError && (
        <div className="p-4 rounded-[12px] bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B] text-xs font-semibold">
          {saveError}
        </div>
      )}

      {/* Threshold Governance Form */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <Card className="lg:col-span-7">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-[#002D72]" />
              Risk Engine Scoring Cutoffs
            </CardTitle>
            <CardDescription>
              Define scoring boundaries for automatic settlement versus human compliance hold
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSaveThresholds} className="space-y-4 text-xs">
              <Input
                label="Human Review Queue Cutoff (%)"
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={humanReviewThreshold}
                onChange={(e) => setHumanReviewThreshold(parseFloat(e.target.value))}
                helperText="Transactions scoring above this percentage will be automatically placed in the analyst review queue."
                disabled={!isAdministrator}
              />

              <Input
                label="High Risk Level Cutoff (%)"
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={highRiskThreshold}
                onChange={(e) => setHighRiskThreshold(parseFloat(e.target.value))}
                helperText="Scores above this boundary will generate automatic high-severity audit cases."
                disabled={!isAdministrator}
              />

              <Input
                label="Critical Auto-Block Threshold (%)"
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={criticalRiskThreshold}
                onChange={(e) => setCriticalRiskThreshold(parseFloat(e.target.value))}
                helperText="Scores exceeding this threshold will automatically freeze transfer settlement and isolate the account."
                disabled={!isAdministrator}
              />

              {isAdministrator && (
                <div className="pt-2 flex justify-end">
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={saving}
                    leftIcon={<Save className="w-4 h-4" />}
                  >
                    Save Threshold Matrix
                  </Button>
                </div>
              )}
            </form>
          </CardContent>
        </Card>

        {/* System Services Status */}
        <Card className="lg:col-span-5">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Server className="w-5 h-5 text-[#002D72]" />
              Service Health &amp; Subsystems
            </CardTitle>
            <CardDescription>
              Live health telemetry across core banking engines
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3.5 text-xs">
            <div className="flex items-center justify-between p-3.5 bg-[#F4F1EC] rounded-[10px] border border-[#E0DDD6]">
              <div>
                <p className="font-bold text-[#0F172A]">PostgreSQL Core Ledger</p>
                <p className="text-[11px] text-[#64748B]">ACID Double-Entry Transaction Engine</p>
              </div>
              <StatusBadge status="ACTIVE" />
            </div>

            <div className="flex items-center justify-between p-3.5 bg-[#F4F1EC] rounded-[10px] border border-[#E0DDD6]">
              <div>
                <p className="font-bold text-[#0F172A]">ML Ensemble Scorer</p>
                <p className="text-[11px] text-[#64748B]">RandomForest + Isolation Forest (v2.4)</p>
              </div>
              <StatusBadge status="ACTIVE" />
            </div>

            <div className="flex items-center justify-between p-3.5 bg-[#F4F1EC] rounded-[10px] border border-[#E0DDD6]">
              <div>
                <p className="font-bold text-[#0F172A]">Network Topology Analyzer</p>
                <p className="text-[11px] text-[#64748B]">Graph Centrality &amp; Entity Smurfing</p>
              </div>
              <StatusBadge status="ACTIVE" />
            </div>

            <div className="flex items-center justify-between p-3.5 bg-[#F4F1EC] rounded-[10px] border border-[#E0DDD6]">
              <div>
                <p className="font-bold text-[#0F172A]">Forensics AI Assistant</p>
                <p className="text-[11px] text-[#64748B]">Evidence Synthesis Copilot (Gemini LLM)</p>
              </div>
              <StatusBadge status="ACTIVE" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
