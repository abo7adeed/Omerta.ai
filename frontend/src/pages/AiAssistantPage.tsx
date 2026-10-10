import React, { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Sparkles,
  Send,
  BookOpen,
  ShieldAlert,
  Network,
  Scale,
  Clock,
  Zap,
  Database,
  BarChart3,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  RefreshCw,
  Layers,
  CheckCircle2,
  HelpCircle,
  TrendingUp,
  FileText,
  Maximize2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { api } from '../api/client';
import type {
  AgenticRAGResponse,
  ResponseBlock,
  Citation,
  MetricResult,
  TableResult,
  ChartArtifactReference,
  SourceType,
} from '../api/client';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  ragResponse?: AgenticRAGResponse;
  isError?: boolean;
}

export const AiAssistantPage: React.FC = () => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-welcome',
      sender: 'assistant',
      text: `Hello ${user?.full_name || 'Investigator'}. I am the **Omerta.ai Agentic RAG & AI Financial Analyst**.\n\nI operate across three authoritative information tiers:\n1. **Banking Document Knowledge Base:** Internal operating policies, security protocols, AML/CFT rules, and governance manuals.\n2. **PostgreSQL Relational Ledger:** Real-time customer records, transaction histories, and risk metrics.\n3. **Neo4j Graph Topology:** Multi-hop entity links, shared devices, IP clusters, and transactional networks.\n\nAsk me compliance questions, request period comparisons, calculate metrics, or generate dynamic statistical visualizations.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [telemetry, setTelemetry] = useState<any>(null);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});
  const [selectedChartModal, setSelectedChartModal] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch live system status
  useEffect(() => {
    api
      .getAgenticRAGStatus()
      .then((data) => setTelemetry(data))
      .catch((err) => console.warn('Could not load RAG telemetry:', err));
  }, []);

  // Auto-scroll on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSubmitting]);

  const samplePrompts = [
    {
      category: 'Policy RAG',
      title: 'Security Hold Access Restoration',
      prompt: 'What is the internal banking policy for restoring account access after a security hold?',
      icon: Scale,
      badge: 'DOCUMENTS',
    },
    {
      category: 'Financial Analytics',
      title: 'Transaction Volume & Aggregation',
      prompt: 'How many transactions occurred in the system and what is the total volume in EGP?',
      icon: Database,
      badge: 'POSTGRESQL',
    },
    {
      category: 'Graph Topology',
      title: 'Shared Device Ring Discovery',
      prompt: 'Which accounts are connected through shared devices or IP clusters?',
      icon: Network,
      badge: 'NEO4J',
    },
    {
      category: 'Visualization',
      title: 'Dynamic Monthly Trend Chart',
      prompt: 'Plot transaction volume by month as a bar chart with corporate colors',
      icon: BarChart3,
      badge: 'MATPLOTLIB',
    },
    {
      category: 'Comparative Analysis',
      title: 'Period Comparison & Growth',
      prompt: 'Compare transaction activity between the current period and previous period',
      icon: TrendingUp,
      badge: 'ANALYTICS',
    },
    {
      category: 'Cross-Source Case',
      title: 'Flagged Transaction Review',
      prompt: 'Why was transaction TXN-1002 flagged and which AML policies apply?',
      icon: ShieldAlert,
      badge: 'CROSS-SOURCE',
    },
  ];

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || inputPrompt).trim();
    if (!query || isSubmitting) return;

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt('');
    setIsSubmitting(true);

    try {
      const response: AgenticRAGResponse = await api.queryAgenticRAG({
        question: query,
        conversation_id: `conv-${user?.id || 'demo'}`,
      });

      const assistantMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        ragResponse: response,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error('Agentic RAG query error:', err);
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        text: `**Operational Alert:** Unable to complete agentic request.\n\n*Error details:* ${err?.message || 'Failed to connect to RAG orchestration engine.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleCitations = (msgId: string) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const renderSourceBadge = (source: SourceType) => {
    switch (source) {
      case 'documents':
        return (
          <span
            key={source}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]"
          >
            <BookOpen className="w-2.5 h-2.5" />
            Policy KB
          </span>
        );
      case 'postgresql':
        return (
          <span
            key={source}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#D1FAE5] text-[#065F46] border border-[#A7F3D0]"
          >
            <Database className="w-2.5 h-2.5" />
            PostgreSQL
          </span>
        );
      case 'neo4j':
        return (
          <span
            key={source}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#EDE9FE] text-[#5B21B6] border border-[#DDD6FE]"
          >
            <Network className="w-2.5 h-2.5" />
            Neo4j Graph
          </span>
        );
      default:
        return null;
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'ANSWERED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#ECFDF5] text-[#047857] border border-[#A7F3D0] flex items-center gap-1">
            <CheckCircle2 className="w-2.5 h-2.5" /> Answered
          </span>
        );
      case 'NEEDS_CLARIFICATION':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A] flex items-center gap-1">
            <HelpCircle className="w-2.5 h-2.5" /> Needs Clarification
          </span>
        );
      case 'INSUFFICIENT_EVIDENCE':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#FEE2E2] text-[#B91C1C] border border-[#FECACA] flex items-center gap-1">
            <AlertTriangle className="w-2.5 h-2.5" /> Insufficient Evidence
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#F1F5F9] text-[#475569] border border-[#E2E8F0]">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12 animate-in fade-in duration-200">
      {/* Top Banner / System Header */}
      <Card className="p-6 bg-gradient-to-r from-white via-[#F8FAFC] to-white border-[#E2E8F0] shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-13 h-13 rounded-[14px] bg-[#002D72] text-[#F9A825] flex items-center justify-center shadow-md shrink-0">
              <Bot className="w-7 h-7 stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl font-extrabold text-[#002D72] tracking-tight">
                  Omerta.ai Agentic RAG &amp; Financial Analyst
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-[#002D72] text-white">
                  v2.0 Production
                </span>
              </div>
              <p className="text-xs text-[#64748B] mt-1 max-w-2xl">
                Hybrid multi-source RAG across versioned policy documents, PostgreSQL core ledger, and Neo4j topological relationships with deterministic financial math and dynamic Matplotlib charts.
              </p>
            </div>
          </div>

          {/* Telemetry Pills */}
          <div className="flex items-center gap-2 self-start md:self-auto bg-white p-2.5 rounded-[12px] border border-[#E2E8F0] shadow-xs text-[11px]">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-[#F0FDF4] rounded-[8px] text-[#166534] font-medium">
              <span className="w-2 h-2 rounded-full bg-[#22C55E] animate-pulse" />
              <span>Orchestrator: Ready</span>
            </div>
            <div className="text-[#94A3B8]">•</div>
            <div className="text-[#475569] font-medium">
              Docs: <strong className="text-[#002D72]">{telemetry?.sources?.document_kb?.indexed_documents || 6}</strong> ({telemetry?.sources?.document_kb?.indexed_chunks || 23} chunks)
            </div>
          </div>
        </div>
      </Card>

      {/* Suggested Fast Actions */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-[#002D72] flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#F9A825]" />
            Sample Analytical Queries
          </span>
          <span className="text-[11px] text-[#94A3B8]">Click any prompt to trigger multi-tool workflow</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {samplePrompts.map((sp, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(sp.prompt)}
              disabled={isSubmitting}
              className="p-3 bg-white border border-[#E2E8F0] rounded-[12px] text-left hover:border-[#002D72] hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] group-hover:text-[#002D72]">
                    {sp.category}
                  </span>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#F1F5F9] text-[#475569] border border-[#E2E8F0]">
                    {sp.badge}
                  </span>
                </div>
                <div className="text-xs font-bold text-[#0F172A] group-hover:text-[#002D72] flex items-center gap-1.5 mb-1">
                  <sp.icon className="w-3.5 h-3.5 text-[#F9A825] shrink-0" />
                  <span>{sp.title}</span>
                </div>
                <p className="text-[11px] text-[#64748B] line-clamp-2 leading-relaxed">{sp.prompt}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Interface */}
      <Card className="min-h-[640px] flex flex-col overflow-hidden border-[#CBD5E1] shadow-sm">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6 bg-[#FAFAF9]">
          {messages.map((m) => {
            const isAi = m.sender === 'assistant';
            const rag = m.ragResponse;
            const msgId = m.id;
            const isCitationsOpen = expandedCitations[msgId] ?? false;

            return (
              <div key={msgId} className={`flex flex-col ${isAi ? 'items-start' : 'items-end'}`}>
                {/* Message Header */}
                <div className="flex items-center gap-2 mb-1 text-[11px] text-[#64748B]">
                  <span className="font-bold text-[#002D72]">
                    {isAi ? 'Omerta AI Analyst' : (user?.full_name || 'Investigator')}
                  </span>
                  <span>•</span>
                  <span className="font-mono text-[10px]">{m.timestamp}</span>
                  {rag && (
                    <>
                      <span>•</span>
                      <span className="font-mono text-[10px] text-[#475569]">
                        {rag.execution_time_ms}ms
                      </span>
                    </>
                  )}
                </div>

                {/* Bubble Container */}
                <div
                  className={`w-full max-w-4xl rounded-[16px] p-5 shadow-xs transition-all ${
                    isAi
                      ? 'bg-white border border-[#E2E8F0] text-[#0F172A]'
                      : 'bg-[#002D72] text-white ml-auto max-w-2xl'
                  }`}
                >
                  {/* AI Metadata Bar (Status & Sources) */}
                  {isAi && rag && (
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-[#F1F5F9]">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#94A3B8]">
                          Sources:
                        </span>
                        {rag.sources_used.length > 0 ? (
                          rag.sources_used.map((s) => renderSourceBadge(s))
                        ) : (
                          <span className="text-[10px] text-[#94A3B8] italic">Direct Knowledge</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {renderStatusBadge(rag.status)}
                        <span className="text-[10px] font-mono text-[#94A3B8]">
                          ID: {rag.investigation_id}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Main Text / Narrative Answer */}
                  <div className="text-xs leading-relaxed whitespace-pre-wrap font-sans">
                    {m.text}
                  </div>

                  {/* Clarification prompt card */}
                  {rag?.clarification_question && (
                    <div className="mt-3 p-3.5 bg-[#FFFBEB] border border-[#FDE68A] rounded-[10px] flex items-start gap-2.5 text-xs text-[#92400E]">
                      <HelpCircle className="w-4 h-4 text-[#F59E0B] shrink-0 mt-0.5" />
                      <div>
                        <strong className="block font-semibold">Clarification Required:</strong>
                        <span>{rag.clarification_question}</span>
                      </div>
                    </div>
                  )}

                  {/* Rich Response Blocks */}
                  {rag && rag.response_blocks && rag.response_blocks.length > 0 && (
                    <div className="mt-4 space-y-4 pt-3 border-t border-[#F1F5F9]">
                      {rag.response_blocks.map((block: ResponseBlock, bIdx: number) => {
                        // 1. METRICS BLOCK
                        if (block.type === 'metric') {
                          return (
                            <div key={bIdx} className="space-y-1.5">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-[#002D72] flex items-center gap-1">
                                <TrendingUp className="w-3 h-3 text-[#F9A825]" /> Verified Financial Metrics
                              </span>
                              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                                {block.metrics.map((met: MetricResult, mIdx: number) => (
                                  <div
                                    key={mIdx}
                                    className="p-3 bg-[#F8FAFC] rounded-[10px] border border-[#E2E8F0] shadow-2xs hover:border-[#002D72] transition-colors"
                                  >
                                    <div className="text-[10px] font-medium text-[#64748B] uppercase tracking-wide">
                                      {met.label}
                                    </div>
                                    <div className="text-base font-extrabold text-[#002D72] mt-0.5">
                                      {typeof met.value === 'number'
                                        ? met.value.toLocaleString()
                                        : met.value}
                                      {met.unit && (
                                        <span className="text-xs font-normal text-[#64748B] ml-1">
                                          {met.unit}
                                        </span>
                                      )}
                                    </div>
                                    {met.period && (
                                      <div className="text-[10px] text-[#94A3B8] mt-1 font-mono">
                                        Period: {met.period}
                                      </div>
                                    )}
                                    {met.comparison && (
                                      <div className="text-[10px] text-[#059669] font-medium mt-0.5">
                                        {met.comparison}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          );
                        }

                        // 2. TABLE BLOCK
                        if (block.type === 'table') {
                          return (
                            <div key={bIdx} className="space-y-1.5">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-[#002D72] flex items-center gap-1">
                                <Layers className="w-3 h-3 text-[#002D72]" /> {block.table.title}
                              </span>
                              <div className="overflow-x-auto rounded-[10px] border border-[#E2E8F0]">
                                <table className="w-full text-[11px] text-left">
                                  <thead className="bg-[#002D72] text-white uppercase text-[10px]">
                                    <tr>
                                      {block.table.columns.map((col, cIdx) => (
                                        <th key={cIdx} className="px-3 py-2 font-semibold">
                                          {col}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-[#E2E8F0] bg-white">
                                    {block.table.rows.map((row, rIdx) => (
                                      <tr key={rIdx} className="hover:bg-[#F8FAFC]">
                                        {row.map((cell, cellIdx) => (
                                          <td
                                            key={cellIdx}
                                            className="px-3 py-1.5 text-[#334155] font-mono text-[10px]"
                                          >
                                            {cell === null ? '—' : String(cell)}
                                          </td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          );
                        }

                        // 3. CHART BLOCK
                        if (block.type === 'chart') {
                          const chart = block.chart;
                          return (
                            <div key={bIdx} className="space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-[#002D72] flex items-center gap-1">
                                  <BarChart3 className="w-3 h-3 text-[#F9A825]" /> {chart.title}
                                </span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 text-[10px] px-2 text-[#002D72] flex items-center gap-1"
                                  onClick={() => setSelectedChartModal(chart.artifact_url)}
                                >
                                  <Maximize2 className="w-3 h-3" /> Expand
                                </Button>
                              </div>
                              <div className="relative group bg-white border border-[#E2E8F0] rounded-[12px] p-2 overflow-hidden shadow-xs hover:border-[#002D72] transition-colors">
                                <img
                                  src={chart.artifact_url}
                                  alt={chart.title}
                                  className="w-full h-auto rounded-[8px] object-contain max-h-[360px] mx-auto cursor-pointer"
                                  onClick={() => setSelectedChartModal(chart.artifact_url)}
                                  loading="lazy"
                                />
                                <div className="mt-2 px-2 py-1 bg-[#F8FAFC] rounded text-[10px] text-[#64748B] flex items-center justify-between">
                                  <span>{chart.data_summary}</span>
                                  <span className="font-mono text-[9px] text-[#94A3B8]">
                                    ID: {chart.artifact_id}
                                  </span>
                                </div>
                              </div>
                            </div>
                          );
                        }

                        // 4. WARNING BLOCK
                        if (block.type === 'warning') {
                          return (
                            <div
                              key={bIdx}
                              className="p-3 bg-[#FFFBEB] border border-[#FDE68A] rounded-[10px] flex items-start gap-2 text-xs text-[#92400E]"
                            >
                              <AlertTriangle className="w-4 h-4 text-[#F59E0B] shrink-0 mt-0.5" />
                              <div>
                                <span className="font-bold">{block.title}: </span>
                                <span>{block.message}</span>
                              </div>
                            </div>
                          );
                        }

                        // 5. REPORT BLOCK
                        if (block.type === 'report') {
                          return (
                            <div
                              key={bIdx}
                              className="p-4 bg-[#F8FAFC] border border-[#CBD5E1] rounded-[12px] space-y-2.5"
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-[#002D72] flex items-center gap-1.5">
                                  <FileText className="w-3.5 h-3.5 text-[#002D72]" />{' '}
                                  {block.report_title}
                                </span>
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]">
                                  {block.recommended_action}
                                </span>
                              </div>
                              <p className="text-xs text-[#334155] leading-relaxed">
                                {block.executive_summary}
                              </p>
                              {block.key_findings.length > 0 && (
                                <ul className="text-[11px] text-[#475569] space-y-1 list-disc pl-4">
                                  {block.key_findings.map((f, fIdx) => (
                                    <li key={fIdx}>{f}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          );
                        }

                        return null;
                      })}
                    </div>
                  )}

                  {/* Expandable Citations Drawer */}
                  {rag && rag.citations && rag.citations.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-[#F1F5F9]">
                      <button
                        onClick={() => toggleCitations(msgId)}
                        className="w-full flex items-center justify-between py-1 text-[11px] font-bold text-[#002D72] hover:text-[#1E88E5] transition-colors cursor-pointer"
                      >
                        <span className="flex items-center gap-1.5 uppercase tracking-wider text-[10px]">
                          <BookOpen className="w-3.5 h-3.5 text-[#F9A825]" />
                          Verified Evidence Citations ({rag.citations.length})
                        </span>
                        {isCitationsOpen ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {isCitationsOpen && (
                        <div className="mt-2.5 space-y-2 animate-in fade-in slide-in-from-top-1 duration-150">
                          {rag.citations.map((c: Citation, cIdx: number) => (
                            <div
                              key={cIdx}
                              className="p-2.5 bg-[#F8FAFC] rounded-[8px] border border-[#E2E8F0] text-[11px] space-y-1"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-bold text-[#0F172A] truncate">
                                  {c.title}
                                </span>
                                <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-white border border-[#CBD5E1] text-[#475569] shrink-0">
                                  {c.locator}
                                </span>
                              </div>
                              {c.excerpt && (
                                <p className="text-[10px] text-[#64748B] italic bg-white p-2 rounded border border-[#E2E8F0] line-clamp-3">
                                  "{c.excerpt}"
                                </p>
                              )}
                              <div className="flex items-center gap-2 text-[9px] text-[#94A3B8]">
                                <span>Evidence ID: {c.evidence_id}</span>
                                {c.version && <span>• Version: {c.version}</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Limitations and Disclaimers */}
                  {rag && rag.limitations && rag.limitations.length > 0 && (
                    <div className="mt-3 pt-2 text-[10px] text-[#94A3B8] border-t border-[#F8FAFC] space-y-0.5">
                      <span className="font-semibold block uppercase tracking-wider text-[9px]">
                        Analytical Boundaries:
                      </span>
                      {rag.limitations.map((lim, lIdx) => (
                        <div key={lIdx} className="flex items-start gap-1">
                          <span>•</span>
                          <span>{lim}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Real-time thinking / tool execution status */}
          {isSubmitting && (
            <div className="flex items-center gap-3 p-4 bg-white border border-[#E2E8F0] rounded-[14px] max-w-md shadow-xs animate-pulse">
              <div className="w-8 h-8 rounded-full bg-[#002D72]/10 flex items-center justify-center text-[#002D72]">
                <RefreshCw className="w-4 h-4 animate-spin text-[#002D72]" />
              </div>
              <div className="text-xs space-y-0.5">
                <span className="font-bold text-[#002D72] block">
                  Agentic Tool Orchestration Active
                </span>
                <span className="text-[11px] text-[#64748B]">
                  Querying PostgreSQL, Neo4j, and Document KB with deterministic calculations...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-[#E2E8F0] bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <Input
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              placeholder="Ask banking policy, query transaction metrics, examine mule rings, or request charts..."
              className="h-12 text-xs flex-1 border-[#CBD5E1] focus:border-[#002D72] focus:ring-[#002D72]"
              disabled={isSubmitting}
            />
            <Button
              type="submit"
              variant="primary"
              size="md"
              className="h-12 px-5 bg-[#002D72] hover:bg-[#001D4A] text-white flex items-center gap-2"
              disabled={!inputPrompt.trim() || isSubmitting}
            >
              {isSubmitting ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span className="font-bold">Execute</span>
            </Button>
          </form>
          <div className="mt-2 flex items-center justify-between text-[10px] text-[#94A3B8]">
            <span>Read-only banking analysis • Mathematical precision • Evidence grounded</span>
            <div className="flex items-center gap-2">
              <span>Quick tags:</span>
              <button
                type="button"
                onClick={() => setInputPrompt('What is the status and history of account ACC-1001?')}
                className="hover:text-[#002D72] underline cursor-pointer"
              >
                ACC-1001
              </button>
              <button
                type="button"
                onClick={() => setInputPrompt('Why was transaction TXN-1002 flagged?')}
                className="hover:text-[#002D72] underline cursor-pointer"
              >
                TXN-1002
              </button>
              <button
                type="button"
                onClick={() => setInputPrompt('Which accounts share device DEV-1001?')}
                className="hover:text-[#002D72] underline cursor-pointer"
              >
                DEV-1001
              </button>
            </div>
          </div>
        </div>
      </Card>

      {/* Modal for Chart Zoom View */}
      {selectedChartModal && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in"
          onClick={() => setSelectedChartModal(null)}
        >
          <div
            className="bg-white rounded-[16px] max-w-4xl w-full p-6 shadow-2xl relative space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
              <h3 className="text-sm font-bold text-[#002D72] flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-[#F9A825]" />
                Dynamic Analytical Visualization (Full Resolution)
              </h3>
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                onClick={() => setSelectedChartModal(null)}
              >
                Close
              </Button>
            </div>
            <div className="flex justify-center p-2 bg-[#FAFAF9] rounded-[10px]">
              <img
                src={selectedChartModal}
                alt="Analytical Chart"
                className="max-h-[75vh] w-auto object-contain rounded"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
