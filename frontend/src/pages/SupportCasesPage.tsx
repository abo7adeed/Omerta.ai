import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  LifeBuoy,
  Search,
  ShieldCheck,
  CheckCircle2,
  Send,
  RefreshCw,
  FileText,
  Paperclip,
  Check,
  X,
  Unlock,
  AlertTriangle,
  Clock,
  UserCheck,
  RotateCcw,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { StatCard } from '../components/ui/StatCard';
import type { SupportTicketItem } from '../types';

const compressImageFile = (file: File, maxDim = 1280, quality = 0.85): Promise<string> => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onerror = () => resolve('');
    reader.onload = () => {
      const result = reader.result as string;
      const img = new Image();
      img.onerror = () => resolve(result);
      img.onload = () => {
        try {
          let { width, height } = img;
          if (width > maxDim || height > maxDim) {
            if (width > height) {
              height = Math.round((height * maxDim) / width);
              width = maxDim;
            } else {
              width = Math.round((width * maxDim) / height);
              height = maxDim;
            }
          }
          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          if (!ctx) {
            resolve(result);
            return;
          }
          ctx.drawImage(img, 0, 0, width, height);
          resolve(canvas.toDataURL('image/jpeg', quality));
        } catch {
          resolve(result);
        }
      };
      img.src = result;
    };
    reader.readAsDataURL(file);
  });
};

