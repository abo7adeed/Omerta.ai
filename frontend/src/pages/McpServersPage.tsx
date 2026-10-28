import React, { useState, useEffect } from 'react';
import {
  Server,
  Cpu,
  Layers,
  Terminal,
  Play,
  Copy,
  Check,
  ShieldCheck,
  ExternalLink,
  Search,
  Code2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Sparkles,
  Database,
  Share2,
  ShieldAlert,
  ScrollText,
  Wallet,
  AlertCircle,
  Activity,
  ArrowRight,
  GitPullRequest,
  Clock,
  Radio,
  FileCheck2,
} from 'lucide-react';
import { api } from '../api/client';

interface ToolSchema {
  name: string;
  description: string;
  input_schema: {
    properties?: Record<string, { title?: string; type?: string; description?: string; default?: any }>;
    required?: string[];
  };
}

interface McpServer {
  id: string;
  name: string;
  title: string;
  description: string;
  category: string;
  transport: string;
  protocol: string;
  read_only: boolean;
  command: string;
  icon: string;
  status: 'ACTIVE' | 'ERROR' | 'OFFLINE';
  tools_count: number;
  tools: ToolSchema[];
}

interface AuditInvocation {
  id: string;
  timestamp: string;
  server_id: string;
  tool_name: string;
  caller: string;
  arguments: Record<string, any>;
  success: boolean;
  duration_ms: number;
  result_preview: string;
}

