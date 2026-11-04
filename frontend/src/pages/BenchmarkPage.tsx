import React, { useEffect, useState } from 'react';
import {
  Scale,
  Play,
  CheckCircle,
  AlertCircle,
  Clock,
  Coins,
  Cpu,
  Layers,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Info,
  ShieldAlert,
  FileText,
  Filter,
  RefreshCw,
  Sliders,
  CheckSquare,
  Square,
  X,
  Download,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { api } from '../api/client';
import type {
  BenchmarkCase,
  BenchmarkCaseResult,
  BenchmarkModelConfig,
  BenchmarkRunDetail,
  BenchmarkRunSummary,
  ModelAvailabilityInfo,
} from '../api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const BenchmarkPage: React.FC = () => {
  // Catalogs & Datasets
  const [availableModels, setAvailableModels] = useState<ModelAvailabilityInfo[]>([]);
  const [scenarios, setScenarios] = useState<BenchmarkCase[]>([]);
  const [selectedCaseIds, setSelectedCaseIds] = useState<string[]>([]);
  const [recentRuns, setRecentRuns] = useState<BenchmarkRunSummary[]>([]);

  // Selected Model Configurations
  const [modelA, setModelA] = useState<BenchmarkModelConfig>({
    model_id: 'openai/gpt-oss-120b',
    provider: 'groq',
    display_name: 'Groq: GPT-OSS 120B (Deep Reasoning)',
    temperature: 0.0,
    max_tokens: 1500,
  });

  const [modelB, setModelB] = useState<BenchmarkModelConfig>({
    model_id: 'openai/gpt-oss-20b',
    provider: 'groq',
    display_name: 'Groq: GPT-OSS 20B (High Speed & Efficiency)',
    temperature: 0.0,
    max_tokens: 1500,
  });

  // Active / Selected Run State
  const [activeRun, setActiveRun] = useState<BenchmarkRunDetail | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Deep Case Inspection Modal
  const [inspectingCase, setInspectingCase] = useState<BenchmarkCaseResult | null>(null);
  const [scenarioFilter, setScenarioFilter] = useState<string>('ALL');

  // Load initial catalog, scenarios, and runs
  const initializePage = async () => {
    setIsLoadingHistory(true);
    try {
      const [modelsData, scenariosData, runsData] = await Promise.all([
        api.getBenchmarkModels(),
        api.getBenchmarkScenariosList(),
        api.getBenchmarkRuns(15, 0),
      ]);
      setAvailableModels(modelsData);
      setScenarios(scenariosData);
      setSelectedCaseIds(scenariosData.map((s) => s.case_id));
      setRecentRuns(runsData);

      // Auto-load most recent run if available
      if (runsData && runsData.length > 0) {
        const latestDetail = await api.getBenchmarkRunDetails(runsData[0].run_id);
        setActiveRun(latestDetail);
      }
    } catch (err: any) {
      console.error('Failed to initialize benchmark page:', err);
      setErrorMessage(err.message || 'Failed loading benchmark configuration.');
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    initializePage();
  }, []);

  // Handle Model Selection
  const handleSelectModel = (modelId: string, isModelA: boolean) => {
    const selected = availableModels.find((m) => m.model_id === modelId);
    if (!selected) return;

    const newConfig: BenchmarkModelConfig = {
      model_id: selected.model_id,
      provider: selected.provider,
      display_name: selected.display_name,
      temperature: 0.0,
      max_tokens: 1500,
    };

    if (isModelA) {
      setModelA(newConfig);
    } else {
      setModelB(newConfig);
    }
  };

  // Toggle Scenario Selection
  const toggleCaseSelection = (caseId: string) => {
    if (selectedCaseIds.includes(caseId)) {
      if (selectedCaseIds.length > 1) {
        setSelectedCaseIds(selectedCaseIds.filter((id) => id !== caseId));
      }
    } else {
      setSelectedCaseIds([...selectedCaseIds, caseId]);
    }
  };

  const toggleSelectAll = () => {
    if (selectedCaseIds.length === scenarios.length) {
      setSelectedCaseIds([scenarios[0].case_id]);
    } else {
      setSelectedCaseIds(scenarios.map((s) => s.case_id));
    }
  };

  // Execute Benchmark Run
  const handleExecuteRun = async () => {
    if (selectedCaseIds.length === 0) {
      setErrorMessage('Please select at least one benchmark case to execute.');
      return;
    }

    setIsRunning(true);
    setErrorMessage(null);
    setStatusMessage('Initiating side-by-side benchmark evaluation across candidate models...');

    try {
      const payload = {
        model_a: modelA,
        model_b: modelB,
        case_ids: selectedCaseIds,
        dataset_version: '1.0',
      };

      const result = await api.executeBenchmarkRun(payload);
      setActiveRun(result);

      // Refresh runs list
      const updatedRuns = await api.getBenchmarkRuns(15, 0);
      setRecentRuns(updatedRuns);
      setStatusMessage('Benchmark run completed successfully.');
    } catch (err: any) {
      console.error('Benchmark execution error:', err);
      setErrorMessage(err.message || 'Benchmark execution failed.');
    } finally {
      setIsRunning(false);
    }
  };

  // Select Historical Run
  const handleSelectRun = async (runId: string) => {
    try {
      setIsLoadingHistory(true);
      const detail = await api.getBenchmarkRunDetails(runId);
      setActiveRun(detail);
    } catch (err: any) {
      setErrorMessage(`Failed to load run ${runId}: ${err.message}`);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Prepare Dimension Comparison Chart Data
  const dimensionChartData = [
    {
      dimension: 'Evidence Grounding',
      [activeRun?.model_a_config.model_id || 'Model A']:
        activeRun?.aggregate_metrics?.model_a?.average_scores?.evidence_grounding || 0,
      [activeRun?.model_b_config.model_id || 'Model B']:
        activeRun?.aggregate_metrics?.model_b?.average_scores?.evidence_grounding || 0,
    },
    {
      dimension: 'Reasoning Quality',
      [activeRun?.model_a_config.model_id || 'Model A']:
        activeRun?.aggregate_metrics?.model_a?.average_scores?.reasoning_quality || 0,
      [activeRun?.model_b_config.model_id || 'Model B']:
        activeRun?.aggregate_metrics?.model_b?.average_scores?.reasoning_quality || 0,
    },
    {
      dimension: 'Completeness',
      [activeRun?.model_a_config.model_id || 'Model A']:
        activeRun?.aggregate_metrics?.model_a?.average_scores?.investigation_completeness || 0,
      [activeRun?.model_b_config.model_id || 'Model B']:
        activeRun?.aggregate_metrics?.model_b?.average_scores?.investigation_completeness || 0,
    },
    {
      dimension: 'Report Quality',
      [activeRun?.model_a_config.model_id || 'Model A']:
        activeRun?.aggregate_metrics?.model_a?.average_scores?.report_quality || 0,
      [activeRun?.model_b_config.model_id || 'Model B']:
        activeRun?.aggregate_metrics?.model_b?.average_scores?.report_quality || 0,
    },
    {
      dimension: 'Overall Quality',
      [activeRun?.model_a_config.model_id || 'Model A']:
        activeRun?.aggregate_metrics?.model_a?.average_scores?.overall_quality || 0,
      [activeRun?.model_b_config.model_id || 'Model B']:
        activeRun?.aggregate_metrics?.model_b?.average_scores?.overall_quality || 0,
    },
  ];

  // Filter cases for the table
  const displayedCases = (activeRun?.cases || []).filter((c) => {
    if (scenarioFilter === 'ALL') return true;
    return c.scenario_type.toUpperCase() === scenarioFilter.toUpperCase();
  });

  const aggA = activeRun?.aggregate_metrics?.model_a;
  const aggB = activeRun?.aggregate_metrics?.model_b;
  const comp = activeRun?.aggregate_metrics?.comparison;

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-gradient-to-r from-[#002D72] to-[#001845] p-6 rounded-xl text-white shadow-lg border border-[#003882]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 bg-[#F9A825]/20 text-[#F9A825] rounded-md">
              <Scale className="w-5 h-5" />
            </span>
            <span className="text-xs font-semibold uppercase tracking-wider text-[#F9A825]">
              Systemic Evaluation & Observability
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            LLM Model Side-by-Side Benchmarks
          </h1>
          <p className="text-sm text-slate-300 mt-1 max-w-2xl">
            Empirical evaluation comparing candidate models on identical financial crime investigation cases
            using deterministic factual grounding, Groq LLM-as-a-Judge, and Langfuse tracing.
          </p>
        </div>

        {/* Quick Benchmark Preset Buttons */}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            className="border-amber-400 bg-amber-500/20 hover:bg-amber-500/30 text-xs text-amber-300 font-semibold shadow-sm"
            onClick={() => {
              handleSelectModel('qwen2.5:1.5b', true);
              handleSelectModel('openai/gpt-oss-120b', false);
            }}
          >
            ★ Local GPU (Qwen 1.5B) vs Cloud (120B)
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="border-slate-600 bg-white/5 hover:bg-white/10 text-xs text-white"
            onClick={() => {
              handleSelectModel('openai/gpt-oss-120b', true);
              handleSelectModel('openai/gpt-oss-20b', false);
            }}
          >
            Preset: 120B vs 20B
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="border-slate-600 bg-white/5 hover:bg-white/10 text-xs text-white"
            onClick={() => {
              handleSelectModel('openai/gpt-oss-120b', true);
              handleSelectModel('qwen/qwen3.8-27b', false);
            }}
          >
            Preset: 120B vs Qwen 27B
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="border-slate-600 bg-white/5 hover:bg-white/10 text-xs text-white"
            onClick={() => {
              handleSelectModel('fake', true);
              handleSelectModel('fake', false);
            }}
          >
            Preset: Offline Rule Mock
          </Button>
        </div>
      </div>

      {/* Notifications */}
      {errorMessage && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-600" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Configuration & Launch Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Model A Configuration */}
        <Card className="border-t-4 border-t-blue-600 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                Candidate Model A
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {modelA.provider.toUpperCase()}
              </span>
            </div>
            <CardTitle className="text-base mt-2">Model Selection & Parameters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Target Model</label>
              <select
                className="w-full border border-slate-300 rounded-md p-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={modelA.model_id}
                onChange={(e) => handleSelectModel(e.target.value, true)}
              >
                {availableModels.map((m) => (
                  <option key={m.model_id} value={m.model_id}>
                    {m.display_name} {m.is_available ? '✓' : '(No Key)'}
                  </option>
                ))}
              </select>
            </div>

            {/* Model A Pricing & Status Badge */}
            {(() => {
              const info = availableModels.find((m) => m.model_id === modelA.model_id);
              return (
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">API Status:</span>
                    <span className={info?.is_available ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                      {info?.status_message || 'Configured'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">Inference Pricing:</span>
                    <span className="font-mono text-slate-700">
                      ${info?.pricing_info.rates.prompt_per_m}/M in · ${info?.pricing_info.rates.completion_per_m}/M out
                    </span>
                  </div>
                </div>
              );
            })()}

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Temperature</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  className="w-full border border-slate-300 rounded p-1.5 text-xs font-mono"
                  value={modelA.temperature}
                  onChange={(e) => setModelA({ ...modelA, temperature: parseFloat(e.target.value) || 0.0 })}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Max Tokens</label>
                <input
                  type="number"
                  step="100"
                  min="200"
                  max="4000"
                  className="w-full border border-slate-300 rounded p-1.5 text-xs font-mono"
                  value={modelA.max_tokens}
                  onChange={(e) => setModelA({ ...modelA, max_tokens: parseInt(e.target.value) || 1500 })}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Model B Configuration */}
        <Card className="border-t-4 border-t-amber-500 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-600 bg-amber-50 px-2 py-0.5 rounded">
                Candidate Model B
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {modelB.provider.toUpperCase()}
              </span>
            </div>
            <CardTitle className="text-base mt-2">Model Selection & Parameters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Target Model</label>
              <select
                className="w-full border border-slate-300 rounded-md p-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                value={modelB.model_id}
                onChange={(e) => handleSelectModel(e.target.value, false)}
              >
                {availableModels.map((m) => (
                  <option key={m.model_id} value={m.model_id}>
                    {m.display_name} {m.is_available ? '✓' : '(No Key)'}
                  </option>
                ))}
              </select>
            </div>

            {/* Model B Pricing & Status Badge */}
            {(() => {
              const info = availableModels.find((m) => m.model_id === modelB.model_id);
              return (
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">API Status:</span>
                    <span className={info?.is_available ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                      {info?.status_message || 'Configured'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">Inference Pricing:</span>
                    <span className="font-mono text-slate-700">
                      ${info?.pricing_info.rates.prompt_per_m}/M in · ${info?.pricing_info.rates.completion_per_m}/M out
                    </span>
                  </div>
                </div>
              );
            })()}

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Temperature</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  className="w-full border border-slate-300 rounded p-1.5 text-xs font-mono"
                  value={modelB.temperature}
                  onChange={(e) => setModelB({ ...modelB, temperature: parseFloat(e.target.value) || 0.0 })}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Max Tokens</label>
                <input
                  type="number"
                  step="100"
                  min="200"
                  max="4000"
                  className="w-full border border-slate-300 rounded p-1.5 text-xs font-mono"
                  value={modelB.max_tokens}
                  onChange={(e) => setModelB({ ...modelB, max_tokens: parseInt(e.target.value) || 1500 })}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Dataset Selection & Execution Panel */}
        <Card className="border-t-4 border-t-emerald-600 shadow-sm flex flex-col justify-between">
          <div>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                  Evaluation Scope
                </span>
                <button
                  onClick={toggleSelectAll}
                  className="text-xs text-emerald-600 hover:text-emerald-800 font-medium"
                >
                  {selectedCaseIds.length === scenarios.length ? 'Deselect All' : 'Select All (7)'}
                </button>
              </div>
              <CardTitle className="text-base mt-2">Test Dataset (Version 1.0)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs max-h-48 overflow-y-auto pr-1">
              {scenarios.map((sc) => {
                const isSelected = selectedCaseIds.includes(sc.case_id);
                return (
                  <div
                    key={sc.case_id}
                    onClick={() => toggleCaseSelection(sc.case_id)}
                    className={`flex items-start gap-2 p-2 rounded cursor-pointer border transition-colors ${
                      isSelected
                        ? 'bg-emerald-50/60 border-emerald-200 text-slate-900'
                        : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
                    }`}
                  >
                    <span className="mt-0.5">
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-emerald-600" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-400" />
                      )}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{sc.title}</div>
                      <div className="text-[10px] text-slate-500 font-mono">
                        {sc.case_id} · {sc.scenario_type}
                      </div>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </div>

          <div className="p-6 pt-2">
            <Button
              className="w-full bg-[#002D72] hover:bg-[#001f54] text-white py-2.5 font-semibold flex items-center justify-center gap-2 shadow"
              disabled={isRunning || selectedCaseIds.length === 0}
              onClick={handleExecuteRun}
            >
              {isRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-[#F9A825]" />
                  <span>Evaluating Side-by-Side...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current text-[#F9A825]" />
                  <span>Execute Benchmark ({selectedCaseIds.length} Cases)</span>
                </>
              )}
            </Button>
            {statusMessage && (
              <p className="text-[11px] text-slate-500 text-center mt-2 font-medium">
                {statusMessage}
              </p>
            )}
          </div>
        </Card>
      </div>

      {/* Historical Run Selector Bar */}
      {recentRuns.length > 0 && (
        <div className="bg-white p-3 rounded-lg border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700">Persisted Benchmark Runs:</span>
            <select
              className="border border-slate-300 rounded px-2.5 py-1 text-xs bg-slate-50 font-mono"
              value={activeRun?.run_id || ''}
              onChange={(e) => handleSelectRun(e.target.value)}
            >
              {recentRuns.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.run_id} ({r.model_a_id.split('/').pop()} vs {r.model_b_id.split('/').pop()}) ·{' '}
                  {new Date(r.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </option>
              ))}
            </select>
          </div>

          {activeRun && (
            <div className="flex flex-wrap items-center gap-4 text-slate-500">
              <span>
                Run Status: <strong className="text-emerald-600 uppercase">{activeRun.status}</strong>
              </span>
              <span>
                Completed: <strong>{activeRun.completed_cases} / {activeRun.total_cases}</strong>
              </span>
              <span>
                Executed:{' '}
                <strong>
                  {new Date(activeRun.started_at).toLocaleDateString()} {new Date(activeRun.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </strong>
              </span>

              <div className="flex items-center gap-2 pl-2 border-l border-slate-300">
                <a
                  href={api.exportBenchmarkRunUrl(activeRun.run_id, 'json')}
                  download={`benchmark-${activeRun.run_id}.json`}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors shadow-xs"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export JSON</span>
                </a>
                <a
                  href={api.exportBenchmarkRunUrl(activeRun.run_id, 'csv')}
                  download={`benchmark-${activeRun.run_id}.csv`}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded hover:bg-emerald-100 transition-colors shadow-xs"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export CSV</span>
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Active Run Results & Metrics */}
      {activeRun ? (
        <div className="space-y-6">
          {/* Aggregate KPI Comparison Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {/* Overall Score */}
            <Card className="p-3 border-l-4 border-l-blue-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Overall Quality</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  {aggA?.average_scores.overall_quality?.toFixed(2) || '0.00'}
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  {aggB?.average_scores.overall_quality?.toFixed(2) || '0.00'}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Scale 1-5</span>
                <span
                  className={`font-semibold ${
                    (comp?.overall_score_delta_mean || 0) >= 0 ? 'text-emerald-600' : 'text-amber-600'
                  }`}
                >
                  Δ {(comp?.overall_score_delta_mean || 0) > 0 ? '+' : ''}
                  {comp?.overall_score_delta_mean?.toFixed(2)}
                </span>
              </div>
            </Card>

            {/* Evidence Grounding */}
            <Card className="p-3 border-l-4 border-l-indigo-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Evidence Grounding</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  {aggA?.average_scores.evidence_grounding?.toFixed(2) || '0.00'}
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  {aggB?.average_scores.evidence_grounding?.toFixed(2) || '0.00'}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Factual Integrity</span>
                <span className="font-semibold text-slate-600">
                  {aggA?.schema_pass_rate_pct}% Schema
                </span>
              </div>
            </Card>

            {/* Deterministic Pass Rate */}
            <Card className="p-3 border-l-4 border-l-emerald-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Deterministic Pass</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  {aggA?.deterministic_pass_rate_pct}%
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  {aggB?.deterministic_pass_rate_pct}%
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Zero Hallucination</span>
                <span className="text-emerald-600 font-medium">Pydantic / IDs</span>
              </div>
            </Card>

            {/* Human Review Trigger Rate */}
            <Card className="p-3 border-l-4 border-l-purple-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Human Review Rate</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  {aggA?.human_review_rate_pct}%
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  {aggB?.human_review_rate_pct}%
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Compliance Safety</span>
                <span className="text-purple-600 font-medium">Triggers</span>
              </div>
            </Card>

            {/* Mean Latency */}
            <Card className="p-3 border-l-4 border-l-teal-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Mean Latency</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  {aggA?.mean_latency_ms?.toFixed(0)}ms
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  {aggB?.mean_latency_ms?.toFixed(0)}ms
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Speedup</span>
                <span className="font-semibold text-teal-600">
                  {comp?.speedup_factor}x faster
                </span>
              </div>
            </Card>

            {/* Inference Cost */}
            <Card className="p-3 border-l-4 border-l-rose-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Total Cost (USD)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  ${aggA?.total_cost_usd?.toFixed(4)}
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  ${aggB?.total_cost_usd?.toFixed(4)}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Cost Savings</span>
                <span className="font-semibold text-emerald-600">
                  {comp?.cost_savings_pct}% lower
                </span>
              </div>
            </Card>
          </div>

          {/* Detailed Performance, Hardware & Quality KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {/* P95 Latency */}
            <Card className="p-3 border-l-4 border-l-cyan-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">P95 Latency</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  {aggA?.p95_latency_ms ? `${aggA.p95_latency_ms.toFixed(0)}ms` : `${aggA?.mean_latency_ms?.toFixed(0)}ms`}
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  {aggB?.p95_latency_ms ? `${aggB.p95_latency_ms.toFixed(0)}ms` : `${aggB?.mean_latency_ms?.toFixed(0)}ms`}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Tail Latency</span>
                <span className="font-semibold text-cyan-600">
                  {comp?.p95_latency_difference_ms !== undefined ? `Δ ${comp.p95_latency_difference_ms}ms` : '95th Percentile'}
                </span>
              </div>
            </Card>

            {/* Citation Accuracy */}
            <Card className="p-3 border-l-4 border-l-sky-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Citation Accuracy</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  {aggA?.citation_accuracy_pct !== undefined ? `${aggA.citation_accuracy_pct}%` : '100%'}
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  {aggB?.citation_accuracy_pct !== undefined ? `${aggB.citation_accuracy_pct}%` : '100%'}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Valid Citations</span>
                <span className="font-semibold text-sky-600">ID Verification</span>
              </div>
            </Card>

            {/* Evidence Coverage */}
            <Card className="p-3 border-l-4 border-l-blue-500 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Evidence Coverage</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  {aggA?.evidence_coverage_pct !== undefined ? `${aggA.evidence_coverage_pct}%` : '100%'}
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  {aggB?.evidence_coverage_pct !== undefined ? `${aggB.evidence_coverage_pct}%` : '100%'}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Evidence Depth</span>
                <span className="font-semibold text-blue-600">Cross-item</span>
              </div>
            </Card>

            {/* Generation Speed */}
            <Card className="p-3 border-l-4 border-l-emerald-500 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Throughput (Tok/s)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-lg font-bold text-blue-700 font-mono">
                  {aggA?.tokens_per_second ? `${aggA.tokens_per_second}` : 'N/A'}
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-lg font-bold text-amber-600 font-mono">
                  {aggB?.tokens_per_second ? `${aggB.tokens_per_second}` : 'N/A'}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Tokens / Sec</span>
                <span className="font-semibold text-emerald-600">Generation</span>
              </div>
            </Card>

            {/* Local GPU VRAM Profile */}
            <Card className="p-3 border-l-4 border-l-violet-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">GPU VRAM Profile</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-xs font-bold text-blue-700 font-mono truncate max-w-[45%]">
                  {aggA?.gpu_vram_used_mb ? `${aggA.gpu_vram_used_mb}MB` : 'N/A'}
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-xs font-bold text-amber-600 font-mono truncate max-w-[45%]">
                  {aggB?.gpu_vram_used_mb ? `${aggB.gpu_vram_used_mb}MB` : 'N/A'}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">nvidia-smi</span>
                <span className="font-semibold text-violet-600">VRAM Footprint</span>
              </div>
            </Card>

            {/* Projected Cost / 1k Cases */}
            <Card className="p-3 border-l-4 border-l-pink-600 bg-white">
              <span className="text-[11px] text-slate-500 font-medium">Cost / 1,000 Cases</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-sm font-bold text-blue-700 font-mono">
                  ${(aggA?.projected_cost_per_1000_cases_usd ?? ((aggA?.total_cost_usd || 0) * 1000 / Math.max(1, activeRun.completed_cases))).toFixed(2)}
                </span>
                <span className="text-xs text-slate-400">vs</span>
                <span className="text-sm font-bold text-amber-600 font-mono">
                  ${(aggB?.projected_cost_per_1000_cases_usd ?? ((aggB?.total_cost_usd || 0) * 1000 / Math.max(1, activeRun.completed_cases))).toFixed(2)}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <span className="text-slate-400">Projected Run</span>
                <span className="font-semibold text-pink-600">USD</span>
              </div>
            </Card>
          </div>

          {/* Visual Score Comparison Bar Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 shadow-sm">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Scale className="w-4 h-4 text-[#002D72]" />
                    Dimension Quality Scores (1-5 Rubric)
                  </CardTitle>
                  <div className="flex items-center gap-4 text-xs">
                    <span className="flex items-center gap-1.5 font-medium text-blue-700">
                      <span className="w-3 h-3 bg-blue-600 rounded-sm" />
                      Model A ({activeRun.model_a_config.model_id.split('/').pop()})
                    </span>
                    <span className="flex items-center gap-1.5 font-medium text-amber-700">
                      <span className="w-3 h-3 bg-amber-500 rounded-sm" />
                      Model B ({activeRun.model_b_config.model_id.split('/').pop()})
                    </span>
                  </div>
                </div>
                <CardDescription className="text-xs">
                  Averaged over all evaluated cases in this benchmark run.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dimensionChartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="dimension" tick={{ fontSize: 11, fill: '#64748B' }} />
                      <YAxis domain={[0, 5]} tick={{ fontSize: 11, fill: '#64748B' }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0F172A',
                          borderRadius: '8px',
                          color: '#F8FAFC',
                          fontSize: '12px',
                        }}
                      />
                      <Bar
                        dataKey={activeRun.model_a_config.model_id}
                        name={`Model A: ${activeRun.model_a_config.model_id.split('/').pop()}`}
                        fill="#2563EB"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        dataKey={activeRun.model_b_config.model_id}
                        name={`Model B: ${activeRun.model_b_config.model_id.split('/').pop()}`}
                        fill="#F59E0B"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Head-to-Head Win Card */}
            <Card className="shadow-sm flex flex-col justify-between">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-600" />
                  Head-to-Head Win Record
                </CardTitle>
                <CardDescription className="text-xs">
                  Overall quality decisions across {activeRun.completed_cases} test cases.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <span className="text-[11px] font-bold text-blue-700 block">Model A Wins</span>
                    <span className="text-2xl font-extrabold text-blue-800 font-mono">
                      {comp?.model_a_wins || 0}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                    <span className="text-[11px] font-bold text-slate-600 block">Ties</span>
                    <span className="text-2xl font-extrabold text-slate-700 font-mono">
                      {comp?.ties || 0}
                    </span>
                  </div>
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <span className="text-[11px] font-bold text-amber-700 block">Model B Wins</span>
                    <span className="text-2xl font-extrabold text-amber-800 font-mono">
                      {comp?.model_b_wins || 0}
                    </span>
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1.5">
                  <div className="font-semibold text-slate-700">Benchmark Verdict Summary:</div>
                  <p className="text-slate-600 text-[11px] leading-relaxed">
                    {(comp?.model_a_wins || 0) > (comp?.model_b_wins || 0)
                      ? `Model A (${activeRun.model_a_config.model_id.split('/').pop()}) outperformed Model B with +${comp?.overall_score_delta_mean?.toFixed(2)} higher average quality.`
                      : (comp?.model_b_wins || 0) > (comp?.model_a_wins || 0)
                      ? `Model B (${activeRun.model_b_config.model_id.split('/').pop()}) outperformed Model A with superior grounding or structure.`
                      : 'Candidate models achieved equivalent overall quality scores across this test suite.'}
                  </p>
                </div>
              </CardContent>
              <div className="p-4 bg-slate-100 border-t border-slate-200 text-[11px] text-slate-500 rounded-b-lg flex justify-between items-center">
                <span>Judge: Groq GPT-OSS 120B</span>
                <span className="font-mono">Langfuse Traced ✓</span>
              </div>
            </Card>
          </div>

          {/* Filterable Per-Case Comparison Table */}
          <Card className="shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-200">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Layers className="w-4 h-4 text-[#002D72]" />
                    Per-Case Side-by-Side Comparison Matrix
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Inspect granular differences, deterministic check results, and judge scores for every case.
                  </CardDescription>
                </div>

                <div className="flex items-center gap-2">
                  <Filter className="w-3.5 h-3.5 text-slate-400" />
                  <select
                    className="border border-slate-300 rounded px-2 py-1 text-xs bg-white text-slate-700"
                    value={scenarioFilter}
                    onChange={(e) => setScenarioFilter(e.target.value)}
                  >
                    <option value="ALL">All Scenario Types ({activeRun.cases.length})</option>
                    <option value="CLEAN">Clean Investigations</option>
                    <option value="SUSPICIOUS">Suspicious Mule Rings</option>
                    <option value="UNSUPPORTED_TRAP">Unsupported Traps</option>
                    <option value="INCOMPLETE_EVIDENCE">Incomplete Evidence</option>
                    <option value="REGRESSION">Regression Cases (SAR-001 / CLEAN-002)</option>
                    <option value="SCHEMA_STRESS">Schema Stress Tests</option>
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <TableContainer>
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50/80 text-[11px]">
                      <TableHead>Case Identifier & Type</TableHead>
                      <TableHead className="text-blue-700">Model A Quality</TableHead>
                      <TableHead className="text-blue-700">Model A Grounding</TableHead>
                      <TableHead className="text-amber-700">Model B Quality</TableHead>
                      <TableHead className="text-amber-700">Model B Grounding</TableHead>
                      <TableHead>Winner</TableHead>
                      <TableHead>Latency (A vs B)</TableHead>
                      <TableHead className="text-right">Deep Inspection</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displayedCases.map((c) => {
                      const scoreA = c.model_a_evaluation?.scores?.overall_quality;
                      const groundA = c.model_a_evaluation?.scores?.evidence_grounding;
                      const scoreB = c.model_b_evaluation?.scores?.overall_quality;
                      const groundB = c.model_b_evaluation?.scores?.evidence_grounding;
                      const winner = c.differences_summary?.winner;

                      return (
                        <TableRow key={c.case_id} className="text-xs hover:bg-slate-50/70">
                          <TableCell className="font-medium">
                            <div className="font-semibold text-slate-900">{c.case_id}</div>
                            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                              {c.scenario_type}
                            </span>
                          </TableCell>

                          <TableCell>
                            <span className="font-mono font-bold text-blue-700">
                              {scoreA !== undefined ? `${scoreA}/5` : 'N/A'}
                            </span>
                            {c.model_a_validation?.passed ? (
                              <span className="ml-1 text-[10px] text-emerald-600">✓ Det</span>
                            ) : (
                              <span className="ml-1 text-[10px] text-rose-500 font-semibold">✗ Det</span>
                            )}
                          </TableCell>

                          <TableCell>
                            <span className="font-mono text-slate-700">
                              {groundA !== undefined ? `${groundA}/5` : 'N/A'}
                            </span>
                          </TableCell>

                          <TableCell>
                            <span className="font-mono font-bold text-amber-600">
                              {scoreB !== undefined ? `${scoreB}/5` : 'N/A'}
                            </span>
                            {c.model_b_validation?.passed ? (
                              <span className="ml-1 text-[10px] text-emerald-600">✓ Det</span>
                            ) : (
                              <span className="ml-1 text-[10px] text-rose-500 font-semibold">✗ Det</span>
                            )}
                          </TableCell>

                          <TableCell>
                            <span className="font-mono text-slate-700">
                              {groundB !== undefined ? `${groundB}/5` : 'N/A'}
                            </span>
                          </TableCell>

                          <TableCell>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                winner === 'MODEL_A'
                                  ? 'bg-blue-100 text-blue-800'
                                  : winner === 'MODEL_B'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-slate-100 text-slate-700'
                              }`}
                            >
                              {winner === 'MODEL_A' ? 'Model A' : winner === 'MODEL_B' ? 'Model B' : 'Tie'}
                            </span>
                          </TableCell>

                          <TableCell className="font-mono text-[11px] text-slate-600">
                            {c.model_a_latency_ms?.toFixed(0)}ms vs {c.model_b_latency_ms?.toFixed(0)}ms
                          </TableCell>

                          <TableCell className="text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs py-1 px-2.5 h-auto text-[#002D72] border-[#002D72]/30 hover:bg-[#002D72]/5"
                              onClick={() => setInspectingCase(c)}
                            >
                              Inspect Diff ↗
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card className="p-12 text-center border-dashed border-2 border-slate-300">
          <Scale className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-700">No Benchmark Execution Loaded</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
            Select candidate Model A and Model B above and click "Execute Benchmark" to run side-by-side
            evaluation across the canonical test dataset.
          </p>
        </Card>
      )}

      {/* Deep Case Inspection Modal */}
      {inspectingCase && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-300 w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono uppercase bg-[#F9A825] text-slate-950 font-bold px-1.5 py-0.5 rounded">
                    {inspectingCase.scenario_type}
                  </span>
                  <h2 className="text-lg font-bold">{inspectingCase.case_id}</h2>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Side-by-Side Report Inspection & Grounding Evaluation
                </p>
              </div>

              <div className="flex items-center gap-3">
                {inspectingCase.model_a_trace_url && (
                  <a
                    href={inspectingCase.model_a_trace_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1.5 rounded border border-slate-700"
                  >
                    <span>View in Langfuse</span>
                    <ExternalLink className="w-3 h-3 text-[#F9A825]" />
                  </a>
                )}
                <button
                  onClick={() => setInspectingCase(null)}
                  className="text-slate-400 hover:text-white p-1 rounded-md"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Content - Side by Side Comparison */}
            <div className="p-6 overflow-y-auto space-y-6 text-xs flex-1">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Model A Column */}
                <div className="space-y-4 border border-blue-200 bg-blue-50/20 p-4 rounded-xl">
                  <div className="flex justify-between items-center pb-2 border-b border-blue-200">
                    <span className="font-bold text-sm text-blue-800">
                      Candidate A: {activeRun?.model_a_config.model_id}
                    </span>
                    <span className="font-mono text-blue-700 font-bold">
                      Score: {inspectingCase.model_a_evaluation?.scores?.overall_quality}/5
                    </span>
                  </div>

                  <div>
                    <span className="font-semibold text-slate-700 block mb-1">Generated Summary:</span>
                    <p className="p-2.5 bg-white rounded border border-slate-200 text-slate-800 leading-relaxed font-sans">
                      {inspectingCase.model_a_output?.summary || inspectingCase.model_a_error || 'No summary'}
                    </p>
                  </div>

                  <div>
                    <span className="font-semibold text-slate-700 block mb-1">Findings & Citations:</span>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto">
                      {(inspectingCase.model_a_output?.findings || []).map((f: any, idx: number) => (
                        <div key={idx} className="p-2 bg-white rounded border border-slate-200 text-[11px]">
                          <span className="font-medium text-slate-900 block">{f.finding}</span>
                          <div className="mt-1 flex gap-1 flex-wrap">
                            {(f.evidence_ids || []).map((ev: string) => (
                              <span key={ev} className="font-mono text-[9px] bg-blue-100 text-blue-800 px-1 py-0.5 rounded">
                                {ev}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Deterministic Validation Details */}
                  <div className="p-2.5 bg-white rounded border border-slate-200 space-y-1">
                    <div className="flex justify-between font-semibold">
                      <span>Deterministic Validation:</span>
                      <span className={inspectingCase.model_a_validation?.passed ? 'text-emerald-600' : 'text-rose-600'}>
                        {inspectingCase.model_a_validation?.passed ? 'PASSED ✓' : 'FAILED ✗'}
                      </span>
                    </div>
                    {inspectingCase.model_a_validation?.discrepancies?.length > 0 && (
                      <div className="text-rose-600 text-[10px] space-y-0.5 pt-1">
                        {inspectingCase.model_a_validation.discrepancies.map((d: string, i: number) => (
                          <div key={i}>• {d}</div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Judge Evaluation Feedback */}
                  <div className="p-2.5 bg-white rounded border border-slate-200 space-y-1">
                    <div className="font-semibold text-slate-700">Judge Rationale:</div>
                    <p className="text-slate-600 text-[11px] leading-relaxed">
                      {inspectingCase.model_a_evaluation?.summary}
                    </p>
                  </div>

                  {/* Detailed Profiling & Grounding Metrics */}
                  {inspectingCase.model_a_metrics && (
                    <div className="p-2.5 bg-white rounded border border-blue-200 space-y-2">
                      <div className="font-semibold text-blue-900 flex justify-between items-center text-[11px]">
                        <span>Granular Grounding & Inference Profile:</span>
                        <span className="font-mono text-[10px] text-blue-700">
                          {inspectingCase.model_a_metrics.tokens_per_second || 0} tok/s
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-2 text-[10px]">
                        <div className="bg-slate-50 p-1.5 rounded border border-slate-100">
                          <span className="text-slate-500 block">Citation Accuracy:</span>
                          <span className="font-bold text-slate-800">
                            {inspectingCase.model_a_metrics.citation_metrics?.citation_accuracy_pct ?? 100}%
                          </span>
                        </div>
                        <div className="bg-slate-50 p-1.5 rounded border border-slate-100">
                          <span className="text-slate-500 block">Evidence Coverage:</span>
                          <span className="font-bold text-slate-800">
                            {inspectingCase.model_a_metrics.citation_metrics?.evidence_coverage_pct ?? 100}%
                          </span>
                        </div>
                      </div>

                      {/* GPU VRAM profile if available */}
                      {inspectingCase.model_a_metrics.gpu_metrics?.measured && (
                        <div className="bg-violet-50 p-1.5 rounded border border-violet-200 text-[10px] text-violet-900">
                          <span className="font-semibold block">Local GPU Profile (nvidia-smi):</span>
                          <span>
                            {inspectingCase.model_a_metrics.gpu_metrics.vram_used_mb} MB VRAM used / {inspectingCase.model_a_metrics.gpu_metrics.vram_total_mb} MB ({inspectingCase.model_a_metrics.gpu_metrics.utilization_pct}%) on {inspectingCase.model_a_metrics.gpu_metrics.gpu_name}
                          </span>
                        </div>
                      )}

                      {/* Ground truth match if present */}
                      {inspectingCase.model_a_metrics.ground_truth_metrics?.has_ground_truth && (
                        <div className="bg-emerald-50 p-1.5 rounded border border-emerald-200 text-[10px] text-emerald-900">
                          <span className="font-semibold block">Ground Truth Evaluation:</span>
                          <div className="flex justify-between mt-0.5">
                            <span>Precision: {inspectingCase.model_a_metrics.ground_truth_metrics.precision}</span>
                            <span>Recall: {inspectingCase.model_a_metrics.ground_truth_metrics.recall}</span>
                            <span className="font-bold">F1: {inspectingCase.model_a_metrics.ground_truth_metrics.f1_score}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Model B Column */}
                <div className="space-y-4 border border-amber-200 bg-amber-50/20 p-4 rounded-xl">
                  <div className="flex justify-between items-center pb-2 border-b border-amber-200">
                    <span className="font-bold text-sm text-amber-800">
                      Candidate B: {activeRun?.model_b_config.model_id}
                    </span>
                    <span className="font-mono text-amber-700 font-bold">
                      Score: {inspectingCase.model_b_evaluation?.scores?.overall_quality}/5
                    </span>
                  </div>

                  <div>
                    <span className="font-semibold text-slate-700 block mb-1">Generated Summary:</span>
                    <p className="p-2.5 bg-white rounded border border-slate-200 text-slate-800 leading-relaxed font-sans">
                      {inspectingCase.model_b_output?.summary || inspectingCase.model_b_error || 'No summary'}
                    </p>
                  </div>

                  <div>
                    <span className="font-semibold text-slate-700 block mb-1">Findings & Citations:</span>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto">
                      {(inspectingCase.model_b_output?.findings || []).map((f: any, idx: number) => (
                        <div key={idx} className="p-2 bg-white rounded border border-slate-200 text-[11px]">
                          <span className="font-medium text-slate-900 block">{f.finding}</span>
                          <div className="mt-1 flex gap-1 flex-wrap">
                            {(f.evidence_ids || []).map((ev: string) => (
                              <span key={ev} className="font-mono text-[9px] bg-amber-100 text-amber-800 px-1 py-0.5 rounded">
                                {ev}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Deterministic Validation Details */}
                  <div className="p-2.5 bg-white rounded border border-slate-200 space-y-1">
                    <div className="flex justify-between font-semibold">
                      <span>Deterministic Validation:</span>
                      <span className={inspectingCase.model_b_validation?.passed ? 'text-emerald-600' : 'text-rose-600'}>
                        {inspectingCase.model_b_validation?.passed ? 'PASSED ✓' : 'FAILED ✗'}
                      </span>
                    </div>
                    {inspectingCase.model_b_validation?.discrepancies?.length > 0 && (
                      <div className="text-rose-600 text-[10px] space-y-0.5 pt-1">
                        {inspectingCase.model_b_validation.discrepancies.map((d: string, i: number) => (
                          <div key={i}>• {d}</div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Judge Evaluation Feedback */}
                  <div className="p-2.5 bg-white rounded border border-slate-200 space-y-1">
                    <div className="font-semibold text-slate-700">Judge Rationale:</div>
                    <p className="text-slate-600 text-[11px] leading-relaxed">
                      {inspectingCase.model_b_evaluation?.summary}
                    </p>
                  </div>

                  {/* Detailed Profiling & Grounding Metrics */}
                  {inspectingCase.model_b_metrics && (
                    <div className="p-2.5 bg-white rounded border border-amber-200 space-y-2">
                      <div className="font-semibold text-amber-900 flex justify-between items-center text-[11px]">
                        <span>Granular Grounding & Inference Profile:</span>
                        <span className="font-mono text-[10px] text-amber-700">
                          {inspectingCase.model_b_metrics.tokens_per_second || 0} tok/s
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-2 text-[10px]">
                        <div className="bg-slate-50 p-1.5 rounded border border-slate-100">
                          <span className="text-slate-500 block">Citation Accuracy:</span>
                          <span className="font-bold text-slate-800">
                            {inspectingCase.model_b_metrics.citation_metrics?.citation_accuracy_pct ?? 100}%
                          </span>
                        </div>
                        <div className="bg-slate-50 p-1.5 rounded border border-slate-100">
                          <span className="text-slate-500 block">Evidence Coverage:</span>
                          <span className="font-bold text-slate-800">
                            {inspectingCase.model_b_metrics.citation_metrics?.evidence_coverage_pct ?? 100}%
                          </span>
                        </div>
                      </div>

                      {/* GPU VRAM profile if available */}
                      {inspectingCase.model_b_metrics.gpu_metrics?.measured && (
                        <div className="bg-violet-50 p-1.5 rounded border border-violet-200 text-[10px] text-violet-900">
                          <span className="font-semibold block">Local GPU Profile (nvidia-smi):</span>
                          <span>
                            {inspectingCase.model_b_metrics.gpu_metrics.vram_used_mb} MB VRAM used / {inspectingCase.model_b_metrics.gpu_metrics.vram_total_mb} MB ({inspectingCase.model_b_metrics.gpu_metrics.utilization_pct}%) on {inspectingCase.model_b_metrics.gpu_metrics.gpu_name}
                          </span>
                        </div>
                      )}

                      {/* Ground truth match if present */}
                      {inspectingCase.model_b_metrics.ground_truth_metrics?.has_ground_truth && (
                        <div className="bg-emerald-50 p-1.5 rounded border border-emerald-200 text-[10px] text-emerald-900">
                          <span className="font-semibold block">Ground Truth Evaluation:</span>
                          <div className="flex justify-between mt-0.5">
                            <span>Precision: {inspectingCase.model_b_metrics.ground_truth_metrics.precision}</span>
                            <span>Recall: {inspectingCase.model_b_metrics.ground_truth_metrics.recall}</span>
                            <span className="font-bold">F1: {inspectingCase.model_b_metrics.ground_truth_metrics.f1_score}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-between items-center text-xs">
              <span className="text-slate-500 font-mono">
                Latencies: Model A {inspectingCase.model_a_latency_ms}ms · Model B {inspectingCase.model_b_latency_ms}ms
              </span>
              <Button variant="outline" size="sm" onClick={() => setInspectingCase(null)}>
                Close Inspection
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
