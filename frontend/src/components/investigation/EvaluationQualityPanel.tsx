import React, { useState } from 'react';
import {
  Scale,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Info,
  Clock,
  Cpu,
  Layers,
  HelpCircle,
  ExternalLink,
} from 'lucide-react';
import type { InvestigationEvaluationResult } from '../../api/client';
import { api } from '../../api/client';
import { Button } from '../ui/Button';

interface EvaluationQualityPanelProps {
  investigationId: string;
  initialEvaluation?: InvestigationEvaluationResult | null;
  reportData?: any;
  evidenceData?: any[];
  contextData?: any;
}

export const EvaluationQualityPanel: React.FC<EvaluationQualityPanelProps> = ({
  investigationId,
  initialEvaluation,
  reportData,
  evidenceData = [],
  contextData = {},
}) => {
  const [evaluation, setEvaluation] = useState<InvestigationEvaluationResult | null>(
    initialEvaluation || null
  );
  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);

  const handleRunEvaluation = async () => {
    if (!reportData) return;
    setEvaluating(true);
    setEvalError(null);
    try {
      const res = await api.evaluateInvestigationReport({
        investigation_id: investigationId,
        report: reportData,
        evidence: evidenceData,
        context: contextData,
        force_run: true,
      });
      setEvaluation(res);
    } catch (err: any) {
      setEvalError(err?.message || 'Evaluation request failed.');
    } finally {
      setEvaluating(false);
    }
  };

  const getScoreColor = (score: number | null | undefined) => {
    if (score == null) return 'text-slate-400 bg-slate-800/60 border-slate-700';
    if (score >= 4) return 'text-emerald-400 bg-emerald-950/40 border-emerald-800/60';
    if (score === 3) return 'text-amber-400 bg-amber-950/40 border-amber-800/60';
    return 'text-rose-400 bg-rose-950/40 border-rose-800/60';
  };

  const getScoreBarWidth = (score: number | null | undefined) => {
    if (score == null) return '0%';
    return `${(score / 5) * 100}%`;
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-xl border border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-lg bg-indigo-950/60 border border-indigo-800/50 text-indigo-400">
            <Scale className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-slate-100">
                LLM-as-a-Judge Evaluation & Quality Assurance
              </h3>
              <span className="text-xs px-2 py-0.5 rounded font-mono bg-indigo-950 border border-indigo-800 text-indigo-300">
                v{evaluation?.evaluation_version || '1.0'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Multi-dimensional evaluation assessing evidence grounding, reasoning logic, and deterministic integrity.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {(evaluation?.trace_url || evaluation?.trace_id) && (
            <a
              href={evaluation.trace_url || `http://localhost:3000/trace/${evaluation.trace_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-emerald-950/70 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-700/70 transition-all shadow-sm"
              title="Open full trace, spans, and scores in Langfuse Dashboard"
            >
              <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />
              <span>View in Langfuse ↗</span>
            </a>
          )}

          <Button
            onClick={handleRunEvaluation}
            disabled={evaluating || !reportData}
            variant="secondary"
            className="flex items-center gap-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border-indigo-700/50"
          >
            <RefreshCw className={`w-4 h-4 ${evaluating ? 'animate-spin' : ''}`} />
            {evaluating ? 'Evaluating with Judge...' : evaluation ? 'Re-Evaluate Report' : 'Run Judge Evaluation'}
          </Button>
        </div>
      </div>

      {evaluation && (
        <div className="p-3.5 rounded-xl border border-emerald-800/40 bg-emerald-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-emerald-300 font-semibold">Langfuse Observability Live:</span>
            <span className="text-slate-300">
              Evaluation scores & deterministic gates attached to investigation trace.
            </span>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {evaluation.trace_id && (
              <div className="flex items-center gap-1.5 text-slate-400 font-mono text-[11px] bg-slate-900/90 px-2 py-1 rounded border border-slate-800">
                <span className="text-slate-500">Trace:</span>
                <span className="text-slate-300 truncate max-w-[150px]" title={evaluation.trace_id}>
                  {evaluation.trace_id}
                </span>
              </div>
            )}
            {(evaluation.trace_url || evaluation.trace_id) && (
              <a
                href={evaluation.trace_url || `http://localhost:3000/trace/${evaluation.trace_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 font-medium hover:underline text-xs"
              >
                <span>Open Dashboard</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>
      )}

      {evalError && (
        <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>Evaluation Error: {evalError}</span>
        </div>
      )}

      {!evaluation && !evaluating && (
        <div className="text-center py-12 px-4 rounded-xl border border-dashed border-slate-800 bg-slate-900/40">
          <Sparkles className="w-8 h-8 text-indigo-400 mx-auto mb-3 opacity-60" />
          <h4 className="text-sm font-medium text-slate-300">No Evaluation Score Recorded Yet</h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
            Execute the LLM-as-a-Judge to evaluate evidence grounding, detect unsupported claims or hallucinated identifiers, and publish scores to Langfuse.
          </p>
          <Button onClick={handleRunEvaluation} disabled={!reportData} className="text-xs">
            Evaluate Now
          </Button>
        </div>
      )}

      {evaluation && (
        <>
          {/* Key Metric Highlights */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Overall Score */}
            <div className={`p-4 rounded-xl border ${getScoreColor(evaluation.scores.overall_quality)}`}>
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-wider font-semibold opacity-80">Overall Quality</span>
                <Sparkles className="w-4 h-4 opacity-70" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold font-mono">
                  {evaluation.scores.overall_quality ?? 'N/A'}
                </span>
                <span className="text-xs text-slate-400 font-mono">/ 5.0</span>
              </div>
              <p className="text-[11px] opacity-75 mt-1 truncate">
                {evaluation.dimension_explanations?.overall_quality || 'Holistic investigation score'}
              </p>
            </div>

            {/* Evidence Grounding */}
            <div className={`p-4 rounded-xl border ${getScoreColor(evaluation.scores.evidence_grounding)}`}>
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-wider font-semibold opacity-80">Evidence Grounding</span>
                <Layers className="w-4 h-4 opacity-70" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold font-mono">
                  {evaluation.scores.evidence_grounding ?? 'N/A'}
                </span>
                <span className="text-xs text-slate-400 font-mono">/ 5.0</span>
              </div>
              <p className="text-[11px] opacity-75 mt-1 truncate">
                {evaluation.dimension_explanations?.evidence_grounding || 'Zero hallucinations'}
              </p>
            </div>

            {/* Deterministic Validation */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs uppercase tracking-wider font-semibold">Deterministic Checks</span>
                {evaluation.deterministic_validation?.passed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                )}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span
                  className={`text-sm font-semibold px-2 py-0.5 rounded ${
                    evaluation.deterministic_validation?.passed
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-rose-950 text-rose-300 border border-rose-800'
                  }`}
                >
                  {evaluation.deterministic_validation?.passed ? 'PASSED (0 Discrepancies)' : 'DISCREPANCIES DETECTED'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-2 truncate">
                Verified accounts, amounts, dates & graph links
              </p>
            </div>

            {/* Human Review Gate */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs uppercase tracking-wider font-semibold">Human Review Gate</span>
                {evaluation.human_review_required ? (
                  <ShieldAlert className="w-4 h-4 text-amber-400" />
                ) : (
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                )}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span
                  className={`text-sm font-semibold px-2 py-0.5 rounded ${
                    evaluation.human_review_required
                      ? 'bg-amber-950 text-amber-300 border border-amber-800'
                      : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  }`}
                >
                  {evaluation.human_review_required ? 'ACTION REQUIRED' : 'NO REVIEW TRIGGERS'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-2 truncate">
                {evaluation.review_reasons?.[0] || 'Investigation rigorously grounded'}
              </p>
            </div>
          </div>

          {/* Detailed Dimensions Breakdown */}
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Granular Evaluation Dimensions (1–5 Rubrics)
            </h4>

            <div className="space-y-3.5">
              {[
                {
                  name: 'Evidence Grounding',
                  score: evaluation.scores.evidence_grounding,
                  desc: evaluation.dimension_explanations?.evidence_grounding,
                },
                {
                  name: 'Reasoning Quality',
                  score: evaluation.scores.reasoning_quality,
                  desc: evaluation.dimension_explanations?.reasoning_quality,
                },
                {
                  name: 'Investigation Completeness',
                  score: evaluation.scores.investigation_completeness,
                  desc: evaluation.dimension_explanations?.investigation_completeness,
                },
                {
                  name: 'Report Quality',
                  score: evaluation.scores.report_quality,
                  desc: evaluation.dimension_explanations?.report_quality,
                },
                {
                  name: 'Overall Quality',
                  score: evaluation.scores.overall_quality,
                  desc: evaluation.dimension_explanations?.overall_quality,
                },
              ].map((dim) => (
                <div key={dim.name} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-200">{dim.name}</span>
                    <span className="font-mono font-bold text-slate-300">
                      {dim.score != null ? `${dim.score}/5` : 'N/A'}
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        (dim.score || 0) >= 4
                          ? 'bg-emerald-500'
                          : (dim.score || 0) === 3
                          ? 'bg-amber-500'
                          : 'bg-rose-500'
                      }`}
                      style={{ width: getScoreBarWidth(dim.score) }}
                    />
                  </div>
                  {dim.desc && <p className="text-[11px] text-slate-400 italic">{dim.desc}</p>}
                </div>
              ))}
            </div>
          </div>

          {/* Qualitative Findings: Unsupported Claims & Discrepancies */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Unsupported Claims */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-rose-400 mb-2">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Unsupported Claims ({evaluation.unsupported_claims.length})</span>
              </div>
              {evaluation.unsupported_claims.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No unsupported claims detected by the judge.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-rose-300">
                  {evaluation.unsupported_claims.map((claim, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-rose-500 font-bold">•</span>
                      <span>{claim}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Evidence Gaps */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-400 mb-2">
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Identified Evidence Gaps ({evaluation.evidence_gaps.length})</span>
              </div>
              {evaluation.evidence_gaps.length === 0 ? (
                <p className="text-xs text-slate-500 italic">All required evidence sources were satisfactorily queried.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-amber-300">
                  {evaluation.evidence_gaps.map((gap, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-amber-500 font-bold">•</span>
                      <span>{gap}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Deterministic Discrepancies (if any) */}
          {evaluation.deterministic_validation?.discrepancies &&
            evaluation.deterministic_validation.discrepancies.length > 0 && (
              <div className="p-4 rounded-xl border border-rose-900/80 bg-rose-950/30 text-rose-200">
                <h5 className="text-xs font-semibold uppercase tracking-wider flex items-center gap-2 text-rose-400 mb-2">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Deterministic Contradictions Found</span>
                </h5>
                <ul className="space-y-1 text-xs list-disc list-inside">
                  {evaluation.deterministic_validation.discrepancies.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
            )}

          {/* Judge Metadata & Legal Advisory */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-2 text-[11px] text-slate-500 border-t border-slate-800/80">
            <div className="flex flex-wrap items-center gap-4">
              <span className="flex items-center gap-1 font-mono">
                <Cpu className="w-3 h-3 text-slate-400" />
                {evaluation.judge_metadata?.provider || 'default'} ({evaluation.judge_metadata?.model || 'judge-v1'})
              </span>
              <span className="flex items-center gap-1 font-mono">
                <Clock className="w-3 h-3 text-slate-400" />
                {evaluation.judge_metadata?.latency_ms ?? 0} ms
              </span>
              {(evaluation.trace_url || evaluation.trace_id) && (
                <a
                  href={evaluation.trace_url || `http://localhost:3000/trace/${evaluation.trace_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 font-mono"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span>Langfuse Trace</span>
                </a>
              )}
            </div>
            <p className="max-w-xl text-slate-400 italic leading-snug">
              {evaluation.disclaimer}
            </p>
          </div>
        </>
      )}
    </div>
  );
};

