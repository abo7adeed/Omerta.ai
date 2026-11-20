import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Search,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Info,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { api } from '../../api/client';
import { Button } from '../ui/Button';

interface SanctionsScreeningPanelProps {
  caseId?: string;
  defaultName?: string;
  defaultCountry?: string;
  defaultDob?: string;
  defaultIdNumber?: string;
  onScreenComplete?: (result: any) => void;
}

export const SanctionsScreeningPanel: React.FC<SanctionsScreeningPanelProps> = ({
  caseId,
  defaultName = '',
  defaultCountry = '',
  defaultDob = '',
  defaultIdNumber = '',
  onScreenComplete,
}) => {
  const [name, setName] = useState(defaultName || 'Mohamed El-Sayed Ahmed');
  const [entityType, setEntityType] = useState('individual');
  const [country, setCountry] = useState(defaultCountry || 'EG');
  const [birthDate, setBirthDate] = useState(defaultDob || '1982-05-14');
  const [idNumber, setIdNumber] = useState(defaultIdNumber || 'EG-NAT-28205140102931');
  const [threshold, setThreshold] = useState(0.70);

  const [loading, setLoading] = useState(false);
  const [caseLoading, setCaseLoading] = useState(false);
  const [screeningResult, setScreeningResult] = useState<any | null>(null);
  const [caseResult, setCaseResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleScreenEntity = async () => {
    if (!name.trim()) {
      setError('Please provide an entity name to screen.');
      return;
    }
    setLoading(true);
    setError(null);
    setCaseResult(null);

    try {
      const res = await api.screenEntity({
        name: name.trim(),
        entity_type: entityType,
        countries: country.trim() ? [country.trim().toUpperCase()] : [],
        birth_date: birthDate.trim() || undefined,
        identification_number: idNumber.trim() || undefined,
        threshold,
        limit: 5,
      });
      setScreeningResult(res);
      if (onScreenComplete) onScreenComplete(res);
    } catch (err: any) {
      setError(err?.data?.detail?.detail || err?.message || 'Screening request failed');
    } finally {
      setLoading(false);
    }
  };

  const handleScreenCaseParticipants = async () => {
    if (!caseId) return;
    setCaseLoading(true);
    setError(null);
    setScreeningResult(null);

    try {
      const res = await api.screenInvestigationCase(caseId);
      setCaseResult(res);
      if (onScreenComplete) onScreenComplete(res);
    } catch (err: any) {
      setError(err?.data?.detail?.detail || err?.message || 'Case screening failed');
    } finally {
      setCaseLoading(false);
    }
  };

  return (
    <div className="space-y-6 text-xs text-[#0F172A]">
      {/* Human-in-the-Loop Regulatory Notice */}
      <div className="p-4 bg-[#FFFBEB] border border-[#FDE68A] rounded-xl flex items-start gap-3 shadow-sm">
        <AlertTriangle className="w-5 h-5 text-[#D97706] shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-bold text-[#92400E] text-xs uppercase tracking-wider">
            Human-in-the-Loop Mandatory Compliance Guardrail
          </h4>
          <p className="text-[11px] text-[#B45309] leading-relaxed">
            All screening results are strictly advisory. In accordance with international AML/CTF due process standards,
            potential matches flag <strong>Review Required</strong> and <strong>never</strong> trigger automated account freezing,
            asset blocking, or regulatory SAR submissions without affirmative Compliance Officer sign-off.
          </p>
        </div>
      </div>

      {/* Screening Search Configuration Card */}
      <div className="p-5 bg-white rounded-xl border border-[#CBD5E1] shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#F1F5F9] pb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#002D72]/10 flex items-center justify-center text-[#002D72]">
              <Sparkles className="w-4 h-4 text-[#002D72]" />
            </div>
            <div>
              <h4 className="font-bold text-[#002D72] text-sm">
                Sanctions &amp; Watchlist Multi-Signal Screening
              </h4>
              <p className="text-[11px] text-[#64748B]">
                Powered by OpenSanctions, OFAC SDN, UN Security Council, and EU Restrictive Measures
              </p>
            </div>
          </div>

          {caseId && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleScreenCaseParticipants}
              disabled={caseLoading}
              className="border-[#002D72] text-[#002D72] hover:bg-[#002D72]/5 shrink-0 flex items-center gap-1.5"
            >
              {caseLoading ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <ShieldCheck className="w-3.5 h-3.5" />
              )}
              Screen Case Participants ({caseId})
            </Button>
          )}
        </div>

        {/* Input Parameters Form */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div>
            <label className="block text-[11px] font-semibold text-[#475569] mb-1">
              Legal Name / Alias <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Mohamed El-Sayed Ahmed or محمد السيد"
              className="w-full px-3 py-2 border border-[#CBD5E1] rounded-lg text-xs bg-[#F8FAFC] focus:bg-white focus:border-[#002D72] outline-none"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-[#475569] mb-1">
              Entity Type
            </label>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="w-full px-3 py-2 border border-[#CBD5E1] rounded-lg text-xs bg-[#F8FAFC] focus:bg-white focus:border-[#002D72] outline-none cursor-pointer"
            >
              <option value="individual">Individual (Person)</option>
              <option value="company">Company / Corporation</option>
              <option value="organization">Organization / Network</option>
              <option value="vessel">Vessel (Ship)</option>
              <option value="aircraft">Aircraft</option>
              <option value="any">Any Entity Type</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-[#475569] mb-1">
              Country / Nationality (ISO-2)
            </label>
            <input
              type="text"
              value={country}
              onChange={(e) => setCountry(e.target.value.toUpperCase())}
              placeholder="e.g. EG, RU, US"
              className="w-full px-3 py-2 border border-[#CBD5E1] rounded-lg text-xs bg-[#F8FAFC] focus:bg-white focus:border-[#002D72] outline-none font-mono"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-[#475569] mb-1">
              Date of Birth (YYYY-MM-DD)
            </label>
            <input
              type="text"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              placeholder="e.g. 1982-05-14"
              className="w-full px-3 py-2 border border-[#CBD5E1] rounded-lg text-xs bg-[#F8FAFC] focus:bg-white focus:border-[#002D72] outline-none font-mono"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-[#475569] mb-1">
              National ID / Passport Number
            </label>
            <input
              type="text"
              value={idNumber}
              onChange={(e) => setIdNumber(e.target.value)}
              placeholder="e.g. EG-NAT-28205140102931"
              className="w-full px-3 py-2 border border-[#CBD5E1] rounded-lg text-xs bg-[#F8FAFC] focus:bg-white focus:border-[#002D72] outline-none font-mono"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-semibold text-[#475569]">
                Confidence Threshold
              </label>
              <span className="font-mono text-[11px] font-bold text-[#002D72]">
                {Math.round(threshold * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.4"
              max="0.95"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="w-full cursor-pointer accent-[#002D72] mt-2"
            />
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center justify-between pt-2">
          <div className="text-[11px] text-[#64748B] flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-[#002D72]" />
            <span>Includes Arabic Tashkeel stripping, Hamza unification &amp; transliteration equivalences.</span>
          </div>

          <Button
            size="sm"
            variant="primary"
            onClick={handleScreenEntity}
            disabled={loading || !name.trim()}
            className="bg-[#002D72] hover:bg-[#001D4A] text-white flex items-center gap-1.5 px-4 font-bold"
          >
            {loading ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Search className="w-3.5 h-3.5" />
            )}
            Run Screening via MCP
          </Button>
        </div>

        {error && (
          <div className="p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-lg text-xs text-[#DC2626] flex items-center gap-2">
            <XCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Case-Level Screening Results Banner */}
      {caseResult && (
        <div className="p-4 bg-white rounded-xl border border-[#CBD5E1] shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
            <div>
              <h4 className="font-bold text-sm text-[#002D72]">
                Case Participants Screening Summary: {caseResult.case_id}
              </h4>
              <p className="text-[11px] text-[#64748B]">
                {caseResult.total_entities_screened} entities evaluated • {caseResult.potential_matches_count} potential match(es) detected
              </p>
            </div>
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                caseResult.review_required
                  ? 'bg-red-100 text-red-700 border border-red-200'
                  : 'bg-green-100 text-green-700 border border-green-200'
              }`}
            >
              {caseResult.overall_status}
            </span>
          </div>

          <div className="space-y-3">
            {caseResult.entities?.map((ent: any, idx: number) => (
              <div
                key={idx}
                className="p-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#0F172A]">{ent.input_name}</span>
                    <span className="text-[10px] text-[#64748B] bg-white px-2 py-0.5 rounded border border-[#E2E8F0]">
                      {ent.participant_role}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#64748B] mt-0.5">
                    Match Confidence: <strong>{Math.round(ent.confidence_score * 100)}%</strong> • Source:{' '}
                    {ent.metadata?.source_queried || 'MCP'}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {ent.match_found ? (
                    <span className="px-2.5 py-1 bg-red-100 text-red-700 rounded-md font-bold text-[11px] flex items-center gap-1">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      Review Required
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 bg-green-100 text-green-700 rounded-md font-bold text-[11px] flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Cleared (No Match)
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Direct Entity Screening Match Results */}
      {screeningResult && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-[#F8FAFC] p-3.5 rounded-xl border border-[#E2E8F0]">
            <div>
              <span className="text-[10px] uppercase font-bold text-[#64748B]">Screening Outcome</span>
              <div className="flex items-center gap-2 mt-0.5">
                <h4 className="text-base font-bold text-[#0F172A]">
                  {screeningResult.match_found ? 'Potential Watchlist Match Detected' : 'No Adverse Watchlist Hits'}
                </h4>
                <span
                  className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${
                    screeningResult.best_match_confidence >= 0.85
                      ? 'bg-red-100 text-red-800'
                      : screeningResult.best_match_confidence >= 0.65
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-green-100 text-green-800'
                  }`}
                >
                  Best Match: {Math.round(screeningResult.best_match_confidence * 100)}%
                </span>
              </div>
            </div>

            <div className="text-right text-[11px] text-[#64748B]">
              <p>Latency: <strong>{screeningResult.execution_metadata?.latency_ms} ms</strong></p>
              <p>Source: <strong>{screeningResult.execution_metadata?.source_queried}</strong></p>
            </div>
          </div>

          {/* Matches List */}
          {screeningResult.matched_entities?.length > 0 ? (
            <div className="space-y-3">
              {screeningResult.matched_entities.map((cand: any, idx: number) => {
                const confPercent = Math.round(cand.confidence_score * 100);
                const isHigh = confPercent >= 85;
                const isMedium = confPercent >= 65 && confPercent < 85;

                return (
                  <div
                    key={idx}
                    className={`p-4 rounded-xl border transition-all ${
                      isHigh
                        ? 'border-red-300 bg-red-50/30'
                        : isMedium
                        ? 'border-amber-300 bg-amber-50/20'
                        : 'border-[#CBD5E1] bg-white'
                    }`}
                  >
                    {/* Header Row */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E2E8F0]/60 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h5 className="font-bold text-sm text-[#0F172A]">{cand.caption}</h5>
                          <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-[#CBD5E1] text-[#64748B]">
                            {cand.entity_type || 'Entity'}
                          </span>
                          {cand.entity_id && (
                            <span className="text-[10px] font-mono text-[#94A3B8]">
                              ID: {cand.entity_id}
                            </span>
                          )}
                        </div>

                        {/* Sanctions Program Badges */}
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {cand.sanctions_details?.sanctions_programs?.map((prog: string, pIdx: number) => (
                            <span
                              key={pIdx}
                              className="px-2 py-0.5 bg-red-100 text-red-800 rounded text-[10px] font-bold"
                            >
                              {prog}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Confidence Score Gauge */}
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <span className="text-[10px] uppercase font-bold text-[#64748B]">
                            Match Confidence
                          </span>
                          <p
                            className={`font-mono text-base font-extrabold ${
                              isHigh ? 'text-red-600' : isMedium ? 'text-amber-600' : 'text-green-600'
                            }`}
                          >
                            {confPercent}%
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Breakdown of Signals */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3 pt-1">
                      {/* Matched Attributes */}
                      <div>
                        <span className="text-[10px] uppercase font-bold text-green-700 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          Matched Factors ({cand.matched_fields?.length || 0})
                        </span>
                        <div className="mt-1 space-y-1">
                          {cand.matched_fields?.map((f: string, fIdx: number) => (
                            <div
                              key={fIdx}
                              className="p-1.5 bg-green-50 border border-green-200 rounded text-[11px] text-green-800 font-medium"
                            >
                              {f}
                            </div>
                          ))}
                          {(!cand.matched_fields || cand.matched_fields.length === 0) && (
                            <p className="text-[10px] text-[#94A3B8] italic">No direct factors matched.</p>
                          )}
                        </div>
                      </div>

                      {/* Conflicting Attributes */}
                      <div>
                        <span className="text-[10px] uppercase font-bold text-red-700 flex items-center gap-1">
                          <XCircle className="w-3 h-3" />
                          Conflicting Factors ({cand.conflicting_fields?.length || 0})
                        </span>
                        <div className="mt-1 space-y-1">
                          {cand.conflicting_fields?.map((f: string, fIdx: number) => (
                            <div
                              key={fIdx}
                              className="p-1.5 bg-red-50 border border-red-200 rounded text-[11px] text-red-800 font-medium"
                            >
                              {f}
                            </div>
                          ))}
                          {(!cand.conflicting_fields || cand.conflicting_fields.length === 0) && (
                            <p className="text-[10px] text-[#94A3B8] italic">No conflicting factors.</p>
                          )}
                        </div>
                      </div>

                      {/* Missing Attributes */}
                      <div>
                        <span className="text-[10px] uppercase font-bold text-[#64748B] flex items-center gap-1">
                          <Info className="w-3 h-3" />
                          Missing Identifiers ({cand.missing_fields?.length || 0})
                        </span>
                        <div className="mt-1 space-y-1">
                          {cand.missing_fields?.map((f: string, fIdx: number) => (
                            <div
                              key={fIdx}
                              className="p-1.5 bg-gray-50 border border-gray-200 rounded text-[11px] text-gray-700"
                            >
                              {f}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Explainable Reasoning */}
                    <div className="mt-3 p-3 bg-white/80 rounded-lg border border-[#E2E8F0]">
                      <span className="text-[10px] uppercase font-bold text-[#002D72]">
                        Auditable Decision Rationale:
                      </span>
                      <p className="text-xs text-[#1E293B] mt-1 leading-relaxed">
                        {cand.reasoning}
                      </p>
                    </div>

                    {/* Source Citations */}
                    {cand.source_citations?.length > 0 && (
                      <div className="mt-2.5 flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] text-[#64748B] font-semibold">Official Citations:</span>
                        {cand.source_citations.map((url: string, uIdx: number) => (
                          <a
                            key={uIdx}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] text-[#002D72] hover:underline font-mono bg-[#EFF6FF] px-2 py-0.5 rounded border border-[#BFDBFE]"
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
            <div className="p-8 text-center bg-white rounded-xl border border-[#CBD5E1] space-y-2">
              <CheckCircle2 className="w-8 h-8 text-green-600 mx-auto" />
              <h4 className="font-bold text-sm text-[#0F172A]">No Matching Entities Found</h4>
              <p className="text-xs text-[#64748B] max-w-md mx-auto">
                No international sanctions, PEP records, or watchlists exceeded the {Math.round(threshold * 100)}% confidence threshold.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

