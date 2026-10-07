import React, { useEffect, useState, useMemo, useRef } from 'react';
import {
  Share2,
  RefreshCw,
  Info,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Search,
  X,
  Activity,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../api/client';
import type { GraphNode, GraphLink } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { RiskBadge } from '../components/ui/RiskBadge';

interface SearchSuggestion {
  id: string;
  title: string;
  subtitle: string;
  type: string;
  risk_level: string;
  query_value: string;
}

export const NetworkAnalysisPage: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [links, setLinks] = useState<GraphLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFocus, setActiveFocus] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'TRANSFER' | 'INFRASTRUCTURE'>('ALL');
  const [hoveredLink, setHoveredLink] = useState<GraphLink | null>(null);

  // Auto-complete suggestions state
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  const fetchGraph = async (focus?: string) => {
    setLoading(true);
    setShowSuggestions(false);
    try {
      const res = await api.getNetworkGraph({
        focus_entity_id: focus ? focus.trim() : undefined,
        max_nodes: 50,
      });
      const returnedNodes: GraphNode[] = res.nodes || [];
      const returnedLinks: GraphLink[] = res.links || [];

      setNodes(returnedNodes);
      setLinks(returnedLinks);
      setActiveFocus(focus || '');

      if (returnedNodes.length > 0) {
        if (focus) {
          const fLower = focus.toLowerCase();
          const matched = returnedNodes.find(
            (n) =>
              n.id.toLowerCase() === fLower ||
              n.customer_name?.toLowerCase().includes(fLower) ||
              n.label.toLowerCase().includes(fLower) ||
              n.omerta_user_number?.toLowerCase().includes(fLower)
          );
          setSelectedNode(matched || returnedNodes[0]);
        } else if (!selectedNode || !returnedNodes.some((n) => n.id === selectedNode.id)) {
          setSelectedNode(returnedNodes[0]);
        }
      } else {
        setSelectedNode(null);
      }
    } catch (err) {
      console.error('Failed to load network graph', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  // Debounced live search suggestions
  useEffect(() => {
    if (!searchTerm || searchTerm.trim().length < 1) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoadingSuggestions(true);
      try {
        const results = await api.getNetworkSearchSuggestions(searchTerm.trim());
        setSuggestions(results || []);
        setShowSuggestions(true);
      } catch (err) {
        console.error('Failed to load search suggestions', err);
      } finally {
        setLoadingSuggestions(false);
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setShowSuggestions(false);
    if (searchTerm.trim()) {
      fetchGraph(searchTerm.trim());
    } else {
      fetchGraph();
    }
  };

  const handleSelectSuggestion = (suggestion: SearchSuggestion) => {
    setSearchTerm(suggestion.query_value);
    setShowSuggestions(false);
    fetchGraph(suggestion.query_value);
  };

  const handleQuickPreset = (query: string) => {
    setSearchTerm(query);
    setShowSuggestions(false);
    fetchGraph(query);
  };

  // Node position layout calculation
  const nodePosMap = useMemo(() => {
    const map = new Map<string, { cx: number; cy: number }>();
    if (nodes.length === 0) return map;

    const focusNodeId = selectedNode?.id || (nodes.length > 0 ? nodes[0].id : null);
    const focusNode = nodes.find((n) => n.id === focusNodeId);
    const otherNodes = nodes.filter((n) => n.id !== focusNodeId);

    if (focusNode) {
      map.set(focusNode.id, { cx: 450, cy: 300 });

      const inboundSources = new Set(
        links
          .filter((l) => l.target === focusNode.id && l.type === 'TRANSFER')
          .map((l) => l.source)
      );
      const outboundTargets = new Set(
        links
          .filter((l) => l.source === focusNode.id && l.type === 'TRANSFER')
          .map((l) => l.target)
      );

      const leftNodes = otherNodes.filter((n) => inboundSources.has(n.id));
      const rightNodes = otherNodes.filter((n) => outboundTargets.has(n.id) && !inboundSources.has(n.id));
      const remainingNodes = otherNodes.filter((n) => !inboundSources.has(n.id) && !outboundTargets.has(n.id));

      leftNodes.forEach((n, idx) => {
        const step = leftNodes.length > 1 ? (idx / (leftNodes.length - 1 || 1)) * 340 - 170 : 0;
        map.set(n.id, { cx: 200 - (idx % 2 === 0 ? 30 : 0), cy: 300 + step });
      });

      rightNodes.forEach((n, idx) => {
        const step = rightNodes.length > 1 ? (idx / (rightNodes.length - 1 || 1)) * 340 - 170 : 0;
        map.set(n.id, { cx: 700 + (idx % 2 === 0 ? 30 : 0), cy: 300 + step });
      });

      remainingNodes.forEach((n, idx) => {
        const angle = (idx / (remainingNodes.length || 1)) * 2 * Math.PI;
        const radius = n.type === 'DEVICE' ? 180 : n.type === 'IP_ADDRESS' ? 260 : 220;
        const cx = 450 + radius * Math.cos(angle);
        const cy = 300 + radius * Math.sin(angle);
        map.set(n.id, { cx, cy });
      });
    } else {
      nodes.forEach((n, idx) => {
        const angle = (idx / (nodes.length || 1)) * 2 * Math.PI;
        const radius = 220 + (idx % 2 === 0 ? 35 : -35);
        map.set(n.id, {
          cx: 450 + radius * Math.cos(angle),
          cy: 300 + radius * Math.sin(angle),
        });
      });
    }

    return map;
  }, [nodes, links, selectedNode?.id]);

  const filteredLinks = useMemo(() => {
    if (activeFilter === 'TRANSFER') {
      return links.filter((l) => l.type === 'TRANSFER');
    }
    if (activeFilter === 'INFRASTRUCTURE') {
      return links.filter((l) => l.type === 'USED_DEVICE' || l.type === 'CONNECTED_IP');
    }
    return links;
  }, [links, activeFilter]);

  const getNodeColor = (type: string, risk?: string) => {
    if (risk === 'CRITICAL') return '#DC2626';
    if (risk === 'HIGH') return '#F9A825';
    if (type === 'ACCOUNT') return '#002D72';
    if (type === 'DEVICE') return '#D97706';
    if (type === 'IP_ADDRESS') return '#475569';
    return '#1E88E5';
  };

  const formatCurrency = (amt?: number, curr = 'EGP') => {
    if (amt === undefined || amt === null) return `0.00 ${curr}`;
    return `${Number(amt).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${curr}`;
  };

  const selectedRiskFactors: string[] = useMemo(() => {
    if (!selectedNode) return [];
    const details = selectedNode.details || {};
    return Array.isArray(details.risk_factors) ? details.risk_factors : [];
  }, [selectedNode]);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Page Header */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <Share2 className="w-4 h-4" />
            Graph Intelligence
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Network Intelligence &amp; Link Analysis
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Forensic multi-hop relationship mapping, shared devices, counterparties, and cyclic money flow detection.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Button
            onClick={() => fetchGraph(activeFocus)}
            variant="primary"
            size="sm"
            leftIcon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Graph
          </Button>
        </div>
      </Card>

      {/* Search & Filter Toolbar */}
      <Card className="p-4 space-y-3">
        <div className="flex flex-col sm:flex-row items-center gap-3">
          {/* Search with autocomplete suggestions */}
          <div ref={searchContainerRef} className="relative flex-1 w-full">
            <form onSubmit={handleSearch}>
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onFocus={() => {
                  if (suggestions.length > 0) setShowSuggestions(true);
                }}
                placeholder="Search Account (ACC-001), Customer Name, Device (DEV-101), or IP..."
                leftIcon={<Search className="w-4 h-4 text-[#64748B]" />}
                className="h-10 text-xs"
              />
            </form>

            {/* Live suggestions dropdown */}
            {showSuggestions && (
              <div className="absolute left-0 right-0 top-11 bg-white border border-[#E0DDD6] rounded-[10px] shadow-lg z-50 overflow-hidden max-h-64 overflow-y-auto">
                {suggestions.map((sug) => (
                  <div
                    key={sug.id}
                    onClick={() => handleSelectSuggestion(sug)}
                    className="p-3 hover:bg-[#FFF9E6] transition-colors cursor-pointer border-b border-[#E0DDD6] last:border-0 flex items-center justify-between"
                  >
                    <div>
                      <p className="font-bold text-[#002D72] text-xs">{sug.title}</p>
                      <p className="text-[11px] text-[#64748B]">{sug.subtitle}</p>
                    </div>
                    <RiskBadge level={sug.risk_level || 'LOW'} size="sm" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Filter switches */}
          <div className="flex items-center gap-1.5 shrink-0">
            {(['ALL', 'TRANSFER', 'INFRASTRUCTURE'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`px-3 py-2 rounded-[8px] text-xs font-bold transition-colors cursor-pointer ${
                  activeFilter === filter
                    ? 'bg-[#002D72] text-white shadow-xs'
                    : 'bg-[#F4F1EC] text-[#475569] hover:bg-[#E0DDD6]'
                }`}
              >
                {filter === 'ALL' ? 'All Links' : filter === 'TRANSFER' ? 'Transfers Only' : 'Devices & IPs'}
              </button>
            ))}
          </div>
        </div>

        {/* Quick presets */}
        <div className="flex items-center gap-2 overflow-x-auto text-xs pt-1">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] shrink-0">
            Quick Entities:
          </span>
          {['Tariq Mansour', 'ACC-1001', 'DEV-1001', '197.34.120.55'].map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => handleQuickPreset(preset)}
              className="px-2.5 py-1 rounded-[6px] bg-[#F4F1EC] hover:bg-[#EBF3FC] text-[#002D72] font-mono text-[11px] font-semibold border border-[#E0DDD6] transition-colors cursor-pointer"
            >
              {preset}
            </button>
          ))}
        </div>
      </Card>

      {/* Main Split-Pane Graph Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* GRAPH CANVAS (8 Cols) */}
        <Card className="lg:col-span-8 flex flex-col h-[680px] relative overflow-hidden bg-white">
          {/* Canvas Controls */}
          <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 bg-white/90 backdrop-blur-xs p-1.5 rounded-[10px] border border-[#E0DDD6] shadow-xs">
            <button
              onClick={() => setZoom((z) => Math.min(2, z + 0.15))}
              className="p-1.5 text-[#475569] hover:text-[#002D72] rounded-[6px] hover:bg-[#F4F1EC] cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))}
              className="p-1.5 text-[#475569] hover:text-[#002D72] rounded-[6px] hover:bg-[#F4F1EC] cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(1)}
              className="p-1.5 text-[#475569] hover:text-[#002D72] rounded-[6px] hover:bg-[#F4F1EC] cursor-pointer"
              title="Reset View"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>

          {/* SVG Graph Viewport */}
          <div className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing">
            {loading ? (
              <div className="h-full flex flex-col items-center justify-center text-[#64748B] space-y-2">
                <Share2 className="w-8 h-8 animate-spin text-[#002D72]" />
                <p className="text-xs font-bold text-[#002D72]">Rendering graph topology...</p>
              </div>
            ) : nodes.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-[#64748B]">
                No graph entities found matching query.
              </div>
            ) : (
              <svg
                className="w-full h-full"
                viewBox="0 0 900 600"
                style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', transition: 'transform 200ms ease-out' }}
              >
                <defs>
                  <marker
                    id="arrowhead-transfer"
                    markerWidth="10"
                    markerHeight="7"
                    refX="22"
                    refY="3.5"
                    orient="auto"
                  >
                    <polygon points="0 0, 10 3.5, 0 7" fill="#002D72" />
                  </marker>
                  <marker
                    id="arrowhead-infra"
                    markerWidth="8"
                    markerHeight="6"
                    refX="18"
                    refY="3"
                    orient="auto"
                  >
                    <polygon points="0 0, 8 3, 0 6" fill="#D97706" />
                  </marker>
                </defs>

                {/* Graph Links */}
                {filteredLinks.map((link, idx) => {
                  const srcPos = nodePosMap.get(link.source);
                  const tgtPos = nodePosMap.get(link.target);
                  if (!srcPos || !tgtPos) return null;

                  const isTransfer = link.type === 'TRANSFER';
                  const isHovered = hoveredLink === link;

                  return (
                    <g key={idx} onMouseEnter={() => setHoveredLink(link)} onMouseLeave={() => setHoveredLink(null)}>
                      <line
                        x1={srcPos.cx}
                        y1={srcPos.cy}
                        x2={tgtPos.cx}
                        y2={tgtPos.cy}
                        stroke={isTransfer ? '#002D72' : '#D97706'}
                        strokeWidth={isHovered ? 3 : isTransfer ? 2 : 1.5}
                        strokeDasharray={isTransfer ? undefined : '4 3'}
                        strokeOpacity={isHovered ? 1 : 0.65}
                        markerEnd={isTransfer ? 'url(#arrowhead-transfer)' : 'url(#arrowhead-infra)'}
                      />
                      {link.amount && (
                        <text
                          x={(srcPos.cx + tgtPos.cx) / 2}
                          y={(srcPos.cy + tgtPos.cy) / 2 - 6}
                          fill="#002D72"
                          fontSize={10}
                          fontWeight="bold"
                          textAnchor="middle"
                          className="select-none bg-white font-mono"
                        >
                          {Number(link.amount).toLocaleString()} {link.currency || 'EGP'}
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* Graph Nodes */}
                {nodes.map((node) => {
                  const pos = nodePosMap.get(node.id);
                  if (!pos) return null;

                  const isSelected = selectedNode?.id === node.id;
                  const nodeColor = getNodeColor(node.type, node.risk_level);

                  return (
                    <g
                      key={node.id}
                      onClick={() => setSelectedNode(node)}
                      className="cursor-pointer transition-transform hover:scale-110"
                    >
                      {/* Soft Outer Ring for Selected / High Risk */}
                      {isSelected && (
                        <circle
                          cx={pos.cx}
                          cy={pos.cy}
                          r={28}
                          fill="none"
                          stroke="#F9A825"
                          strokeWidth={3}
                          strokeOpacity={0.8}
                          className="animate-pulse"
                        />
                      )}

                      {/* Main Node Circle */}
                      <circle
                        cx={pos.cx}
                        cy={pos.cy}
                        r={node.type === 'ACCOUNT' ? 20 : 16}
                        fill={nodeColor}
                        stroke="#FFFFFF"
                        strokeWidth={2.5}
                        className="shadow-sm"
                      />

                      {/* Node Label */}
                      <text
                        x={pos.cx}
                        y={pos.cy + (node.type === 'ACCOUNT' ? 32 : 28)}
                        fill="#002D72"
                        fontSize={11}
                        fontWeight="bold"
                        textAnchor="middle"
                        className="select-none"
                      >
                        {node.customer_name || node.label || node.id}
                      </text>

                      {node.type === 'ACCOUNT' && (
                        <text
                          x={pos.cx}
                          y={pos.cy + 44}
                          fill="#64748B"
                          fontSize={9}
                          fontFamily="monospace"
                          textAnchor="middle"
                          className="select-none"
                        >
                          {node.id}
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        </Card>

        {/* ENTITY INSPECTION SIDEBAR (4 Cols) */}
        <Card className="lg:col-span-4 flex flex-col h-[680px] overflow-hidden">
          {selectedNode ? (
            <div className="flex-1 flex flex-col overflow-y-auto">
              {/* Header */}
              <CardHeader className="p-5 border-b border-[#E0DDD6] bg-[#F4F1EC]/40">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B]">
                    {selectedNode.type} Entity
                  </span>
                  <RiskBadge level={selectedNode.risk_level || 'LOW'} />
                </div>
                <CardTitle className="text-base truncate">
                  {selectedNode.customer_name || selectedNode.label || selectedNode.id}
                </CardTitle>
                <p className="text-xs text-[#64748B] font-mono mt-0.5">ID: {selectedNode.id}</p>
              </CardHeader>

              <CardContent className="p-5 space-y-4 flex-1">
                {/* Entity Metrics */}
                <div className="grid grid-cols-2 gap-2 bg-[#F4F1EC] p-3 rounded-[10px] border border-[#E0DDD6] text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Degree Count</span>
                    <p className="font-bold text-[#002D72] mt-0.5">{(selectedNode as any).degree_count || 3} Connections</p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Risk Score</span>
                    <p className="font-bold text-[#F9A825] font-mono mt-0.5">
                      {selectedNode.risk_score ? `${selectedNode.risk_score}%` : 'Low'}
                    </p>
                  </div>
                </div>

                {/* Risk Factors */}
                {selectedRiskFactors.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#002D72]">
                      Observed Risk Vectors
                    </span>
                    <div className="space-y-1">
                      {selectedRiskFactors.map((rf, idx) => (
                        <div key={idx} className="p-2 bg-[#FFF9E6] border border-[#FFE082] rounded-[8px] text-[11px] text-[#002D72] flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-[#F9A825] shrink-0" />
                          <span>{rf}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Inflow Sources */}
                {selectedNode.inflow_sources && selectedNode.inflow_sources.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#002D72]">
                      Inflow Sources (Incoming Funds)
                    </span>
                    <div className="space-y-1 text-xs">
                      {selectedNode.inflow_sources.map((src, idx) => (
                        <div key={idx} className="p-2.5 bg-white border border-[#E0DDD6] rounded-[8px] flex items-center justify-between">
                          <div className="truncate max-w-[140px]">
                            <p className="font-bold text-[#0F172A] truncate">{src.sender_name || src.sender_account}</p>
                            <p className="text-[10px] text-[#64748B] font-mono">{src.sender_account}</p>
                          </div>
                          <span className="font-mono font-bold text-[#10B981] text-xs">
                            +{formatCurrency(src.amount, src.currency)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Outflow Destinations */}
                {selectedNode.outflow_destinations && selectedNode.outflow_destinations.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#002D72]">
                      Outflow Destinations (Disbursed Funds)
                    </span>
                    <div className="space-y-1 text-xs">
                      {selectedNode.outflow_destinations.map((dest, idx) => (
                        <div key={idx} className="p-2.5 bg-white border border-[#E0DDD6] rounded-[8px] flex items-center justify-between">
                          <div className="truncate max-w-[140px]">
                            <p className="font-bold text-[#0F172A] truncate">{dest.recipient_name || dest.recipient_account}</p>
                            <p className="text-[10px] text-[#64748B] font-mono">{dest.recipient_account}</p>
                          </div>
                          <span className="font-mono font-bold text-[#002D72] text-xs">
                            -{formatCurrency(dest.amount, dest.currency)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-[#64748B]">
              <Info className="w-8 h-8 text-[#CBD5E1] mb-2" />
              <p className="font-bold text-[#002D72]">Click an entity in the graph</p>
              <p className="text-xs text-[#64748B]">Inspect degree centrality, connected accounts, and transaction topology.</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