export const McpServersPage: React.FC = () => {
  // Navigation Tabs
  const [activeTab, setActiveTab] = useState<'registry' | 'simulation' | 'audit'>('registry');

  // Servers State
  const [servers, setServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [expandedServerId, setExpandedServerId] = useState<string | null>('transaction_server');
  const [copiedCommand, setCopiedCommand] = useState<string | null>(null);

  // Test Tool Runner State
  const [activeTestServer, setActiveTestServer] = useState<McpServer | null>(null);
  const [activeTestTool, setActiveTestTool] = useState<ToolSchema | null>(null);
  const [testArguments, setTestArguments] = useState<string>('{}');
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);


  // Live Simulation State
  const [simAccount, setSimAccount] = useState('ACC-1001');
  const [simScenario, setSimScenario] = useState('MULE_SYNDICATE_STRUCTURING');
  const [simLoading, setSimLoading] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);
  const [simExpandedStep, setSimExpandedStep] = useState<number | null>(null);

  // Audit Log State
  const [auditLogs, setAuditLogs] = useState<AuditInvocation[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [autoRefreshAudit, setAutoRefreshAudit] = useState(false);

  const fetchServers = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getMcpServers();
      setServers(res.servers || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load MCP servers from backend.');
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      setAuditLoading(true);
      const res = await api.getMcpAuditLog(40);
      setAuditLogs(res.invocations || []);
    } catch (err) {
      console.error('Failed to fetch MCP audit logs:', err);
    } finally {
      setAuditLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
    fetchAuditLogs();
  }, []);

  useEffect(() => {
    if (!autoRefreshAudit || activeTab !== 'audit') return;
    const interval = setInterval(fetchAuditLogs, 3000);
    return () => clearInterval(interval);
  }, [autoRefreshAudit, activeTab]);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCommand(id);
    setTimeout(() => setCopiedCommand(null), 2000);
  };

  const openToolTester = (server: McpServer, tool: ToolSchema) => {
    setActiveTestServer(server);
    setActiveTestTool(tool);
    setTestResult(null);

    const template: Record<string, any> = {};
    if (tool.input_schema?.properties) {
      Object.entries(tool.input_schema.properties).forEach(([k, prop]) => {
        if (prop.default !== undefined) {
          template[k] = prop.default;
        } else if (prop.type === 'integer' || prop.type === 'number') {
          template[k] = 10;
        } else if (prop.type === 'boolean') {
          template[k] = true;
        } else {
          template[k] = k.includes('id') ? 'ACC-1001' : k.includes('query') ? 'smurfing layering' : 'sample_value';
        }
      });
    }
    setTestArguments(JSON.stringify(template, null, 2));
  };

  const executeToolTest = async () => {
    if (!activeTestServer || !activeTestTool) return;
    try {
      setTestLoading(true);
      setTestResult(null);
      let parsedArgs = {};
      try {
        parsedArgs = JSON.parse(testArguments);
      } catch (err) {
        setTestResult({ success: false, error: 'Malformed JSON input arguments' });
        return;
      }

      const res = await api.testMcpTool({
        server_id: activeTestServer.id,
        tool_name: activeTestTool.name,
        arguments: parsedArgs,
      });
      setTestResult(res);
      fetchAuditLogs();
    } catch (err: any) {
      setTestResult({
        success: false,
        error: err?.message || 'Execution failed due to network or server error.',
      });
    } finally {
      setTestLoading(false);
    }
  };

  const runSimulation = async () => {
    try {
      setSimLoading(true);
      setSimResult(null);
      const res = await api.simulateMcpInvestigation({
        account_id: simAccount,
        scenario: simScenario,
      });
      setSimResult(res);
      fetchAuditLogs();
    } catch (err: any) {
      alert(`Simulation failed: ${err?.message || 'Network error'}`);
    } finally {
      setSimLoading(false);
    }
  };

  const getServerIcon = (iconName: string) => {
    switch (iconName) {
      case 'Wallet':
        return <Wallet className="w-6 h-6 text-emerald-500" />;
      case 'Share2':
        return <Share2 className="w-6 h-6 text-blue-500" />;
      case 'ShieldAlert':
        return <ShieldAlert className="w-6 h-6 text-amber-500" />;
      case 'ScrollText':
        return <ScrollText className="w-6 h-6 text-purple-500" />;
      default:
        return <Database className="w-6 h-6 text-indigo-500" />;
    }
  };

  const categories = ['ALL', 'Ledger & Entities', 'Graph Topology (Neo4j)', 'Risk & Machine Learning', 'Regulatory & AML Corpus'];

  const filteredServers = servers.filter((s) => {
    const matchesCat = selectedCategory === 'ALL' || s.category === selectedCategory;
    const matchesSearch =
      searchQuery === '' ||
      s.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.tools.some(
        (t) =>
          t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          t.description.toLowerCase().includes(searchQuery.toLowerCase())
      );
    return matchesCat && matchesSearch;
  });

  const totalTools = servers.reduce((acc, curr) => acc + (curr.tools_count || 0), 0);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-8 text-white shadow-2xl border border-indigo-900/50">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-indigo-500/20 border border-indigo-400/30 text-indigo-400">
                <Cpu className="w-7 h-7" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                Model Context Protocol (MCP) Hub
                <span className="px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  4 Active Servers
                </span>
              </h1>
            </div>
            <p className="text-slate-300 max-w-2xl text-sm leading-relaxed">
              Standardized Model Context Protocol endpoints providing LLM agents with deterministic, read-only
              forensic intelligence over Ledgers, Neo4j Topology, Deterministic Risk Models, and the AML Regulatory Corpus.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <a
              href="http://localhost:3000"
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/25 flex items-center gap-2 transition"
            >
              <Activity className="w-4 h-4" /> Open Langfuse APM ↗
            </a>
          </div>
        </div>

        {/* Invariant & Metrics Bar */}
        <div className="mt-6 pt-6 border-t border-indigo-900/40 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <div>
              <div className="text-xs text-slate-400">Zero-Write Invariant</div>
              <div className="text-xs font-semibold text-emerald-400">100% Read-Only Tools</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Terminal className="w-5 h-5 text-indigo-400" />
            <div>
              <div className="text-xs text-slate-400">Standard Transport</div>
              <div className="text-xs font-semibold text-slate-200">JSON-RPC 2.0 (stdio)</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Layers className="w-5 h-5 text-blue-400" />
            <div>
              <div className="text-xs text-slate-400">Registered Tools</div>
              <div className="text-xs font-semibold text-slate-200">{totalTools} Active Capabilities</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <div>
              <div className="text-xs text-slate-400">Agent Observability</div>
              <div className="text-xs font-semibold text-amber-300">Langfuse + Realtime Feed</div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('registry')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 ${
            activeTab === 'registry'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Server className="w-4 h-4" /> Servers & Tool Schemas ({servers.length})
        </button>
        <button
          onClick={() => setActiveTab('simulation')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 ${
            activeTab === 'simulation'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <GitPullRequest className="w-4 h-4" /> Agent Flow & Live Simulation
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        </button>
        <button
          onClick={() => {
            setActiveTab('audit');
            fetchAuditLogs();
          }}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 ${
            activeTab === 'audit'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Clock className="w-4 h-4" /> Live Invocations Audit ({auditLogs.length})
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: REGISTRY & TOOL SCHEMAS                                            */}
      {/* ========================================================================= */}
      {activeTab === 'registry' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search MCP servers or tools by name, parameter, or keyword..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                    selectedCategory === cat
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  {cat}
                </button>
              ))}
              <button
                onClick={fetchServers}
                title="Refresh MCP Servers"
                className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Servers Grid */}
          {error ? (
            <div className="p-8 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-center space-y-3">
              <AlertCircle className="w-8 h-8 mx-auto" />
              <div className="font-semibold">{error}</div>
              <button
                onClick={fetchServers}
                className="px-4 py-2 rounded-lg bg-red-500 text-white text-xs font-medium"
              >
                Retry Fetching Servers
              </button>
            </div>
          ) : loading ? (
            <div className="py-20 text-center space-y-4">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-indigo-500" />
              <div className="text-xs text-slate-400">Querying Model Context Protocol servers...</div>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredServers.map((server) => {
                const isExpanded = expandedServerId === server.id;
                return (
                  <div
                    key={server.id}
                    className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden transition"
                  >
                    {/* Server Header */}
                    <div className="p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800/80">
                      <div className="flex items-start gap-4">
                        <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex-shrink-0">
                          {getServerIcon(server.icon)}
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-3">
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white">{server.title}</h2>
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-indigo-500/10 text-indigo-500 dark:text-indigo-400 border border-indigo-500/20">
                              {server.name}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              {server.status}
                            </span>
                          </div>
                          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-3xl leading-relaxed">
                            {server.description}
                          </p>
                          <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-slate-400">
                            <span>Category: <strong className="text-slate-700 dark:text-slate-300">{server.category}</strong></span>
                            <span>•</span>
                            <span>Transport: <strong className="text-slate-700 dark:text-slate-300">{server.transport} ({server.protocol})</strong></span>
                            <span>•</span>
                            <span>Tools: <strong className="text-indigo-600 dark:text-indigo-400">{server.tools_count} schemas</strong></span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-end md:self-center">
                        <button
                          onClick={() => handleCopy(server.command, server.id)}
                          title="Copy stdio run command"
                          className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono flex items-center gap-1.5 transition"
                        >
                          {copiedCommand === server.id ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-500" /> Copied
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" /> Copy stdio CMD
                            </>
                          )}
                        </button>
                        <button
                          onClick={() => setExpandedServerId(isExpanded ? null : server.id)}
                          className="px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 text-xs font-semibold flex items-center gap-1.5 transition"
                        >
                          {isExpanded ? (
                            <>
                              Hide Tools <ChevronUp className="w-3.5 h-3.5" />
                            </>
                          ) : (
                            <>
                              View {server.tools_count} Tools <ChevronDown className="w-3.5 h-3.5" />
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Tools Accordion Body */}
                    {isExpanded && (
                      <div className="p-6 bg-slate-50/50 dark:bg-slate-950/40 space-y-4">
                        <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          <span>Exposed Read-Only Tool Interfaces</span>
                          <span className="text-[11px] font-normal text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                            <ShieldCheck className="w-3.5 h-3.5" /> Zero Mutation Guarantee
                          </span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {server.tools.map((tool) => (
                            <div
                              key={tool.name}
                              className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col justify-between gap-3 shadow-xs hover:border-indigo-400 dark:hover:border-indigo-500/50 transition group"
                            >
                              <div className="space-y-1.5">
                                <div className="flex items-center justify-between">
                                  <div className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400 group-hover:underline flex items-center gap-1.5">
                                    <Code2 className="w-3.5 h-3.5" />
                                    {tool.name}
                                  </div>
                                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                                    Read-Only
                                  </span>
                                </div>
                                <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed">
                                  {tool.description}
                                </p>
                              </div>

                              {/* Parameters pill list */}
                              {tool.input_schema?.properties && Object.keys(tool.input_schema.properties).length > 0 && (
                                <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center gap-1.5">
                                  <span className="text-[10px] text-slate-400">Params:</span>
                                  {Object.entries(tool.input_schema.properties).map(([pName, pVal]) => (
                                    <span
                                      key={pName}
                                      className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                                      title={pVal.description}
                                    >
                                      {pName}: <span className="text-indigo-500">{pVal.type || 'any'}</span>
                                    </span>
                                  ))}
                                </div>
                              )}

                              <div className="pt-1 flex items-center justify-between">
                                <span className="text-[10px] font-mono text-slate-400">stdio JSON-RPC</span>
                                <button
                                  onClick={() => openToolTester(server, tool)}
                                  className="px-3 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-600 dark:bg-indigo-950/60 dark:hover:bg-indigo-600 text-indigo-600 hover:text-white dark:text-indigo-300 dark:hover:text-white text-xs font-medium flex items-center gap-1.5 transition"
                                >
                                  <Play className="w-3 h-3" /> Test Tool
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: AGENT FLOW & LIVE SIMULATION                                       */}
      {/* ========================================================================= */}
      {activeTab === 'simulation' && (
        <div className="space-y-6">
          {/* Visual Architecture Diagram */}
          <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <GitPullRequest className="w-5 h-5 text-indigo-500" />
                  Forensic Agent Swarm MCP Orchestration Flow
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  How autonomous AML agents query all 4 sandboxed MCP servers to reconstruct multi-hop forensic chains.
                </p>
              </div>
              <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 text-xs font-semibold flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 animate-pulse" /> Live Swarm Architecture
              </div>
            </div>

            {/* Architecture Flowchart */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 pt-4">
              <div className="p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 text-center space-y-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center mx-auto text-xs font-bold">1</div>
                <div className="text-xs font-bold text-indigo-900 dark:text-indigo-200">Ledger Intelligence</div>
                <div className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400">transaction_server</div>
                <p className="text-[10px] text-slate-500 leading-tight">Queries account facts, velocity, balances, and counterparties.</p>
              </div>

              <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 text-center space-y-2">
                <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center mx-auto text-xs font-bold">2</div>
                <div className="text-xs font-bold text-blue-900 dark:text-blue-200">Graph Topology</div>
                <div className="text-[11px] font-mono text-blue-600 dark:text-blue-400">graph_server (Neo4j)</div>
                <p className="text-[10px] text-slate-500 leading-tight">Discovers shared device fingerprints, IP collisions & fraud rings.</p>
              </div>

              <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-center space-y-2">
                <div className="w-8 h-8 rounded-lg bg-amber-600 text-white flex items-center justify-center mx-auto text-xs font-bold">3</div>
                <div className="text-xs font-bold text-amber-900 dark:text-amber-200">Anomaly Scoring</div>
                <div className="text-[11px] font-mono text-amber-600 dark:text-amber-400">risk_server</div>
                <p className="text-[10px] text-slate-500 leading-tight">Calculates composite risk score & evaluates statistical anomaly flags.</p>
              </div>

              <div className="p-4 rounded-xl bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800 text-center space-y-2">
                <div className="w-8 h-8 rounded-lg bg-purple-600 text-white flex items-center justify-center mx-auto text-xs font-bold">4</div>
                <div className="text-xs font-bold text-purple-900 dark:text-purple-200">Regulatory Corpus</div>
                <div className="text-[11px] font-mono text-purple-600 dark:text-purple-400">knowledge_server</div>
                <p className="text-[10px] text-slate-500 leading-tight">Grounds evidence against FATF typologies and FinCEN SAR rules.</p>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-center space-y-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center mx-auto text-xs font-bold">5</div>
                <div className="text-xs font-bold text-emerald-900 dark:text-emerald-200">Consensus Verdict</div>
                <div className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400">SAR Recommendation</div>
                <p className="text-[10px] text-slate-500 leading-tight">Synthesizes evidence chain into SAR draft and freeze recommendation.</p>
              </div>
            </div>
          </div>

          {/* Interactive Trigger Panel */}
          <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-5">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-500" />
              Live Interactive Agent Investigation Simulation
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">
                  Target Account ID
                </label>
                <input
                  type="text"
                  value={simAccount}
                  onChange={(e) => setSimAccount(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-white font-mono focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  placeholder="e.g. ACC-1001"
                />
                <div className="flex gap-2 mt-2">
                  {['ACC-1001', 'ACC-1002', 'ACC-1003'].map((acc) => (
                    <button
                      key={acc}
                      onClick={() => setSimAccount(acc)}
                      className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950 text-slate-600 dark:text-slate-400"
                    >
                      {acc}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">
                  Investigation Scenario
                </label>
                <select
                  value={simScenario}
                  onChange={(e) => setSimScenario(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  <option value="MULE_SYNDICATE_STRUCTURING">Mule Syndicate & Structuring</option>
                  <option value="RAPID_DISPERSAL">Rapid Fund Layering & Dispersal</option>
                  <option value="SHARED_DEVICE_COLLUSION">Shared Hardware Fingerprint Collusion</option>
                </select>
              </div>

              <div className="flex items-end">
                <button
                  onClick={runSimulation}
                  disabled={simLoading}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2 transition disabled:opacity-50"
                >
                  {simLoading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" /> Orchestrating 4 MCP Servers...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-current" /> Dispatch Swarm Investigation
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Simulation Results Display */}
            {simResult && (
              <div className="pt-6 border-t border-slate-200 dark:border-slate-800 space-y-6">
                {/* Consensus Verdict Card */}
                <div className="p-5 rounded-2xl bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-white border border-indigo-900/50 shadow-xl space-y-4">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="text-[11px] uppercase tracking-wider text-indigo-300 font-semibold flex items-center gap-2">
                        <FileCheck2 className="w-4 h-4 text-emerald-400" />
                        Autonomous Multi-Agent Consensus Decision
                      </div>
                      <h3 className="text-xl font-bold text-white flex items-center gap-3">
                        Verdict:
                        <span className="px-3 py-1 rounded-full text-xs font-black bg-red-500 text-white tracking-wide animate-pulse">
                          {simResult.consensus_verdict?.verdict}
                        </span>
                        <span className="text-xs font-normal text-slate-300">
                          (Confidence: {Math.round((simResult.consensus_verdict?.confidence || 0) * 100)}%)
                        </span>
                      </h3>
                    </div>

                    <div className="flex items-center gap-2">
                      <a
                        href={simResult.langfuse_trace_url || 'http://localhost:3000'}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3.5 py-1.5 rounded-xl bg-purple-600/30 hover:bg-purple-600/50 border border-purple-500/50 text-purple-200 text-xs font-semibold flex items-center gap-1.5 transition"
                      >
                        <Activity className="w-3.5 h-3.5" /> View Distributed Trace in Langfuse ↗
                      </a>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed bg-white/5 p-3 rounded-xl border border-white/10">
                    <strong>Action:</strong> {simResult.consensus_verdict?.recommended_action}
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-1">
                    <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-400 text-[10px] block">Investigation Time</span>
                      <strong className="text-indigo-400 font-mono">{simResult.total_duration_ms} ms</strong>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-400 text-[10px] block">Typology Grounding</span>
                      <strong className="text-purple-300 truncate block">{simResult.consensus_verdict?.typology_reference}</strong>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-400 text-[10px] block">Security Invariant</span>
                      <strong className="text-emerald-400 text-[11px] block">{simResult.consensus_verdict?.zero_write_adherence}</strong>
                    </div>
                  </div>
                </div>

                {/* Step-by-Step Tool Trace */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                    Sequential MCP Tool Call Trace ({simResult.steps?.length} Invocations)
                  </h4>

                  <div className="space-y-3">
                    {simResult.steps?.map((step: any) => {
                      const isStepExpanded = simExpandedStep === step.step;
                      return (
                        <div
                          key={step.step}
                          className="rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 overflow-hidden"
                        >
                          <div
                            onClick={() => setSimExpandedStep(isStepExpanded ? null : step.step)}
                            className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                          >
                            <div className="flex items-center gap-3">
                              <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
                                {step.step}
                              </span>
                              <div>
                                <div className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                  <span>{step.agent}</span>
                                  <ArrowRight className="w-3 h-3 text-slate-400" />
                                  <span className="font-mono text-indigo-600 dark:text-indigo-400 font-semibold">
                                    {step.tool_name}()
                                  </span>
                                </div>
                                <div className="text-[11px] text-slate-500 dark:text-slate-400">{step.finding}</div>
                              </div>
                            </div>

                            <div className="flex items-center gap-3 self-end sm:self-center">
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-300">
                                {step.server_id}
                              </span>
                              <span className="text-[11px] font-mono text-slate-400 font-semibold">{step.duration_ms} ms</span>
                              {isStepExpanded ? (
                                <ChevronUp className="w-4 h-4 text-slate-400" />
                              ) : (
                                <ChevronDown className="w-4 h-4 text-slate-400" />
                              )}
                            </div>
                          </div>

                          {isStepExpanded && (
                            <div className="p-4 bg-slate-100 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                              <div>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                                  Tool Input Arguments
                                </span>
                                <pre className="p-3 rounded-lg bg-slate-900 text-emerald-300 font-mono text-[11px] overflow-x-auto">
                                  {JSON.stringify(step.arguments, null, 2)}
                                </pre>
                              </div>
                              <div>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                                  MCP Server Structured Output
                                </span>
                                <pre className="p-3 rounded-lg bg-slate-900 text-blue-300 font-mono text-[11px] overflow-x-auto max-h-48">
                                  {JSON.stringify(step.output, null, 2)}
                                </pre>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: LIVE AUDIT LOG & OBSERVABILITY                                     */}
      {/* ========================================================================= */}
      {activeTab === 'audit' && (
        <div className="space-y-6">
          {/* Observability Banner */}
          <div className="p-6 rounded-2xl bg-gradient-to-r from-purple-950 via-indigo-950 to-slate-950 border border-purple-900/50 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-purple-300 text-xs font-semibold uppercase tracking-wider">
                <Activity className="w-4 h-4" /> Dual-Tier Observability Architecture
              </div>
              <h2 className="text-xl font-bold text-white">Full-Stack Agent & Tool Telemetry</h2>
              <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                Every MCP call in Omerta is audited at two layers:
                <br />
                1. <strong>In-App Forensic Audit Log:</strong> Real-time zero-write validation, latency, and arguments.
                <br />
                2. <strong>Langfuse Distributed Tracing:</strong> Full LLM reasoning trees, token costs, spans, and step latencies on{' '}
                <code className="text-indigo-300">http://localhost:3000</code>.
              </p>
            </div>
            <a
              href="http://localhost:3000"
              target="_blank"
              rel="noreferrer"
              className="px-5 py-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold shadow-lg shadow-purple-500/25 flex items-center gap-2 flex-shrink-0 transition"
            >
              Open Langfuse Dashboard ↗
            </a>
          </div>

          {/* Audit Feed Table */}
          <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Clock className="w-4 h-4 text-indigo-500" />
                  Real-Time MCP Tool Execution Log ({auditLogs.length} events)
                </h3>
                <p className="text-xs text-slate-400">Chronological feed of tool executions triggered by agents or direct test suites.</p>
              </div>

              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRefreshAudit}
                    onChange={(e) => setAutoRefreshAudit(e.target.checked)}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Auto-Refresh (3s)</span>
                </label>
                <button
                  onClick={fetchAuditLogs}
                  disabled={auditLoading}
                  className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-medium flex items-center gap-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${auditLoading ? 'animate-spin' : ''}`} /> Refresh
                </button>
              </div>
            </div>

            {auditLogs.length === 0 ? (
              <div className="py-16 text-center text-xs text-slate-400">
                No tool invocations recorded yet. Run a tool test or simulation to generate events.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 font-semibold">
                    <tr>
                      <th className="p-3 rounded-l-lg">Time</th>
                      <th className="p-3">Caller</th>
                      <th className="p-3">Server</th>
                      <th className="p-3">Tool Name</th>
                      <th className="p-3">Arguments</th>
                      <th className="p-3">Latency</th>
                      <th className="p-3 rounded-r-lg">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="p-3 font-mono text-[11px] text-slate-400">
                          {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Just now'}
                        </td>
                        <td className="p-3 font-medium text-slate-700 dark:text-slate-300">{log.caller}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400">
                            {log.server_id}
                          </span>
                        </td>
                        <td className="p-3 font-mono font-semibold text-slate-900 dark:text-white">
                          {log.tool_name}()
                        </td>
                        <td className="p-3 font-mono text-[11px] text-slate-500 max-w-xs truncate" title={JSON.stringify(log.arguments)}>
                          {JSON.stringify(log.arguments)}
                        </td>
                        <td className="p-3 font-mono text-indigo-500 font-semibold">{log.duration_ms} ms</td>
                        <td className="p-3">
                          {log.success ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                              SUCCESS
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-500/10 text-red-500 border border-red-500/20">
                              FAILED
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: DIRECT MCP TOOL TEST RUNNER                                        */}
      {/* ========================================================================= */}
      {activeTestServer && activeTestTool && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-2xl w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400">
                  <Terminal className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    Test Tool: <span className="font-mono text-indigo-600 dark:text-indigo-400">{activeTestTool.name}()</span>
                  </h2>
                  <p className="text-xs text-slate-500">{activeTestServer.title}</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setActiveTestServer(null);
                  setActiveTestTool(null);
                }}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-5 overflow-y-auto space-y-4">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                  Description
                </span>
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  {activeTestTool.description}
                </p>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
                  JSON Arguments (Validated via Pydantic Strict Schema)
                </label>
                <textarea
                  rows={5}
                  value={testArguments}
                  onChange={(e) => setTestArguments(e.target.value)}
                  className="w-full p-3 rounded-xl bg-slate-950 font-mono text-xs text-emerald-300 border border-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* Execution Result Box */}
              {testResult && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-500 uppercase tracking-wider">
                      Execution Output
                    </span>
                    <span
                      className={`font-semibold ${
                        testResult.success ? 'text-emerald-500' : 'text-red-500'
                      }`}
                    >
                      {testResult.success ? `SUCCESS (${testResult.duration_ms} ms)` : 'ERROR'}
                    </span>
                  </div>
                  <pre className="p-4 rounded-xl bg-slate-950 text-blue-300 font-mono text-xs overflow-x-auto max-h-60 border border-slate-800">
                    {JSON.stringify(testResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <span className="text-[11px] text-emerald-500 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" /> Read-Only Execution Guaranteed
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setActiveTestServer(null);
                    setActiveTestTool(null);
                  }}
                  className="px-4 py-2 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold text-xs"
                >
                  Close
                </button>
                <button
                  onClick={executeToolTest}
                  disabled={testLoading}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-indigo-500/20 disabled:opacity-50"
                >
                  {testLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Executing...
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" /> Execute Read-Only Call
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
