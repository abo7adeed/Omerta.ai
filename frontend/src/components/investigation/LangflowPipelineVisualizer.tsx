import React, { useState } from 'react';
import {
  Sparkles,
  GitPullRequest,
  Check,
  Copy,
  Terminal,
  Code2,
  ArrowRight,
  ShieldCheck,
  UserCheck,
  RefreshCw,
  Scale,
  ShieldAlert,
  FileCheck2,
  ExternalLink,
  Play,
} from 'lucide-react';

interface LangflowPipelineVisualizerProps {
  onTestTool?: () => void;
}

export const LangflowPipelineVisualizer: React.FC<LangflowPipelineVisualizerProps> = ({
  onTestTool,
}) => {
  const [selectedNode, setSelectedNode] = useState<string>('node_mcp_tool');
  const [copied, setCopied] = useState(false);

  const handleCopyCmd = () => {
    navigator.clipboard.writeText('pip install langflow; langflow run --port 7860');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const nodes = [
    {
      id: 'node_input_entity',
      title: '1. Entity Input',
      desc: 'Ingests name, type, country, DOB & ID',
      icon: <UserCheck className="w-5 h-5 text-blue-500" />,
      python: 'apps.api.v1.sanctions.EntityScreeningRequest',
      role: 'Participant Ingestion',
    },
    {
      id: 'node_normalize',
      title: '2. Normalizer',
      desc: 'Tashkeel stripping & transliteration',
      icon: <RefreshCw className="w-5 h-5 text-amber-500" />,
      python: 'domain.services.entity_resolution_service.normalize_name',
      role: 'Bilingual Script Normalization',
    },
    {
      id: 'node_mcp_tool',
      title: '3. MCP Screening',
      desc: 'omerta-sanctions-server JSON-RPC',
      icon: <ShieldCheck className="w-5 h-5 text-sky-500" />,
      python: 'mcp_servers.sanctions_server.tools.screen_entity_against_watchlists',
      role: 'Sandboxed Read-Only Execution',
    },
    {
      id: 'node_scoring',
      title: '4. Scoring & Ranker',
      desc: 'Multi-signal weights (Name, DOB, ID)',
      icon: <Scale className="w-5 h-5 text-purple-500" />,
      python: 'domain.services.entity_resolution_service.EntityResolutionService',
      role: 'Deterministic Score Fusion',
    },
    {
      id: 'node_explainability',
      title: '5. HITL Advisor',
      desc: 'Enforces human review & factor audit',
      icon: <ShieldAlert className="w-5 h-5 text-red-500" />,
      python: 'EntityResolutionService.score_candidate',
      role: 'Human-in-the-Loop Mandate',
    },
    {
      id: 'node_output',
      title: '6. Audit Report',
      desc: 'Structured JSON response & provenance',
      icon: <FileCheck2 className="w-5 h-5 text-emerald-500" />,
      python: 'apps.api.v1.sanctions.EntityScreeningResponse',
      role: 'Audit-Grade Evidence Output',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-indigo-900/50 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-4 h-4" /> Visual AI Orchestration
          </div>
          <h2 className="text-xl font-bold text-white">Langflow Visual Workflow Pipeline</h2>
          <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
            Omerta.ai encapsulates sanctions screening as an executable visual DAG in{' '}
            <code className="text-amber-300 bg-white/10 px-1.5 py-0.5 rounded font-mono">
              langflow/sanctions_screening_flow.json
            </code>
            . Each node executes an atomic step from bilingual name normalization to MCP tool invocation and explainability generation.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-2.5 shrink-0">
          <button
            onClick={handleCopyCmd}
            className="px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white text-xs font-mono flex items-center gap-2 transition"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" /> Copied Command
              </>
            ) : (
              <>
                <Terminal className="w-3.5 h-3.5 text-amber-400" /> langflow run --port 7860
              </>
            )}
          </button>
        </div>
      </div>

      {/* Visual DAG Nodes Pipeline */}
      <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <GitPullRequest className="w-4 h-4 text-indigo-500" />
              6-Stage Visual Workflow Pipeline (Directed Acyclic Graph)
            </h3>
            <p className="text-xs text-slate-400">
              Click any stage node to inspect its runtime contract, parameter bindings, and Python implementation.
            </p>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
            DAG Flow: Validated
          </span>
        </div>

        {/* Interactive Node Flow Chart */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
          {nodes.map((n) => {
            const isSelected = selectedNode === n.id;
            return (
              <button
                key={n.id}
                type="button"
                onClick={() => setSelectedNode(n.id)}
                className={`p-4 rounded-xl border text-left transition-all relative flex flex-col justify-between gap-3 ${
                  isSelected
                    ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/40 shadow-md ring-2 ring-indigo-500/20'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
                    {n.icon}
                  </div>
                  <span className="text-[10px] font-mono font-bold text-slate-400">
                    {n.id.replace('node_', '')}
                  </span>
                </div>

                <div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white">{n.title}</h4>
                  <p className="text-[11px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                    {n.desc}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 text-[10px] text-indigo-500 font-semibold flex items-center justify-between">
                  <span>{isSelected ? 'Viewing' : 'Inspect'}</span>
                  <ArrowRight className="w-3 h-3" />
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Node Details Inspector */}
        <div className="p-5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-indigo-600 text-white">
                <Code2 className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 dark:text-white font-mono">
                  Node Specification: {selectedNode}
                </h4>
                <p className="text-[11px] text-slate-500">
                  Defined in <code className="text-indigo-500 font-mono">langflow/sanctions_screening_flow.json</code>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {selectedNode === 'node_mcp_tool' && onTestTool && (
                <button
                  onClick={onTestTool}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition"
                >
                  <Play className="w-3 h-3" /> Test in MCP Runner
                </button>
              )}
            </div>
          </div>

          {/* Inspector Content Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-3">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                  Underlying Python Implementation
                </span>
                <pre className="p-2.5 rounded-lg bg-slate-900 text-emerald-400 font-mono text-[11px] overflow-x-auto">
                  {selectedNode === 'node_input_entity'
                    ? 'apps.api.v1.sanctions.EntityScreeningRequest'
                    : selectedNode === 'node_normalize'
                    ? 'domain.services.entity_resolution_service.normalize_name'
                    : selectedNode === 'node_mcp_tool'
                    ? 'mcp_servers.sanctions_server.tools.screen_entity_against_watchlists'
                    : selectedNode === 'node_scoring'
                    ? 'domain.services.entity_resolution_service.EntityResolutionService'
                    : selectedNode === 'node_explainability'
                    ? 'EntityResolutionService.score_candidate'
                    : 'apps.api.v1.sanctions.EntityScreeningResponse'}
                </pre>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                  Node Responsibility &amp; Compliance Invariant
                </span>
                <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-[11px]">
                  {selectedNode === 'node_input_entity'
                    ? 'Validates input payload fields (legal name, nationality, date of birth, and identity numbers). Rejects injection attempts before processing.'
                    : selectedNode === 'node_normalize'
                    ? 'Executes bilingual Arabic/English script cleaning: strips Tashkeel diacritics, unifies Hamza/Alif variants, detaches prefixes (Al-, El-, Abdel-), and maps transliteration clusters.'
                    : selectedNode === 'node_mcp_tool'
                    ? 'Executes sandboxed read-only query over OpenSanctions FollowTheMoney dataset. Bound by specialist RBAC and fail-closed authentication.'
                    : selectedNode === 'node_scoring'
                    ? 'Combines Jaro-Winkler, Token Sort, and substring similarities with DOB and country concordance. Applies conflict penalties for mismatched birth years or jurisdictions.'
                    : selectedNode === 'node_explainability'
                    ? 'Guarantees Human-in-the-Loop compliance. Flags review_required=True and formulates auditable factor explanations. Automated freezing is strictly prohibited.'
                    : 'Serializes the final screening report with cryptographic execution metadata, source provenance, and audit trail for compliance records.'}
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                  Runtime Parameters &amp; Thresholds
                </span>
                <div className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5 font-mono text-[11px]">
                  {selectedNode === 'node_mcp_tool' ? (
                    <>
                      <div>server_id: <span className="text-indigo-500">"sanctions_server"</span></div>
                      <div>tool_name: <span className="text-indigo-500">"screen_entity_against_watchlists"</span></div>
                      <div>specialist: <span className="text-emerald-500">"SanctionsScreeningAgent"</span></div>
                      <div>read_only: <span className="text-emerald-500">true</span></div>
                    </>
                  ) : selectedNode === 'node_scoring' ? (
                    <>
                      <div>name_weight: <span className="text-indigo-500">0.50</span></div>
                      <div>dob_weight: <span className="text-indigo-500">0.25</span></div>
                      <div>country_weight: <span className="text-indigo-500">0.15</span></div>
                      <div>id_weight: <span className="text-indigo-500">0.10</span></div>
                      <div>threshold: <span className="text-amber-500">0.70</span></div>
                    </>
                  ) : selectedNode === 'node_explainability' ? (
                    <>
                      <div>enforce_hitl: <span className="text-red-500">true</span></div>
                      <div>advisory_only: <span className="text-emerald-500">true</span></div>
                      <div>allow_auto_freeze: <span className="text-red-500">false</span></div>
                    </>
                  ) : (
                    <>
                      <div>protocol: <span className="text-indigo-500">"JSON-RPC 2.0"</span></div>
                      <div>schema: <span className="text-indigo-500">"FollowTheMoney / Pydantic"</span></div>
                      <div>status: <span className="text-emerald-500">"ACTIVE"</span></div>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

