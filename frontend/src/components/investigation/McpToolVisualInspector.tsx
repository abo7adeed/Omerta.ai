import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Code2,
  Copy,
  Check,
  Sparkles,
  Info,
} from 'lucide-react';

interface McpToolVisualInspectorProps {
  toolName: string;
  testResult: {
    success: boolean;
    duration_ms: number;
    result: any;
    arguments?: Record<string, any>;
  };
}

export const McpToolVisualInspector: React.FC<McpToolVisualInspectorProps> = ({
  toolName,
  testResult,
}) => {
  const [viewMode, setViewMode] = useState<'visual' | 'json'>('visual');
  const [copied, setCopied] = useState(false);

  const payload = testResult.result;
  const isSanctionsTool =
    toolName === 'screen_entity_against_watchlists' ||
    Boolean(payload?.matched_entities || payload?.match_found !== undefined);

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(testResult, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-3 text-xs">
      {/* View Switcher Header */}
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-500 uppercase tracking-wider text-[11px]">
            Execution Result
          </span>
          {isSanctionsTool && (
            <div className="flex items-center bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5">
              <button
                type="button"
                onClick={() => setViewMode('visual')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition ${
                  viewMode === 'visual'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                Visual Inspector
              </button>
              <button
                type="button"
                onClick={() => setViewMode('json')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition ${
                  viewMode === 'json'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                Raw JSON
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopyJson}
            className="px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-600 dark:text-slate-400 text-[10px] font-mono flex items-center gap-1 transition"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy Output'}
          </button>
          <span
            className={`font-semibold text-[11px] ${
              testResult.success ? 'text-emerald-500' : 'text-red-500'
            }`}
          >
            {testResult.success ? `SUCCESS (${testResult.duration_ms} ms)` : 'ERROR'}
          </span>
        </div>
      </div>

      {/* Visual Inspector Body */}
      {viewMode === 'visual' && isSanctionsTool && payload ? (
        <div className="space-y-3.5 max-h-[380px] overflow-y-auto pr-1">
          {/* Top Outcome Summary Bar */}
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">
                Decision Recommendation
              </span>
              <div className="flex items-center gap-2 mt-0.5">
                <span
                  className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase ${
                    (payload.best_match_confidence || 0) >= 0.85
                      ? 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20'
                      : (payload.best_match_confidence || 0) >= 0.65
                      ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20'
                      : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                  }`}
                >
                  {payload.match_found
                    ? (payload.best_match_confidence || 0) >= 0.85
                      ? 'POTENTIAL_MATCH'
                      : 'NEEDS_HUMAN_REVIEW'
                    : 'NO_MATCH'}
                </span>
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                  Confidence: {Math.round((payload.best_match_confidence || 0) * 100)}%
                </span>
              </div>
            </div>

            <div className="text-right text-[11px] text-slate-500">
              <div>
                Source: <strong className="text-indigo-500">{payload.execution_metadata?.source_queried || 'LOCAL_BASELINE'}</strong>
              </div>
              <div>
                Analyzed: <strong>{payload.total_candidates_analyzed || 0} entities</strong>
              </div>
            </div>
          </div>

          {/* Mandatory Human-in-the-Loop Regulatory Notice */}
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-[11px] text-amber-700 dark:text-amber-400 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>
              <strong>Human Review Mandatory:</strong> Screening results are strictly advisory. In accordance with international AML compliance standards, automated freezing of accounts or confirmation of sanctions is strictly prohibited without Compliance Officer adjudication.
            </span>
          </div>

          {/* Matched Entities List */}
          {payload.matched_entities && payload.matched_entities.length > 0 ? (
            <div className="space-y-3">
              {payload.matched_entities.map((cand: any, idx: number) => {
                const confPercent = Math.round(cand.confidence_score * 100);
                const isHigh = confPercent >= 85;

                return (
                  <div
                    key={idx}
                    className={`p-3.5 rounded-xl border transition-all ${
                      isHigh
                        ? 'bg-red-50/20 dark:bg-red-950/10 border-red-300 dark:border-red-900/40'
                        : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800'
                    } space-y-3`}
                  >
                    <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-slate-900 dark:text-white">
                          {cand.caption}
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                          {cand.entity_type || 'Entity'}
                        </span>
                        {cand.entity_id && (
                          <span className="text-[10px] font-mono text-slate-400">
                            ID: {cand.entity_id}
                          </span>
                        )}
                      </div>
                      <span
                        className={`font-mono text-xs font-extrabold ${
                          isHigh ? 'text-red-500' : 'text-amber-500'
                        }`}
                      >
                        {confPercent}% Match
                      </span>
                    </div>

                    {/* Sanctions Program Badges */}
                    {cand.sanctions_details?.sanctions_programs?.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {cand.sanctions_details.sanctions_programs.map((prog: string, pIdx: number) => (
                          <span
                            key={pIdx}
                            className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/10 text-red-600 dark:text-red-400"
                          >
                            {prog}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Factor Breakdown */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                      {cand.matched_fields?.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[10px] uppercase font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Matched Factors
                          </span>
                          {cand.matched_fields.map((mf: string, mIdx: number) => (
                            <div
                              key={mIdx}
                              className="p-1 rounded bg-emerald-500/5 text-emerald-700 dark:text-emerald-300 text-[10px] font-medium"
                            >
                              {mf}
                            </div>
                          ))}
                        </div>
                      )}

                      {cand.conflicting_fields?.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[10px] uppercase font-bold text-red-600 dark:text-red-400 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" /> Conflicting Factors
                          </span>
                          {cand.conflicting_fields.map((cf: string, cIdx: number) => (
                            <div
                              key={cIdx}
                              className="p-1 rounded bg-red-500/5 text-red-700 dark:text-red-300 text-[10px] font-medium"
                            >
                              {cf}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Reasoning Narrative Callout */}
                    <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-[11px] text-slate-700 dark:text-slate-300 leading-relaxed">
                      <span className="font-bold text-slate-900 dark:text-white">Auditable Rationale: </span>
                      {cand.reasoning}
                    </div>

                    {/* Source Citations */}
                    {cand.source_citations?.length > 0 && (
                      <div className="flex items-center gap-2 flex-wrap pt-1">
                        <span className="text-[10px] text-slate-400 font-semibold">Official Citations:</span>
                        {cand.source_citations.map((url: string, uIdx: number) => (
                          <a
                            key={uIdx}
                            href={url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-[10px] text-indigo-500 hover:underline font-mono bg-indigo-50 dark:bg-indigo-950 px-2 py-0.5 rounded"
                          >
                            <span>{url.replace(/^https?:\/\//, '').split('/')[0]}</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-6 text-center bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 space-y-1.5">
              <CheckCircle2 className="w-7 h-7 text-emerald-500 mx-auto" />
              <h5 className="font-bold text-xs text-slate-900 dark:text-white">No Matching Entities Found</h5>
              <p className="text-[11px] text-slate-500">
                Zero entities exceeded the confidence threshold across OpenSanctions and international watchlists.
              </p>
            </div>
          )}
        </div>
      ) : (
        /* Raw JSON Output Block */
        <pre className="p-4 rounded-xl bg-slate-950 text-blue-300 font-mono text-xs overflow-x-auto max-h-64 border border-slate-800">
          {JSON.stringify(testResult, null, 2)}
        </pre>
      )}
    </div>
  );
};