export const SupportCasesPage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();

  // All tickets fetched from the backend (unfiltered platform master list)
  const [allCases, setAllCases] = useState<SupportTicketItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<SupportTicketItem | null>(null);
  const [activeTab, setActiveTab] = useState<'UNSOLVED' | 'PENDING_ID' | 'RESOLVED' | 'ALL'>('UNSOLVED');
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [loading, setLoading] = useState(true);

  // Role permissions
  const isSuperAdmin = user?.role === 'ADMINISTRATOR' || user?.role === 'SUB_ADMINISTRATOR';
  const canRestoreTransfer = isSuperAdmin || user?.role === 'FRAUD_ANALYST' || user?.role === 'SENIOR_INVESTIGATOR';

  // Live Staff Chat State
  const [staffMessage, setStaffMessage] = useState('');
  const [staffAttachments, setStaffAttachments] = useState<{ url: string; name: string }[]>([]);
  const [isSending, setIsSending] = useState(false);

  // Identity Verification Review State
  const [reviewerNotes, setReviewerNotes] = useState('Identity documents match registered database records.');
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifySuccess, setVerifySuccess] = useState<string | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  // Restore Transfer Access Dialog State
  const [isRestoreModalOpen, setIsRestoreModalOpen] = useState(false);
  const [restoreReason, setRestoreReason] = useState('National ID verified by compliance. Transfer access restored.');
  const [isRestoring, setIsRestoring] = useState(false);
  const [restoreSuccess, setRestoreSuccess] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  // Image zoom modal
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch all cases without restrictive server status filtering so global StatCards stay accurate
  const fetchAllCases = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const res = await api.getAdminSupportCases({ status: 'ALL' });
      const items: SupportTicketItem[] = Array.isArray(res) ? res : res.items || [];
      setAllCases(items);

      if (selectedCase) {
        const selId = selectedCase.id || selectedCase.ticket_number;
        const updated = items.find((c: any) => (c.id || c.ticket_number) === selId);
        if (updated) setSelectedCase(updated);
      }
    } catch (err) {
      console.error('Failed to load support cases', err);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllCases(true);
  }, []);

  // Polling for live chat updates every 3.5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchAllCases(false);
    }, 3500);
    return () => clearInterval(interval);
  }, [selectedCase?.id, selectedCase?.ticket_number]);

  // Compute Global Counts from allCases
  const metrics = useMemo(() => {
    const openCount = allCases.filter((c) => c.status !== 'RESOLVED' && c.status !== 'CLOSED').length;
    const idvCount = allCases.filter(
      (c) =>
        c.issue_type === 'TRANSFER_BLOCKED' ||
        c.has_pending_id_verification ||
        Boolean(c.identity_verification) ||
        (c.identity_verifications && c.identity_verifications.length > 0)
    ).length;
    const resolvedCount = allCases.filter((c) => c.status === 'RESOLVED' || c.status === 'CLOSED').length;
    const totalCount = allCases.length;

    return { openCount, idvCount, resolvedCount, totalCount };
  }, [allCases]);

  // Filtered cases for dual-pane list
  const displayedCases = useMemo(() => {
    return allCases.filter((c) => {
      // 1. Tab filter
      if (activeTab === 'UNSOLVED') {
        if (c.status === 'RESOLVED' || c.status === 'CLOSED') return false;
      } else if (activeTab === 'PENDING_ID') {
        const hasId =
          c.issue_type === 'TRANSFER_BLOCKED' ||
          c.has_pending_id_verification ||
          Boolean(c.identity_verification) ||
          (c.identity_verifications && c.identity_verifications.length > 0);
        if (!hasId) return false;
      } else if (activeTab === 'RESOLVED') {
        if (c.status !== 'RESOLVED' && c.status !== 'CLOSED') return false;
      }

      // 2. Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchNumber = c.ticket_number?.toLowerCase().includes(q) || c.ticket_id?.toLowerCase().includes(q);
        const matchSubject = c.subject?.toLowerCase().includes(q);
        const matchCustomer = c.customer_name?.toLowerCase().includes(q) || c.customer?.name?.toLowerCase().includes(q);
        const matchUserNo = c.omerta_user_number?.toLowerCase().includes(q) || c.customer?.omerta_user_number?.toLowerCase().includes(q);
        const matchNatId = c.national_id_number?.toLowerCase().includes(q) || c.customer?.national_id_number?.toLowerCase().includes(q);
        const matchDesc = c.description?.toLowerCase().includes(q);
        if (!matchNumber && !matchSubject && !matchCustomer && !matchUserNo && !matchNatId && !matchDesc) {
          return false;
        }
      }

      return true;
    });
  }, [allCases, activeTab, searchQuery]);

  // Sync selected case when displayedCases change
  useEffect(() => {
    if (displayedCases.length > 0) {
      if (!selectedCase) {
        setSelectedCase(displayedCases[0]);
      } else {
        const selId = selectedCase.id || selectedCase.ticket_number;
        const matching = displayedCases.find((c) => (c.id || c.ticket_number) === selId);
        if (matching) {
          setSelectedCase(matching);
        } else {
          setSelectedCase(displayedCases[0]);
        }
      }
    } else {
      setSelectedCase(null);
    }
  }, [displayedCases]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [selectedCase?.messages?.length]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!staffMessage.trim() && staffAttachments.length === 0) || !selectedCase) return;

    const tId = selectedCase.id || selectedCase.ticket_number;
    setIsSending(true);
    try {
      const joinedUrls = staffAttachments.map((a) => a.url).join('|||');
      const joinedNames = staffAttachments.map((a) => a.name).join('|||');

      await api.adminSendSupportMessage(tId, {
        message_text: staffMessage.trim() || '(Evidence attachment provided by Compliance)',
        attachment_url: joinedUrls || undefined,
        attachment_name: joinedNames || undefined,
        attachment_type: staffAttachments.length > 0 ? 'IMAGE' : 'NONE',
      });
      setStaffMessage('');
      setStaffAttachments([]);
      fetchAllCases(false);
    } catch (err: any) {
      alert(err.message || 'Failed to send compliance response message.');
    } finally {
      setIsSending(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.type.startsWith('image/')) {
        const compressed = await compressImageFile(file);
        if (compressed) {
          setStaffAttachments((prev) => [...prev, { url: compressed, name: file.name }]);
        }
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleVerifyIdentity = async (decision: 'VERIFIED' | 'REJECTED') => {
    if (!selectedCase) return;
    const tId = selectedCase.id || selectedCase.ticket_number;
    setIsVerifying(true);
    setVerifySuccess(null);
    setVerifyError(null);

    try {
      await api.adminVerifyIdentityDecision(tId, {
        decision,
        reviewer_notes: reviewerNotes,
      });
      setVerifySuccess(`National ID document verification ${decision.toLowerCase()} successfully.`);
      setTimeout(() => setVerifySuccess(null), 4000);
      fetchAllCases(false);
    } catch (err: any) {
      setVerifyError(err.message || 'Failed to submit identity verification decision.');
      setTimeout(() => setVerifyError(null), 4000);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleRestoreTransfers = async () => {
    if (!selectedCase) return;
    const tId = selectedCase.id || selectedCase.ticket_number;
    setIsRestoring(true);
    setRestoreSuccess(null);
    setRestoreError(null);

    try {
      await api.adminRestoreTransferAccess(tId, {
        confirmation: true,
        reason: restoreReason,
      });
      setRestoreSuccess('Customer transfer access has been restored and security lockout unlocked!');
      setTimeout(() => {
        setIsRestoreModalOpen(false);
        setRestoreSuccess(null);
        fetchAllCases(false);
      }, 1400);
    } catch (err: any) {
      setRestoreError(err.message || 'Failed to restore transfer access.');
    } finally {
      setIsRestoring(false);
    }
  };

  const handleResolveCase = async (status: 'RESOLVED' | 'CLOSED' | 'OPEN') => {
    if (!selectedCase) return;
    const tId = selectedCase.id || selectedCase.ticket_number;
    try {
      await api.adminUpdateTicketStatus(tId, { status });
      fetchAllCases(false);
    } catch (err: any) {
      alert(err.message || 'Failed to update case status.');
    }
  };

  // Resolve ID documents & data from selectedCase
  const latestIdv =
    selectedCase?.identity_verifications && selectedCase.identity_verifications.length > 0
      ? selectedCase.identity_verifications[selectedCase.identity_verifications.length - 1]
      : selectedCase?.identity_verification;

  const hasIdDoc = Boolean(
    latestIdv?.document_front_url ||
      selectedCase?.issue_type === 'TRANSFER_BLOCKED' ||
      selectedCase?.transfer_blocked ||
      (selectedCase?.identity_verifications && selectedCase.identity_verifications.length > 0)
  );

  const idFrontUrl = latestIdv?.document_front_url;
  const idBackUrl = latestIdv?.document_back_url;
  const nationalIdNum =
    latestIdv?.national_id_number || selectedCase?.national_id_number || selectedCase?.customer?.national_id_number;
  const idStatus = latestIdv?.verification_status || latestIdv?.status || selectedCase?.identity_status || 'PENDING_REVIEW';
  const isTransferBlocked =
    selectedCase?.transfer_blocked ||
    selectedCase?.customer?.transfer_status === 'BLOCKED' ||
    selectedCase?.issue_type === 'TRANSFER_BLOCKED';

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header Banner */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-[#E0DDD6]">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <LifeBuoy className="w-4 h-4" />
            Case Management Center
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Cases &amp; Customer Investigations
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Review identity documents, customer support inquiries, live dialog, and restore transfer permissions.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={() => fetchAllCases(true)}
            variant="primary"
            size="sm"
            leftIcon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />}
            className="shadow-sm"
          >
            Refresh Feed
          </Button>
        </div>
      </Card>

      {/* KPI Cards: Always Display Global Platform Counts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Open Cases"
          value={metrics.openCount}
          subtitle="Pending staff action"
          icon={LifeBuoy}
          variant="gold"
          onClick={() => setActiveTab('UNSOLVED')}
          className={`cursor-pointer transition-all duration-150 ${activeTab === 'UNSOLVED' ? 'ring-2 ring-[#F9A825] shadow-md' : 'hover:border-[#F9A825]'}`}
        />
        <StatCard
          title="ID Verifications"
          value={metrics.idvCount}
          subtitle="Document proof awaiting check"
          icon={ShieldCheck}
          variant="sapphire"
          onClick={() => setActiveTab('PENDING_ID')}
          className={`cursor-pointer transition-all duration-150 ${activeTab === 'PENDING_ID' ? 'ring-2 ring-[#002D72] shadow-md' : 'hover:border-[#002D72]'}`}
        />
        <StatCard
          title="Resolved Cases"
          value={metrics.resolvedCount}
          subtitle="Compliance approved & settled"
          icon={CheckCircle2}
          variant="emerald"
          onClick={() => setActiveTab('RESOLVED')}
          className={`cursor-pointer transition-all duration-150 ${activeTab === 'RESOLVED' ? 'ring-2 ring-[#10B981] shadow-md' : 'hover:border-[#10B981]'}`}
        />
        <StatCard
          title="Total Tickets"
          value={metrics.totalCount}
          subtitle="Cumulative inquiries"
          icon={FileText}
          variant="sapphire"
          onClick={() => setActiveTab('ALL')}
          className={`cursor-pointer transition-all duration-150 ${activeTab === 'ALL' ? 'ring-2 ring-[#002D72] shadow-md' : 'hover:border-[#002D72]'}`}
        />
      </div>

      {/* Dual Pane: Cases List + Case Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: CASES LIST (5 Cols) */}
        <Card className="lg:col-span-5 flex flex-col h-[760px] overflow-hidden bg-white border border-[#E0DDD6]">
          <div className="p-4 border-b border-[#E0DDD6] space-y-3 bg-[#F4F1EC]/40">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search case #, customer, ID, subject..."
              leftIcon={<Search className="w-4 h-4 text-[#64748B]" />}
              className="h-9 text-xs bg-white"
            />

            <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
              {[
                { id: 'UNSOLVED', label: 'Unsolved', count: metrics.openCount },
                { id: 'PENDING_ID', label: 'ID Reviews', count: metrics.idvCount },
                { id: 'RESOLVED', label: 'Resolved', count: metrics.resolvedCount },
                { id: 'ALL', label: 'All Cases', count: metrics.totalCount },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-3 py-1.5 rounded-[8px] text-xs font-bold whitespace-nowrap transition-all cursor-pointer flex items-center gap-1.5 ${
                    activeTab === tab.id
                      ? 'bg-[#002D72] text-white shadow-xs'
                      : 'bg-white text-[#64748B] hover:text-[#002D72] border border-[#E0DDD6]'
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                      activeTab === tab.id ? 'bg-[#F9A825] text-[#002D72] font-black' : 'bg-[#E2E8F0] text-[#475569]'
                    }`}
                  >
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-[#E0DDD6]">
            {displayedCases.length > 0 ? (
              displayedCases.map((c) => {
                const isSelected = (selectedCase?.id || selectedCase?.ticket_number) === (c.id || c.ticket_number);
                const hasId =
                  c.issue_type === 'TRANSFER_BLOCKED' ||
                  c.has_pending_id_verification ||
                  Boolean(c.identity_verification) ||
                  (c.identity_verifications && c.identity_verifications.length > 0);
                const isBlocked = c.transfer_blocked || c.customer?.transfer_status === 'BLOCKED' || c.issue_type === 'TRANSFER_BLOCKED';

                return (
                  <div
                    key={c.id || c.ticket_number}
                    onClick={() => setSelectedCase(c)}
                    className={`p-4 transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-[#FFF9E6] border-l-4 border-l-[#F9A825]'
                        : 'hover:bg-[#F9F8F6]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-[#002D72] text-xs">
                          #{c.ticket_number || c.ticket_id}
                        </span>
                        {isBlocked && (
                          <span className="px-1.5 py-0.5 rounded bg-rose-50 border border-rose-200 text-rose-700 text-[10px] font-bold">
                            Blocked
                          </span>
                        )}
                      </div>
                      <StatusBadge status={c.status} />
                    </div>

                    <h4 className="text-xs font-bold text-[#0F172A] truncate mb-1">
                      {c.subject || 'Customer Inquiry'}
                    </h4>

                    <div className="flex items-center justify-between text-[11px] text-[#64748B]">
                      <span className="font-semibold text-[#002D72] truncate max-w-[160px]">
                        {c.customer_name || c.customer?.name || 'Customer'}
                      </span>
                      <span className="font-mono text-[10px]">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString() : 'Recent'}
                      </span>
                    </div>

                    {hasId && (
                      <div className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-[6px] bg-[#EBF3FC] text-[#002D72] text-[10px] font-bold border border-[#BFDBFE]">
                        <ShieldCheck className="w-3 h-3 text-[#10B981]" />
                        <span>ID Submission Included</span>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="p-12 text-center text-xs text-[#64748B] flex flex-col items-center justify-center gap-2">
                <LifeBuoy className="w-8 h-8 text-[#CBD5E1]" />
                <p className="font-semibold text-[#002D72]">
                  {loading ? 'Fetching case tickets...' : 'No cases found for this tab.'}
                </p>
                <p className="text-[11px] text-[#94A3B8]">
                  Try switching to another tab or resetting the search filter.
                </p>
              </div>
            )}
          </div>
        </Card>

        {/* RIGHT COLUMN: ACTIVE CASE WORKSPACE & CHAT (7 Cols) */}
        <Card className="lg:col-span-7 flex flex-col h-[760px] overflow-hidden bg-white border border-[#E0DDD6]">
          {selectedCase ? (
            <>
              {/* Workspace Header */}
              <div className="p-4 sm:p-5 border-b border-[#E0DDD6] flex items-center justify-between gap-3 bg-[#F4F1EC]/50">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono font-bold text-[#002D72]">
                      #{selectedCase.ticket_number || selectedCase.ticket_id}
                    </span>
                    <StatusBadge status={selectedCase.status} />
                    <span className="px-2 py-0.5 rounded-[6px] bg-[#E2E8F0] text-[#334155] font-bold text-[10px] uppercase">
                      {selectedCase.priority || 'HIGH'}
                    </span>
                    {isTransferBlocked && (
                      <span className="px-2 py-0.5 rounded-[6px] bg-rose-100 text-rose-800 font-bold text-[10px] uppercase border border-rose-200">
                        Transfer Hold Active
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-bold text-[#002D72]">
                    {selectedCase.subject}
                  </h3>
                  <p className="text-xs text-[#64748B]">
                    Customer:{' '}
                    <span className="font-semibold text-[#0F172A]">
                      {selectedCase.customer_name || selectedCase.customer?.name}
                    </span>{' '}
                    (
                    <span className="font-mono font-medium text-[#002D72]">
                      {selectedCase.omerta_user_number || selectedCase.customer?.omerta_user_number || selectedCase.customer_id}
                    </span>
                    )
                    {selectedCase.customer?.email && (
                      <span className="ml-2 text-[#94A3B8]">· {selectedCase.customer.email}</span>
                    )}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {canRestoreTransfer && (
                    <Button
                      onClick={() => setIsRestoreModalOpen(true)}
                      variant="primary"
                      size="sm"
                      className="text-xs h-8 px-3 shadow-xs"
                    >
                      <Unlock className="w-3.5 h-3.5 mr-1" />
                      <span>Unlock Transfers</span>
                    </Button>
                  )}
                  {selectedCase.status !== 'RESOLVED' && selectedCase.status !== 'CLOSED' ? (
                    <Button
                      onClick={() => handleResolveCase('RESOLVED')}
                      variant="emerald"
                      size="sm"
                      className="text-xs h-8 px-3"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                      <span>Resolve</span>
                    </Button>
                  ) : (
                    <Button
                      onClick={() => handleResolveCase('OPEN')}
                      variant="secondary"
                      size="sm"
                      className="text-xs h-8 px-3"
                    >
                      <RotateCcw className="w-3.5 h-3.5 mr-1" />
                      <span>Reopen</span>
                    </Button>
                  )}
                </div>
              </div>

              {/* ID Verification Panel (If customer submitted documents or transfer blocked) */}
              {hasIdDoc && (
                <div className="p-4 bg-[#FFF9E6] border-b border-[#FFE082] space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-[#002D72]" />
                      <span className="text-xs font-bold text-[#002D72] uppercase tracking-wider">
                        Identity Verification Documents
                      </span>
                      {nationalIdNum && (
                        <span className="font-mono text-xs font-semibold text-[#64748B]">
                          ID: {nationalIdNum}
                        </span>
                      )}
                    </div>
                    <StatusBadge status={idStatus} />
                  </div>

                  {verifySuccess && (
                    <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-300 text-xs font-bold text-emerald-800 flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-600" />
                      <span>{verifySuccess}</span>
                    </div>
                  )}

                  {verifyError && (
                    <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-300 text-xs font-bold text-rose-800 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-600" />
                      <span>{verifyError}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    {idFrontUrl ? (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[10px] font-bold uppercase text-[#64748B]">
                          <span>National ID (Front)</span>
                          <span className="text-[#002D72] cursor-pointer hover:underline" onClick={() => setZoomedImage(idFrontUrl)}>
                            Enlarge
                          </span>
                        </div>
                        <img
                          src={idFrontUrl}
                          alt="ID Front"
                          onClick={() => setZoomedImage(idFrontUrl)}
                          className="h-24 w-full object-cover rounded-[8px] border border-[#E0DDD6] cursor-pointer hover:opacity-95 shadow-xs transition-opacity"
                        />
                      </div>
                    ) : (
                      <div className="p-4 rounded-lg bg-white/70 border border-amber-200 text-xs text-amber-900 font-medium flex items-center justify-center">
                        Front document awaiting upload
                      </div>
                    )}

                    {idBackUrl ? (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[10px] font-bold uppercase text-[#64748B]">
                          <span>National ID (Back)</span>
                          <span className="text-[#002D72] cursor-pointer hover:underline" onClick={() => setZoomedImage(idBackUrl)}>
                            Enlarge
                          </span>
                        </div>
                        <img
                          src={idBackUrl}
                          alt="ID Back"
                          onClick={() => setZoomedImage(idBackUrl)}
                          className="h-24 w-full object-cover rounded-[8px] border border-[#E0DDD6] cursor-pointer hover:opacity-95 shadow-xs transition-opacity"
                        />
                      </div>
                    ) : (
                      <div className="p-4 rounded-lg bg-white/70 border border-amber-200 text-xs text-amber-900 font-medium flex items-center justify-center">
                        Back document optional/pending
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-1">
                    <Button
                      onClick={() => handleVerifyIdentity('REJECTED')}
                      variant="danger"
                      size="sm"
                      disabled={isVerifying}
                      className="h-7.5 text-xs px-3"
                    >
                      <X className="w-3.5 h-3.5 mr-1" />
                      <span>Reject ID</span>
                    </Button>
                    <Button
                      onClick={() => handleVerifyIdentity('VERIFIED')}
                      variant="emerald"
                      size="sm"
                      disabled={isVerifying}
                      className="h-7.5 text-xs px-3 shadow-xs"
                    >
                      <Check className="w-3.5 h-3.5 mr-1" />
                      <span>Approve ID Document</span>
                    </Button>
                  </div>
                </div>
              )}

              {/* Chat Thread Messages */}
              <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-3.5 bg-[#FAF9F6]">
                {selectedCase.messages && selectedCase.messages.length > 0 ? (
                  selectedCase.messages.map((m) => {
                    const isStaff = m.sender_role !== 'CUSTOMER';
                    const imageUrls = m.attachment_url?.split('|||').filter(Boolean) || [];

                    return (
                      <div
                        key={m.id || m.message_id}
                        className={`flex flex-col ${isStaff ? 'items-end' : 'items-start'}`}
                      >
                        <div className="flex items-center gap-1.5 mb-0.5 text-[10px] text-[#64748B]">
                          <span className="font-bold text-[#002D72]">
                            {isStaff ? (m.sender_name || 'Compliance Officer') : (selectedCase.customer_name || 'Customer')}
                          </span>
                          <span>•</span>
                          <span className="font-mono">
                            {m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                          </span>
                        </div>

                        <div
                          className={`p-3 rounded-[12px] max-w-md text-xs leading-relaxed ${
                            isStaff
                              ? 'bg-[#002D72] text-white rounded-br-none shadow-sm'
                              : 'bg-white text-[#0F172A] rounded-bl-none border border-[#E0DDD6] shadow-xs'
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{m.message_text}</p>

                          {/* Attachments */}
                          {imageUrls.length > 0 && (
                            <div className="mt-2 grid grid-cols-2 gap-2 pt-2 border-t border-white/20">
                              {imageUrls.map((att: string, idx: number) => (
                                <img
                                  key={idx}
                                  src={att}
                                  alt="Attachment"
                                  onClick={() => setZoomedImage(att)}
                                  className="h-16 w-full object-cover rounded-[6px] cursor-pointer hover:opacity-90 transition-opacity"
                                />
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="py-12 text-center text-xs text-[#64748B] flex flex-col items-center justify-center gap-2">
                    <LifeBuoy className="w-8 h-8 text-[#CBD5E1]" />
                    <p className="font-semibold text-[#002D72]">Initial Case Opened</p>
                    <p className="text-[11px] text-[#94A3B8] max-w-xs">
                      {selectedCase.description || 'No additional message text provided.'}
                    </p>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>

              {/* Chat Input Bar */}
              <form onSubmit={handleSendMessage} className="p-3 border-t border-[#E0DDD6] bg-[#F4F1EC]/60 space-y-2">
                {/* Pending Attachments preview */}
                {staffAttachments.length > 0 && (
                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                    {staffAttachments.map((att, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-1.5 px-2 py-1 rounded-[6px] bg-white border border-[#E0DDD6] text-[11px]"
                      >
                        <span className="truncate max-w-[100px] text-[#002D72] font-medium">{att.name}</span>
                        <button
                          type="button"
                          onClick={() => setStaffAttachments((prev) => prev.filter((_, i) => i !== idx))}
                          className="text-rose-600 hover:text-rose-800 cursor-pointer"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept="image/*"
                    multiple
                    className="hidden"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    className="h-10 px-2.5 text-[#64748B] hover:text-[#002D72]"
                    title="Attach image evidence"
                  >
                    <Paperclip className="w-4 h-4" />
                  </Button>

                  <Input
                    value={staffMessage}
                    onChange={(e) => setStaffMessage(e.target.value)}
                    placeholder="Type official compliance response to customer..."
                    className="h-10 text-xs flex-1 bg-white"
                  />

                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={isSending || (!staffMessage.trim() && staffAttachments.length === 0)}
                    className="h-10 px-4 shadow-sm"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </form>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-[#64748B]">
              <LifeBuoy className="w-12 h-12 text-[#CBD5E1] mb-2" />
              <p className="font-bold text-[#002D72] text-sm">Select a Case from the List</p>
              <p className="text-xs text-[#64748B] max-w-sm mt-1">
                View customer support inquiries, inspect uploaded verification documents, or send live compliance responses.
              </p>
            </div>
          )}
        </Card>
      </div>

      {/* MODAL 1: RESTORE TRANSFER PRIVILEGES */}
      {isRestoreModalOpen && selectedCase && (
        <Modal
          isOpen={isRestoreModalOpen}
          onClose={() => setIsRestoreModalOpen(false)}
          title="Restore Transfer Privileges"
          subtitle={`Customer: ${selectedCase.customer_name || selectedCase.customer?.name} (${selectedCase.omerta_user_number || selectedCase.customer?.omerta_user_number || selectedCase.customer_id})`}
          maxWidth="md"
        >
          <div className="space-y-4 text-xs">
            {restoreSuccess && (
              <div className="p-3 bg-[#ECFDF5] border border-[#A7F3D0] rounded-[10px] text-[#065F46] flex items-center gap-2">
                <Check className="w-4 h-4 text-[#10B981]" />
                <span className="font-semibold">{restoreSuccess}</span>
              </div>
            )}
            {restoreError && (
              <div className="p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-[10px] text-[#991B1B]">
                {restoreError}
              </div>
            )}

            <div className="p-3.5 rounded-[10px] bg-[#EBF3FC] border border-[#BFDBFE] text-[#002D72] flex items-start gap-2.5">
              <ShieldCheck className="w-5 h-5 text-[#002D72] shrink-0 mt-0.5" />
              <p className="text-xs leading-relaxed text-[#475569]">
                This action unlocks the customer account, resets security holds, and flags their portal to set a new Transfer Password.
              </p>
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#475569]">
                Audit Reason &amp; Authorization
              </label>
              <textarea
                rows={3}
                value={restoreReason}
                onChange={(e) => setRestoreReason(e.target.value)}
                className="w-full bg-white border border-[#E0DDD6] rounded-[10px] p-3 text-xs text-[#0F172A] outline-none focus:border-[#1E88E5]"
                required
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setIsRestoreModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={handleRestoreTransfers}
                isLoading={isRestoring}
              >
                <Unlock className="w-4 h-4 mr-1.5" />
                <span>Confirm Restoration</span>
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 2: IMAGE ZOOM */}
      {zoomedImage && (
        <Modal
          isOpen={Boolean(zoomedImage)}
          onClose={() => setZoomedImage(null)}
          title="Document Inspection Viewer"
          maxWidth="4xl"
        >
          <div className="flex justify-center p-2">
            <img
              src={zoomedImage}
              alt="Enlarged Document"
              className="max-h-[75vh] w-auto rounded-[10px] shadow-lg object-contain"
            />
          </div>
        </Modal>
      )}
    </div>
  );
};
