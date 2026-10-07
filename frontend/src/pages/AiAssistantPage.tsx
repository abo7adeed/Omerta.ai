import React, { useState } from 'react';
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
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  citations?: string[];
}

export const AiAssistantPage: React.FC = () => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-1',
      sender: 'assistant',
      text: `Hello ${user?.full_name || 'Investigator'}. I am the **Omerta.ai Financial Crime & Regulatory Copilot**. I assist with autonomous case intelligence, mule network analysis, and AML compliance queries.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      citations: ['FATF Recommendations 10 & 16', 'Omerta Typology Knowledge Base v2026.1'],
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const samplePrompts = [
    {
      title: 'Analyze Smurfing & Structuring',
      prompt: 'Check for transactions structured just below the 50,000 EGP reporting threshold in the last 48 hours.',
      icon: ShieldAlert,
    },
    {
      title: 'FATF Recommendation 16 Travel Rule',
      prompt: 'Explain wire transfer Travel Rule requirements for cross-border transactions involving high-risk jurisdictions.',
      icon: Scale,
    },
    {
      title: 'Mule Ring Topology Summary',
      prompt: 'Summarize the multi-account device cluster connected to Device DEV-1001.',
      icon: Network,
    },
  ];

  const handleSend = (textToSend?: string) => {
    const query = (textToSend || inputPrompt).trim();
    if (!query) return;

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt('');
    setIsTyping(true);

    setTimeout(() => {
      const assistantMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: 'assistant',
        text: `**[RAG Knowledge Store & Multi-Agent Swarm]**\n\nYour query has been indexed against the financial-crime vector knowledge store: \`"${query}"\`.\n\nMulti-agent analysis, graph embeddings, and direct SAR narrative drafting are active. For immediate topological investigations, also consult the **Investigations Dossier** and **Network Analysis Graph** tabs.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citations: ['Omerta AML Regulatory Corpus (FATF/Egmont)', 'Graph DB: omerta-neo4j:17687'],
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setIsTyping(false);
    }, 800);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-[12px] bg-[#002D72] text-[#F9A825] flex items-center justify-center shadow-sm shrink-0">
            <Bot className="w-6 h-6 stroke-[2.2]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-[#002D72] tracking-tight">
                AI Intelligence &amp; RAG Copilot
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-[#EBF3FC] text-[#002D72] border border-[#BFDBFE]">
                Forensic RAG
              </span>
            </div>
            <p className="text-xs text-[#64748B] mt-1">
              Autonomous regulatory research, suspicious typology detection, and FinCEN narrative assistance.
            </p>
          </div>
        </div>
      </Card>

      {/* Suggested Prompts */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {samplePrompts.map((sp, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(sp.prompt)}
            className="p-3.5 bg-white border border-[#E0DDD6] rounded-[12px] text-left hover:border-[#F9A825] hover:shadow-sm transition-all cursor-pointer space-y-1"
          >
            <div className="flex items-center gap-2 text-xs font-bold text-[#002D72]">
              <sp.icon className="w-4 h-4 text-[#F9A825]" />
              <span>{sp.title}</span>
            </div>
            <p className="text-[11px] text-[#64748B] line-clamp-2">{sp.prompt}</p>
          </button>
        ))}
      </div>

      {/* Chat Conversation Card */}
      <Card className="h-[560px] flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-white">
          {messages.map((m) => {
            const isAi = m.sender === 'assistant';
            return (
              <div
                key={m.id}
                className={`flex flex-col ${isAi ? 'items-start' : 'items-end'}`}
              >
                <div className="flex items-center gap-1.5 mb-1 text-[10px] text-[#64748B]">
                  <span className="font-bold">{isAi ? 'Omerta AI Copilot' : 'Investigator'}</span>
                  <span>•</span>
                  <span className="font-mono">{m.timestamp}</span>
                </div>

                <div
                  className={`p-4 rounded-[14px] max-w-2xl text-xs leading-relaxed ${
                    isAi
                      ? 'bg-[#F4F1EC] text-[#0F172A] rounded-tl-none border border-[#E0DDD6]'
                      : 'bg-[#002D72] text-white rounded-tr-none shadow-xs'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.text}</p>

                  {m.citations && (
                    <div className="mt-3 pt-2.5 border-t border-[#E0DDD6] space-y-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#002D72] flex items-center gap-1">
                        <BookOpen className="w-3 h-3 text-[#F9A825]" />
                        Referenced Compliance Sources:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {m.citations.map((c, i) => (
                          <span
                            key={i}
                            className="text-[10px] font-mono px-2 py-0.5 rounded bg-white text-[#475569] border border-[#E0DDD6]"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {isTyping && (
            <div className="flex items-center gap-2 p-3 bg-[#F4F1EC] rounded-[10px] w-48 text-xs text-[#64748B] animate-pulse">
              <Bot className="w-4 h-4 text-[#002D72]" />
              <span>Querying vector store...</span>
            </div>
          )}
        </div>

        {/* Prompt Input */}
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="p-3.5 border-t border-[#E0DDD6] bg-[#F4F1EC]/40 flex items-center gap-2">
          <Input
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            placeholder="Ask compliance copilot e.g. Analyze rapid pass-through mule patterns..."
            className="h-11 text-xs flex-1"
          />
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={!inputPrompt.trim()}
          >
            <Send className="w-4 h-4" />
            <span>Submit</span>
          </Button>
        </form>
      </Card>
    </div>
  );
};
