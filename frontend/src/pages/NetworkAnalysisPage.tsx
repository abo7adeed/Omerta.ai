import React, { useEffect, useState, useMemo, useRef } from 'react';
import {
  Share2,
  RefreshCw,
  Info,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Search,
  AlertTriangle,
  Move,
  Smartphone,
  Globe,
  User,
  ArrowRight,
  Shield,
  Layers,
} from 'lucide-react';
import { api } from '../api/client';
import type { GraphNode, GraphLink } from '../types';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
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

interface NodeCoord {
  cx: number;
  cy: number;
}

export const NetworkAnalysisPage: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [links, setLinks] = useState<GraphLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFocus, setActiveFocus] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'TRANSFER' | 'INFRASTRUCTURE'>('ALL');
  const [hoveredLink, setHoveredLink] = useState<GraphLink | null>(null);

  // Auto-complete suggestions state
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Node position map with drag capability
  const [nodePositions, setNodePositions] = useState<Record<string, NodeCoord>>({});
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

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

  // Click outside listener for search suggestions
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter links according to active selection
  const filteredLinks = useMemo(() => {
    if (activeFilter === 'TRANSFER') {
      return links.filter((l) => l.type === 'TRANSFER');
    }
    if (activeFilter === 'INFRASTRUCTURE') {
      return links.filter((l) => l.type === 'USED_DEVICE' || l.type === 'CONNECTED_IP');
    }
    return links;
  }, [links, activeFilter]);

  // Compute clean layout with guaranteed collision elimination
  useEffect(() => {
    if (nodes.length === 0) {
      setNodePositions({});
      return;
    }

    const posMap: Record<string, NodeCoord> = {};
    const focusNodeId = selectedNode?.id || nodes[0].id;
    const focusNode = nodes.find((n) => n.id === focusNodeId) || nodes[0];
    const otherNodes = nodes.filter((n) => n.id !== focusNode.id);

    // 1. Anchor Focus Node centrally
    posMap[focusNode.id] = { cx: 480, cy: 300 };

    // Group remaining nodes by role/type
    const counterparties = otherNodes.filter((n) => n.type === 'ACCOUNT');
    const devices = otherNodes.filter((n) => n.type === 'DEVICE');
    const ips = otherNodes.filter((n) => n.type === 'IP_ADDRESS');

    // 2. Position Counterparty Accounts on the Left quadrant
    counterparties.forEach((n, idx) => {
      const total = counterparties.length;
      const ySpread = total > 1 ? (idx / (total - 1)) * 320 - 160 : 0;
      posMap[n.id] = {
        cx: 190 - (idx % 2 === 0 ? 30 : -20),
        cy: 300 + ySpread,
      };
    });

    // 3. Position Hardware Devices in Top-Right quadrant
    devices.forEach((n, idx) => {
      const total = devices.length;
      const xOffset = (idx % 2) * 80;
      const yOffset = Math.floor(idx / 2) * 90;
      posMap[n.id] = {
        cx: 740 + xOffset,
        cy: 180 + yOffset,
      };
    });

    // 4. Position IP Addresses in Bottom-Right quadrant
    ips.forEach((n, idx) => {
      const total = ips.length;
      const xOffset = (idx % 2) * 80;
      const yOffset = Math.floor(idx / 2) * 90;
      posMap[n.id] = {
        cx: 740 + xOffset,
        cy: 420 + yOffset,
      };
    });

    // 5. Physics Collision Relaxation pass (Force-directed repulsion)
    // Mathematically guarantees that no two nodes overlap (min distance = 160px)
    const allNodeList = [focusNode, ...otherNodes];
    const MIN_DISTANCE = 160;

    for (let iter = 0; iter < 140; iter++) {
      for (let i = 0; i < allNodeList.length; i++) {
        for (let j = i + 1; j < allNodeList.length; j++) {
          const uId = allNodeList[i].id;
          const vId = allNodeList[j].id;
          const u = posMap[uId];
          const v = posMap[vId];
          if (!u || !v) continue;

          const dx = v.cx - u.cx;
          const dy = v.cy - u.cy;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;

          if (dist < MIN_DISTANCE) {
            const overlap = (MIN_DISTANCE - dist) / 2;
            const nx = dx / dist;
            const ny = dy / dist;

            // Push apart along vector (focus node has higher inertia)
            if (uId !== focusNode.id) {
              u.cx -= nx * overlap * 0.85;
              u.cy -= ny * overlap * 0.85;
            }
            if (vId !== focusNode.id) {
              v.cx += nx * overlap * 0.85;
              v.cy += ny * overlap * 0.85;
            }
          }
        }
      }

      // Constrain inside boundaries [90, 870] x [80, 520]
      for (const id in posMap) {
        if (id !== focusNode.id) {
          posMap[id].cx = Math.max(90, Math.min(870, posMap[id].cx));
          posMap[id].cy = Math.max(80, Math.min(520, posMap[id].cy));
        }
      }
    }

    setNodePositions(posMap);
  }, [nodes, links, selectedNode?.id]);

  // Compute curved paths for parallel and bidirectional links
  const computedLinks = useMemo(() => {
    // Group links by unordered node pair
    const pairGroups = new Map<string, GraphLink[]>();
    filteredLinks.forEach((l) => {
      const key = [l.source, l.target].sort().join('___');
      const list = pairGroups.get(key) || [];
      list.push(l);
      pairGroups.set(key, list);
    });

    return filteredLinks
      .map((link, idx) => {
        const srcPos = nodePositions[link.source];
        const tgtPos = nodePositions[link.target];
        if (!srcPos || !tgtPos) return null;

        const key = [link.source, link.target].sort().join('___');
        const group = pairGroups.get(key) || [link];
        const linkIndex = group.indexOf(link);
        const isMulti = group.length > 1;

        // Normal vector perpendicular to connecting line
        const dx = tgtPos.cx - srcPos.cx;
        const dy = tgtPos.cy - srcPos.cy;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const nx = -dy / dist;
        const ny = dx / dist;

        // Curve offset: if multi/bidirectional, curve outward in opposite directions (+40 / -40)
        let curveOffset = 0;
        if (isMulti) {
          const sign = link.source < link.target ? 1 : -1;
          curveOffset = sign * (linkIndex === 0 ? 42 : -42);
        } else if (link.type !== 'TRANSFER') {
          curveOffset = 18;
        }

        const midX = (srcPos.cx + tgtPos.cx) / 2;
        const midY = (srcPos.cy + tgtPos.cy) / 2;
        const ctrlX = midX + nx * curveOffset;
        const ctrlY = midY + ny * curveOffset;

        // Label location along quadratic curve at apex (t = 0.5)
        const labelX = 0.25 * srcPos.cx + 0.5 * ctrlX + 0.25 * tgtPos.cx;
        const labelY = 0.25 * srcPos.cy + 0.5 * ctrlY + 0.25 * tgtPos.cy;

        // Adjust target point along tangent so arrowhead lands on perimeter (R = 26)
        const targetRadius = 26;
        const tdx = tgtPos.cx - ctrlX;
        const tdy = tgtPos.cy - ctrlY;
        const tdist = Math.sqrt(tdx * tdx + tdy * tdy) || 1;
        const endX = tgtPos.cx - (tdx / tdist) * targetRadius;
        const endY = tgtPos.cy - (tdy / tdist) * targetRadius;

        const pathD = `M ${srcPos.cx} ${srcPos.cy} Q ${ctrlX} ${ctrlY} ${endX} ${endY}`;
        const isTransfer = link.type === 'TRANSFER';
        const isSuspicious = Boolean((link as any).is_suspicious || ((link as any).risk_score && (link as any).risk_score > 40));

        return {
          id: `link-${idx}`,
          link,
          pathD,
          labelX,
          labelY,
          isTransfer,
          isSuspicious,
          amount: link.amount,
          currency: link.currency || 'EGP',
        };
      })
      .filter(Boolean);
  }, [filteredLinks, nodePositions]);

  // Interactive Drag & Pan handlers
  const handleMouseDownNode = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    setDraggingNodeId(nodeId);
    setSelectedNode(nodes.find((n) => n.id === nodeId) || null);
  };

  const handleSvgMouseDown = (e: React.MouseEvent) => {
    if (e.target === svgRef.current || (e.target as HTMLElement).tagName === 'svg') {
      setIsPanning(true);
      panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (draggingNodeId && svgRef.current) {
      const rect = svgRef.current.getBoundingClientRect();
      const scaleX = 960 / (rect.width * zoom);
      const scaleY = 640 / (rect.height * zoom);
      const svgX = (e.clientX - rect.left - pan.x) * scaleX;
      const svgY = (e.clientY - rect.top - pan.y) * scaleY;

      setNodePositions((prev) => ({
        ...prev,
        [draggingNodeId]: {
          cx: Math.max(50, Math.min(910, svgX)),
          cy: Math.max(50, Math.min(590, svgY)),
        },
      }));
    } else if (isPanning) {
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      });
    }
  };

  const handleMouseUp = () => {
    setDraggingNodeId(null);
    setIsPanning(false);
  };

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
          {/* Autocomplete Search Input */}
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

            {/* Live Suggestions Dropdown */}
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

          {/* Filter Buttons */}
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

        {/* Quick Presets */}
        <div className="flex items-center gap-2 overflow-x-auto text-xs pt-1">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] shrink-0">
            Quick Entities:
          </span>
          {['Tariq Mansour', 'Abdo Haaland', 'ACC-1001', 'DEV-1001', '41.179.245.75'].map((preset) => (
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
        <Card className="lg:col-span-8 flex flex-col h-[700px] relative overflow-hidden bg-[#FAFAF9] border border-[#E0DDD6] shadow-sm">
          {/* Top Controls Toolbar */}
          <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 bg-white/95 backdrop-blur-xs p-1.5 rounded-[10px] border border-[#E0DDD6] shadow-sm">
            <button
              onClick={() => setZoom((z) => Math.min(2.2, z + 0.15))}
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
              onClick={() => {
                setZoom(1);
                setPan({ x: 0, y: 0 });
              }}
              className="p-1.5 text-[#475569] hover:text-[#002D72] rounded-[6px] hover:bg-[#F4F1EC] cursor-pointer"
              title="Reset View"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>

          {/* Interactive Graph Legend Bar */}
          <div className="absolute bottom-4 left-4 z-20 flex flex-wrap items-center gap-3 bg-white/95 backdrop-blur-xs px-3 py-2 rounded-[10px] border border-[#E0DDD6] text-[11px] shadow-sm text-[#475569]">
            <div className="flex items-center gap-1.5 font-medium">
              <span className="w-3 h-3 rounded-full bg-[#002D72] inline-block border border-white shadow-xs" />
              <span>Account</span>
            </div>
            <div className="flex items-center gap-1.5 font-medium">
              <span className="w-3 h-3 rounded-full bg-[#D97706] inline-block border border-white shadow-xs" />
              <span>Device</span>
            </div>
            <div className="flex items-center gap-1.5 font-medium">
              <span className="w-3 h-3 rounded-full bg-[#334155] inline-block border border-white shadow-xs" />
              <span>IP Endpoint</span>
            </div>
            <div className="h-3 w-px bg-[#CBD5E1]" />
            <div className="flex items-center gap-1.5 font-medium">
              <span className="w-4 h-0.5 bg-[#002D72] inline-block" />
              <span>Transfer Flow</span>
            </div>
            <div className="flex items-center gap-1.5 font-medium">
              <span className="w-4 h-0.5 border-t border-dashed border-[#D97706] inline-block" />
              <span>Hardware Link</span>
            </div>
          </div>

          {/* SVG Viewport */}
          <div
            className="flex-1 w-full h-full relative select-none cursor-default"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            {loading ? (
              <div className="h-full flex flex-col items-center justify-center text-[#64748B] space-y-2">
                <Share2 className="w-8 h-8 animate-spin text-[#002D72]" />
                <p className="text-xs font-bold text-[#002D72]">Calculating network topology...</p>
              </div>
            ) : nodes.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-[#64748B]">
                No graph entities found matching query.
              </div>
            ) : (
              <svg
                ref={svgRef}
                className="w-full h-full"
                viewBox="0 0 960 640"
                onMouseDown={handleSvgMouseDown}
                style={{
                  transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
                  transformOrigin: 'center center',
                  transition: draggingNodeId || isPanning ? 'none' : 'transform 180ms ease-out',
                }}
              >
                <defs>
                  {/* Subtle drop shadows */}
                  <filter id="node-shadow" x="-30%" y="-30%" width="160%" height="160%">
                    <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.08" />
                  </filter>
                  <filter id="badge-shadow" x="-30%" y="-30%" width="160%" height="160%">
                    <feDropShadow dx="0" dy="2" stdDeviation="4" floodOpacity="0.12" />
                  </filter>

                  {/* Transfer Arrowhead (Sapphire) */}
                  <marker
                    id="arrowhead-transfer"
                    markerWidth="11"
                    markerHeight="8"
                    refX="9"
                    refY="4"
                    orient="auto"
                  >
                    <polygon points="0 0, 11 4, 0 8" fill="#002D72" />
                  </marker>

                  {/* Suspicious Transfer Arrowhead (Crimson) */}
                  <marker
                    id="arrowhead-transfer-suspicious"
                    markerWidth="11"
                    markerHeight="8"
                    refX="9"
                    refY="4"
                    orient="auto"
                  >
                    <polygon points="0 0, 11 4, 0 8" fill="#DC2626" />
                  </marker>

                  {/* Device / Infrastructure Arrowhead (Amber) */}
                  <marker
                    id="arrowhead-infra"
                    markerWidth="9"
                    markerHeight="7"
                    refX="8"
                    refY="3.5"
                    orient="auto"
                  >
                    <polygon points="0 0, 9 3.5, 0 7" fill="#D97706" />
                  </marker>
                </defs>

                {/* GRAPH LINKS (Curved Paths with Non-Overlapping Arcs) */}
                {computedLinks.map((item) => {
                  if (!item) return null;
                  const { link, pathD, labelX, labelY, isTransfer, isSuspicious, amount, currency } = item;
                  const isHovered = hoveredLink === link;

                  return (
                    <g
                      key={item.id}
                      onMouseEnter={() => setHoveredLink(link)}
                      onMouseLeave={() => setHoveredLink(null)}
                      className="cursor-pointer"
                    >
                      {/* Link Curved Line */}
                      <path
                        d={pathD}
                        fill="none"
                        stroke={isSuspicious ? '#DC2626' : isTransfer ? '#002D72' : '#D97706'}
                        strokeWidth={isHovered ? 3.5 : isTransfer ? 2.5 : 1.8}
                        strokeDasharray={isTransfer ? undefined : '5 4'}
                        strokeOpacity={isHovered ? 1 : 0.75}
                        markerEnd={
                          isSuspicious
                            ? 'url(#arrowhead-transfer-suspicious)'
                            : isTransfer
                            ? 'url(#arrowhead-transfer)'
                            : 'url(#arrowhead-infra)'
                        }
                      />

                      {/* Prominent High-Contrast Amount Pill Badge */}
                      {amount && (
                        <g transform={`translate(${labelX}, ${labelY})`} className="cursor-pointer">
                          <rect
                            x="-52"
                            y="-13"
                            width="104"
                            height="26"
                            rx="13"
                            fill="#FFFFFF"
                            stroke={isSuspicious ? '#DC2626' : '#002D72'}
                            strokeWidth={isSuspicious ? 2 : 1.5}
                            filter="url(#badge-shadow)"
                            className="transition-all hover:scale-105"
                          />
                          <text
                            x="0"
                            y="4.5"
                            textAnchor="middle"
                            fill={isSuspicious ? '#DC2626' : '#002D72'}
                            fontSize={10.5}
                            fontWeight="bold"
                            fontFamily="monospace"
                            className="select-none"
                          >
                            {Number(amount).toLocaleString(undefined, {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })}{' '}
                            {currency}
                          </text>
                        </g>
                      )}
                    </g>
                  );
                })}

                {/* GRAPH NODES (Structured Intelligence Cards with Shields) */}
                {nodes.map((node) => {
                  const pos = nodePositions[node.id];
                  if (!pos) return null;

                  const isSelected = selectedNode?.id === node.id;
                  const isFocus = activeFocus && node.id.toLowerCase() === activeFocus.toLowerCase();
                  const isCritical = node.risk_level === 'CRITICAL';
                  const isHighRisk = node.risk_level === 'HIGH';

                  // Determine color & radius
                  const circleRadius = node.type === 'ACCOUNT' ? 24 : node.type === 'DEVICE' ? 20 : 18;
                  const nodeFill =
                    isCritical
                      ? '#DC2626'
                      : isHighRisk
                      ? '#F9A825'
                      : node.type === 'ACCOUNT'
                      ? '#002D72'
                      : node.type === 'DEVICE'
                      ? '#D97706'
                      : '#334155';

                  const labelTitle = node.customer_name || node.label || node.id;

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.cx}, ${pos.cy})`}
                      onMouseDown={(e) => handleMouseDownNode(e, node.id)}
                      className="cursor-grab active:cursor-grabbing"
                    >
                      {/* Selected Outer Glowing Halo */}
                      {isSelected && (
                        <circle
                          cx={0}
                          cy={0}
                          r={circleRadius + 9}
                          fill="none"
                          stroke="#F9A825"
                          strokeWidth={3}
                          strokeOpacity={0.85}
                          className="animate-pulse"
                        />
                      )}

                      {/* Main Node Circle */}
                      <circle
                        cx={0}
                        cy={0}
                        r={circleRadius}
                        fill={nodeFill}
                        stroke="#FFFFFF"
                        strokeWidth={3}
                        filter="url(#node-shadow)"
                      />

                      {/* Center Node Icon Symbol */}
                      <text
                        x={0}
                        y={4}
                        textAnchor="middle"
                        fill="#FFFFFF"
                        fontSize={11}
                        fontWeight="bold"
                        className="select-none pointer-events-none"
                      >
                        {node.type === 'ACCOUNT' ? 'Acc' : node.type === 'DEVICE' ? 'Dev' : 'IP'}
                      </text>

                      {/* Floating Label Card below Circle (Shielded White Box) */}
                      <g transform={`translate(0, ${circleRadius + 10})`}>
                        <rect
                          x="-68"
                          y="0"
                          width="136"
                          height="36"
                          rx="8"
                          fill="#FFFFFF"
                          stroke={isSelected ? '#F9A825' : '#E2E8F0'}
                          strokeWidth={isSelected ? 2 : 1.5}
                          filter="url(#node-shadow)"
                        />
                        <text
                          x="0"
                          y="15"
                          textAnchor="middle"
                          fill="#002D72"
                          fontSize={11}
                          fontWeight="bold"
                          className="select-none"
                        >
                          {labelTitle.length > 17 ? `${labelTitle.slice(0, 16)}...` : labelTitle}
                        </text>
                        <text
                          x="0"
                          y="28"
                          textAnchor="middle"
                          fill="#64748B"
                          fontSize={9.5}
                          fontFamily="monospace"
                          className="select-none"
                        >
                          {node.id}
                        </text>
                      </g>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        </Card>

        {/* ENTITY INSPECTION SIDEBAR (4 Cols) */}
        <Card className="lg:col-span-4 flex flex-col h-[700px] overflow-hidden bg-white border border-[#E0DDD6] shadow-sm">
          {selectedNode ? (
            <div className="flex-1 flex flex-col overflow-y-auto">
              {/* Header */}
              <CardHeader className="p-5 border-b border-[#E0DDD6] bg-[#F4F1EC]/50">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B]">
                    {selectedNode.type} Entity
                  </span>
                  <RiskBadge level={selectedNode.risk_level || 'LOW'} />
                </div>
                <CardTitle className="text-base truncate text-[#002D72]">
                  {selectedNode.customer_name || selectedNode.label || selectedNode.id}
                </CardTitle>
                <p className="text-xs text-[#64748B] font-mono mt-0.5">ID: {selectedNode.id}</p>
              </CardHeader>

              <CardContent className="p-5 space-y-4 flex-1">
                {/* Degree Centrality & Risk Score */}
                <div className="grid grid-cols-2 gap-2 bg-[#F4F1EC] p-3 rounded-[10px] border border-[#E0DDD6] text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Degree Count</span>
                    <p className="font-bold text-[#002D72] mt-0.5">
                      {(selectedNode as any).degree_count || 3} Connections
                    </p>
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
                        <div
                          key={idx}
                          className="p-2.5 bg-[#FFF9E6] border border-[#FFE082] rounded-[8px] text-[11px] text-[#002D72] flex items-center gap-2"
                        >
                          <AlertTriangle className="w-3.5 h-3.5 text-[#F9A825] shrink-0" />
                          <span>{rf}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Inflow Sources ("From Where Got Money") */}
                {selectedNode.inflow_sources && selectedNode.inflow_sources.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#002D72]">
                      Inflow Sources (Incoming Funds)
                    </span>
                    <div className="space-y-1 text-xs">
                      {selectedNode.inflow_sources.map((src, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 bg-white border border-[#E0DDD6] rounded-[8px] flex items-center justify-between"
                        >
                          <div className="truncate max-w-[140px]">
                            <p className="font-bold text-[#0F172A] truncate">
                              {src.sender_name || src.sender_account}
                            </p>
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

                {/* Outflow Destinations ("Where Money Went") */}
                {selectedNode.outflow_destinations && selectedNode.outflow_destinations.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#002D72]">
                      Outflow Destinations (Disbursed Funds)
                    </span>
                    <div className="space-y-1 text-xs">
                      {selectedNode.outflow_destinations.map((dest, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 bg-white border border-[#E0DDD6] rounded-[8px] flex items-center justify-between"
                        >
                          <div className="truncate max-w-[140px]">
                            <p className="font-bold text-[#0F172A] truncate">
                              {dest.recipient_name || dest.recipient_account}
                            </p>
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
              <p className="text-xs text-[#64748B]">
                Inspect degree centrality, connected accounts, and transaction topology.
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
