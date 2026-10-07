import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  LifeBuoy,
  Plus,
  Send,
  Paperclip,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Upload,
  FileText,
  CheckCircle2,
  RefreshCw,
  HelpCircle,
  Eye,
  Check,
  ArrowRight,
  Shield,
  X,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import {
  Card,
  Button,
  Input,
  Select,
  StatusBadge,
  Modal,
  Alert,
} from '../../components/ui';
import type { SupportTicketItem, SupportMessageItem } from '../../types';

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

export const CustomerSupportPage: React.FC = () => {
  const { customer, user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [tickets, setTickets] = useState<SupportTicketItem[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<SupportTicketItem | null>(null);
  const [ticketTab, setTicketTab] = useState<'UNSOLVED' | 'SOLVED'>('UNSOLVED');
  const [isSending, setIsSending] = useState(false);
  const [messageText, setMessageText] = useState('');

  // New Ticket Modal State
  const [isNewTicketModalOpen, setIsNewTicketModalOpen] = useState(false);
  const [newTicketData, setNewTicketData] = useState({
    issue_type: searchParams.get('reason') === 'TRANSFER_BLOCKED' ? 'TRANSFER_BLOCKED' : 'FORGOTTEN_TRANSFER_PASSWORD',
    subject: searchParams.get('reason') === 'TRANSFER_BLOCKED' ? 'Transfer Password Blocked — Requesting Identity Verification' : 'Forgotten Transfer Password — Identity Verification & Reset Request',
    description: searchParams.get('reason') === 'TRANSFER_BLOCKED'
      ? 'I entered my transfer password incorrectly 3 times. Please review my submitted National ID and restore my money transfer privileges.'
      : 'I have forgotten my transfer password and cannot send money. Please verify my National ID to allow me to set a new transfer password and restore transfer privileges.',
    priority: 'HIGH',
  });
  const [modalIdFront, setModalIdFront] = useState<string | null>(null);
  const [modalIdBack, setModalIdBack] = useState<string | null>(null);
  const [modalNationalId, setModalNationalId] = useState<string>('');
  const [newTicketLoading, setNewTicketLoading] = useState(false);
  const [newTicketError, setNewTicketError] = useState<string | null>(null);

  // Identity Upload Section State
  const [idFrontPreview, setIdFrontPreview] = useState<string | null>(null);
  const [idBackPreview, setIdBackPreview] = useState<string | null>(null);
  const [nationalIdInput, setNationalIdInput] = useState<string>('');
  const [idUploading, setIdUploading] = useState(false);
  const [idUploadSuccess, setIdUploadSuccess] = useState(false);
  const [idUploadError, setIdUploadError] = useState<string | null>(null);

  // Multi-Attachment for chat messages
  const [chatAttachments, setChatAttachments] = useState<{ url: string; name: string }[]>([]);

  // Zoomed image modal
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);

  // Chat scroll anchor
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const fetchTickets = async (autoSelectId?: number | string) => {
    try {
      const res = await api.getCustomerSupportTickets();
      setTickets(res);
      if (res.length > 0) {
        if (autoSelectId) {
          const found = res.find((t: any) => t.id === autoSelectId || t.ticket_id === autoSelectId || t.ticket_number === autoSelectId);
          if (found) {
            setSelectedTicket(found);
            await fetchSelectedTicketDetails(found.id || found.ticket_id || found.ticket_number);
          }
        } else if (!selectedTicket) {
          const firstUnsolved = res.find((t: any) => t.status !== 'RESOLVED' && t.status !== 'CLOSED');
          const toSelect = firstUnsolved || res[0];
          setSelectedTicket(toSelect);
          await fetchSelectedTicketDetails(toSelect.id || toSelect.ticket_id || toSelect.ticket_number);
        } else {
          const refreshed = res.find((t: any) => t.id === selectedTicket.id || t.ticket_id === (selectedTicket.ticket_id || selectedTicket.id));
          if (refreshed) {
            setSelectedTicket(refreshed);
          }
        }
      }
    } catch {
      // Fallback
    }
  };

  const fetchSelectedTicketDetails = async (ticketId: number | string) => {
    if (!ticketId || ticketId === 'undefined') return;
    try {
      const ticket = await api.getCustomerSupportTicket(ticketId);
      setSelectedTicket(ticket);
    } catch {
      // Silent error during polling
    }
  };

  const handleSelectTicket = async (ticket: SupportTicketItem) => {
    setSelectedTicket(ticket);
    const tId = ticket.id || (ticket as any).ticket_id || ticket.ticket_number;
    if (tId && tId !== 'undefined') {
      await fetchSelectedTicketDetails(tId);
    }
  };

  useEffect(() => {
    fetchTickets();
    if (searchParams.get('reason') === 'TRANSFER_BLOCKED') {
      setIsNewTicketModalOpen(true);
    }
  }, []);

  useEffect(() => {
    const tId = selectedTicket?.id || (selectedTicket as any)?.ticket_id || selectedTicket?.ticket_number;
    if (!tId || tId === 'undefined') return;
    const interval = setInterval(() => {
      fetchSelectedTicketDetails(tId);
    }, 4000);
    return () => clearInterval(interval);
  }, [selectedTicket?.id, (selectedTicket as any)?.ticket_id, selectedTicket?.ticket_number]);

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    setNewTicketError(null);
    if (!newTicketData.subject.trim() || !newTicketData.description.trim()) {
      setNewTicketError('Subject and description are required.');
      return;
    }

    setNewTicketLoading(true);
    try {
      const res = await api.createSupportTicket({
        issue_type: newTicketData.issue_type,
        subject: newTicketData.subject,
        description: newTicketData.description,
        priority: newTicketData.priority,
      });

      const newTicketId = res.id || res.ticket_id || res.ticket_number;

      if (modalIdFront && newTicketId) {
        try {
          const natId = (modalNationalId.trim() || customer?.national_id_number || '29801011234567').replace(/[^0-9]/g, '');
          await api.uploadSupportIdDocument(newTicketId, {
            national_id_number: natId.length >= 6 ? natId : (customer?.national_id_number || '29801011234567'),
            document_type: 'NATIONAL_ID',
            document_front_url: modalIdFront,
            document_back_url: modalIdBack || undefined,
          });
        } catch {
          // Non-blocking
        }
      }

      setIsNewTicketModalOpen(false);
      setModalIdFront(null);
      setModalIdBack(null);
      setModalNationalId('');
      setNewTicketData({
        issue_type: 'FORGOTTEN_TRANSFER_PASSWORD',
        subject: '',
        description: '',
        priority: 'HIGH',
      });
      setTicketTab('UNSOLVED');
      await fetchTickets(newTicketId);
    } catch (err: any) {
      setNewTicketError(err.message || 'Failed to create support ticket.');
    } finally {
      setNewTicketLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const tId = selectedTicket?.id || (selectedTicket as any)?.ticket_id || selectedTicket?.ticket_number;
    if (!tId || (!messageText.trim() && chatAttachments.length === 0)) return;

    setIsSending(true);
    try {
      const joinedUrls = chatAttachments.map((a) => a.url).join('|||');
      const joinedNames = chatAttachments.map((a) => a.name).join('|||');

      await api.sendSupportMessage(tId, {
        message_text: messageText.trim() || 'Uploaded attachment',
        attachment_url: joinedUrls || undefined,
        attachment_name: joinedNames || undefined,
        attachment_type: chatAttachments.length > 0 ? 'IMAGE' : 'NONE',
      });

      setMessageText('');
      setChatAttachments([]);
      await fetchSelectedTicketDetails(tId);
    } catch (err: any) {
      alert(err.message || 'Failed to send message.');
    } finally {
      setIsSending(false);
    }
  };

  const handleMultiChatFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const newAttachments: { url: string; name: string }[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const compressed = await compressImageFile(file);
      newAttachments.push({ url: compressed, name: file.name });
    }
    setChatAttachments((prev) => [...prev, ...newAttachments]);
  };

  const handleIdPhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>, target: 'front' | 'back') => {
    const file = e.target.files?.[0];
    if (!file) return;

    const compressed = await compressImageFile(file);
    if (target === 'front') {
      setIdFrontPreview(compressed);
    } else if (target === 'back') {
      setIdBackPreview(compressed);
    }
  };

  const handleModalPhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>, target: 'front' | 'back') => {
    const file = e.target.files?.[0];
    if (!file) return;

    const compressed = await compressImageFile(file);
    if (target === 'front') {
      setModalIdFront(compressed);
    } else if (target === 'back') {
      setModalIdBack(compressed);
    }
  };

  const handleUploadIdDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket) return;
    setIdUploadError(null);

    const ticketId = selectedTicket.id || (selectedTicket as any).ticket_id || selectedTicket.ticket_number;
    if (!ticketId || ticketId === 'undefined') {
      setIdUploadError('No valid support ticket selected.');
      return;
    }

    if (!idFrontPreview) {
      setIdUploadError('Please attach a clear photo of the front side of your National ID / Passport.');
      return;
    }

    setIdUploading(true);
    try {
      const natId = (nationalIdInput.trim() || customer?.national_id_number || '29801011234567').replace(/[^0-9]/g, '');
      await api.uploadSupportIdDocument(ticketId, {
        national_id_number: natId.length >= 6 ? natId : (customer?.national_id_number || '29801011234567'),
        document_type: 'NATIONAL_ID',
        document_front_url: idFrontPreview,
        document_back_url: idBackPreview || undefined,
      });

      setIdUploadSuccess(true);
      setTimeout(() => {
        setIdUploadSuccess(false);
      }, 5000);
      await fetchSelectedTicketDetails(ticketId);
      await fetchTickets(ticketId);
    } catch (err: any) {
      setIdUploadError(err.message || 'Failed to submit ID verification.');
    } finally {
      setIdUploading(false);
    }
  };

  const unsolvedTickets = tickets.filter((t) => t.status !== 'RESOLVED' && t.status !== 'CLOSED');
  const solvedTickets = tickets.filter((t) => t.status === 'RESOLVED' || t.status === 'CLOSED');
  const displayedTickets = ticketTab === 'UNSOLVED' ? unsolvedTickets : solvedTickets;

  const handleSwitchTab = (tab: 'UNSOLVED' | 'SOLVED') => {
    setTicketTab(tab);
    const target = tab === 'UNSOLVED' ? unsolvedTickets : solvedTickets;
    if (target.length > 0) {
      handleSelectTicket(target[0]);
    } else {
      setSelectedTicket(null);
    }
  };

  const isCaseResolved = selectedTicket?.status === 'RESOLVED' || selectedTicket?.status === 'CLOSED';

  const renderPhotoGrid = (imageUrls: string[]) => {
    if (imageUrls.length === 0) return null;
    return (
      <div className="p-1.5 grid grid-cols-2 gap-1.5">
        {imageUrls.map((imgUrl, idx) => (
          <div
            key={idx}
            onClick={() => setZoomedImage(imgUrl)}
            className="relative group cursor-pointer overflow-hidden rounded-lg bg-[var(--color-secondary-surface)] border border-[var(--color-border)] h-32 flex items-center justify-center shadow-xs"
          >
            <img
              src={imgUrl}
              alt={`Attachment ${idx + 1}`}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
            />
            <div className="absolute inset-0 bg-[var(--color-sapphire)]/60 opacity-0 group-hover:opacity-100 flex items-center justify-center gap-1 text-white text-xs font-bold transition-opacity">
              <Eye className="w-4 h-4" />
              <span>Zoom</span>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <Card className="p-6 md:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-sapphire)] flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[var(--color-sapphire)] text-[var(--color-gold)] shadow-sm">
              <LifeBuoy className="h-6 w-6 stroke-[2.2]" />
            </div>
            <span>Support &amp; Helpdesk</span>
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2 font-medium">
            Direct dialogue with Compliance Officers for identity verification, transfer recovery, and security reviews.
          </p>
        </div>

        <Button
          type="button"
          onClick={() => {
            setNewTicketError(null);
            setIsNewTicketModalOpen(true);
          }}
          variant="primary"
          size="sm"
          className="self-start sm:self-auto shrink-0"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          <span>New Support Ticket</span>
        </Button>
      </Card>

      {/* Main Support Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[620px]">
        {/* LEFT COLUMN: Segmented Ticket Queue */}
        <Card className="lg:col-span-4 p-0 flex flex-col overflow-hidden">
          {/* Header & Tabs */}
          <div className="p-4 border-b border-[var(--color-border)] space-y-3 bg-[var(--color-secondary-surface)]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-[var(--color-sapphire)]" />
                <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--color-sapphire)]">Your Cases</h2>
              </div>
              <button
                onClick={() => fetchTickets()}
                className="p-1.5 rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-sapphire)] hover:bg-white transition-colors cursor-pointer"
                title="Refresh tickets"
                aria-label="Refresh tickets"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>

            {/* UNSOLVED vs SOLVED Segmented Controls */}
            <div className="grid grid-cols-2 gap-1.5 p-1 rounded-xl bg-white border border-[var(--color-border)]">
              <button
                type="button"
                onClick={() => handleSwitchTab('UNSOLVED')}
                className={`py-2 px-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                  ticketTab === 'UNSOLVED'
                    ? 'bg-[var(--color-sapphire)] text-white shadow-xs'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-sapphire)]'
                }`}
              >
                <span>Active</span>
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${ticketTab === 'UNSOLVED' ? 'bg-white/25 text-white' : 'bg-[var(--color-secondary-surface)] text-[var(--color-text-muted)]'}`}>
                  {unsolvedTickets.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => handleSwitchTab('SOLVED')}
                className={`py-2 px-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                  ticketTab === 'SOLVED'
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-sapphire)]'
                }`}
              >
                <span>Solved</span>
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${ticketTab === 'SOLVED' ? 'bg-white/25 text-white' : 'bg-[var(--color-secondary-surface)] text-[var(--color-text-muted)]'}`}>
                  {solvedTickets.length}
                </span>
              </button>
            </div>
          </div>

          {/* Ticket List Stream */}
          <div className="flex-1 overflow-y-auto divide-y divide-[var(--color-border)] max-h-[560px]">
            {displayedTickets.length === 0 ? (
              <div className="p-10 text-center text-xs text-[var(--color-text-secondary)] space-y-2">
                <HelpCircle className="h-10 w-10 mx-auto text-[var(--color-text-muted)]" />
                <p className="font-medium">
                  {ticketTab === 'UNSOLVED'
                    ? 'No open unsolved tickets. All customer cases are resolved!'
                    : 'No resolved tickets yet.'}
                </p>
                {ticketTab === 'UNSOLVED' && (
                  <button
                    onClick={() => setIsNewTicketModalOpen(true)}
                    className="text-[var(--color-royal-blue)] hover:underline font-bold text-xs cursor-pointer block mx-auto pt-1"
                  >
                    Open a new ticket
                  </button>
                )}
              </div>
            ) : (
              displayedTickets.map((t: SupportTicketItem) => {
                const isSelected = selectedTicket?.id === t.id || selectedTicket?.ticket_number === t.ticket_number;
                const isResolved = t.status === 'RESOLVED' || t.status === 'CLOSED';

                return (
                  <div
                    key={t.id || t.ticket_number}
                    onClick={() => handleSelectTicket(t)}
                    className={`p-4 cursor-pointer transition-all text-xs ${
                      isSelected
                        ? 'bg-blue-50/70 border-l-4 border-l-[var(--color-sapphire)]'
                        : 'hover:bg-[var(--color-hover-surface)]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono font-bold text-[var(--color-sapphire)]">{t.ticket_number}</span>
                      <StatusBadge status={t.status} />
                    </div>

                    <h4 className="font-bold text-[var(--color-text-primary)] line-clamp-1 mb-1">{t.subject}</h4>

                    <div className="flex items-center gap-2 text-[10px] text-[var(--color-text-muted)] mb-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded-full bg-[var(--color-secondary-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] font-medium">
                        {t.issue_type}
                      </span>
                      {t.transfer_blocked && (
                        <span className="px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 font-bold border border-rose-200">
                          Transfer Blocked
                        </span>
                      )}
                      {isResolved && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold border border-emerald-200 flex items-center gap-1">
                          <Check className="w-3 h-3" /> Solved
                        </span>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-[var(--color-text-secondary)] font-medium">
                      <span>{new Date(t.created_at).toLocaleDateString()}</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>

        {/* RIGHT COLUMN: Chat & ID Upload */}
        <Card className="lg:col-span-8 p-0 flex flex-col justify-between overflow-hidden min-h-[620px]">
          {selectedTicket ? (
            <>
              {/* Ticket Top Bar */}
              <div className="p-5 border-b border-[var(--color-border)] bg-[var(--color-secondary-surface)] flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-sm font-extrabold text-[var(--color-sapphire)]">{selectedTicket.ticket_number}</span>
                    <StatusBadge status={selectedTicket.status} />
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white border border-[var(--color-border)] text-[var(--color-text-secondary)]">
                      Priority: {selectedTicket.priority}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">{selectedTicket.subject}</h3>
                </div>

                <div className="flex items-center gap-2.5 text-xs">
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] block">Assigned Staff</span>
                    <span className="font-bold text-[var(--color-sapphire)]">
                      {selectedTicket.assigned_to_name || 'Omerta Compliance Desk'}
                    </span>
                  </div>
                  <div className="w-9 h-9 rounded-xl bg-[var(--color-sapphire)] text-[var(--color-gold)] flex items-center justify-center font-bold shadow-xs">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                </div>
              </div>

              {/* RESOLVED CASE CONGRATULATORY BANNER */}
              {isCaseResolved && (
                <div className="m-4 p-4 rounded-xl bg-emerald-50 border border-emerald-300 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                      <CheckCircle2 className="w-6 h-6 stroke-[2.2]" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-emerald-950">Case Solved &amp; Verified</h4>
                      <p className="text-xs text-emerald-800 font-medium">
                        Compliance officers have verified your identity. Transfer privileges are restored!
                      </p>
                    </div>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="success"
                    onClick={() => navigate('/customer/dashboard')}
                  >
                    <span>Go to Dashboard</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </Button>
                </div>
              )}

              {/* ACTION REQUIRED BANNER: NATIONAL ID VERIFICATION */}
              {!isCaseResolved &&
                (selectedTicket.issue_type === 'TRANSFER_BLOCKED' ||
                  selectedTicket.issue_type === 'FORGOTTEN_TRANSFER_PASSWORD' ||
                  selectedTicket.requires_identity_verification ||
                  selectedTicket.transfer_blocked ||
                  customer?.transfer_status === 'BLOCKED') &&
                selectedTicket.identity_status !== 'VERIFIED' && (
                  <div className="m-4 mb-0 p-4 rounded-xl bg-amber-50 border border-amber-300 flex items-center justify-between gap-3 text-xs">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center shrink-0">
                        <AlertTriangle className="w-5 h-5 stroke-[2.2]" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-amber-950">Action Required: National ID Verification</h4>
                        <p className="text-xs text-amber-900 font-medium">
                          To reset your transfer password and restore sending privileges, upload your National ID in the box below.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

              {/* IDENTITY VERIFICATION UPLOAD BOX */}
              {!isCaseResolved &&
                (selectedTicket.issue_type === 'TRANSFER_BLOCKED' ||
                  selectedTicket.issue_type === 'FORGOTTEN_TRANSFER_PASSWORD' ||
                  selectedTicket.requires_identity_verification ||
                  selectedTicket.transfer_blocked ||
                  customer?.transfer_status === 'BLOCKED') && (
                  <div className="m-4 p-5 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-3">
                    <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4 text-[var(--color-sapphire)]" />
                        <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-sapphire)]">
                          Identity &amp; Ownership Verification
                        </h4>
                      </div>
                      {selectedTicket.identity_status && (
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${selectedTicket.identity_status === 'VERIFIED' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                          ID: {selectedTicket.identity_status}
                        </span>
                      )}
                    </div>

                    <div className="p-3 rounded-lg bg-white border border-[var(--color-border)] text-xs text-[var(--color-text-secondary)] flex items-center gap-2.5 font-medium">
                      <Shield className="w-4 h-4 text-[var(--color-sapphire)] shrink-0" />
                      <span>
                        🔒 <strong>End-to-End Encrypted Verification:</strong> Upload clear photos of your National ID or Passport (Front &amp; Back).
                      </span>
                    </div>

                    {idUploadSuccess ? (
                      <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-xs flex items-center gap-2 font-bold">
                        <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-600" />
                        <span>Identity documents uploaded successfully! Compliance officers will review your submission shortly.</span>
                      </div>
                    ) : (
                      <form onSubmit={handleUploadIdDocument} className="space-y-3 text-xs">
                        {idUploadError && (
                          <Alert
                            variant="danger"
                            icon={<AlertTriangle className="w-4 h-4" />}
                            message={idUploadError}
                          />
                        )}

                        <Input
                          label="National ID Number (14 Digits)"
                          type="text"
                          maxLength={14}
                          value={nationalIdInput}
                          onChange={(e) => setNationalIdInput(e.target.value)}
                          placeholder={customer?.national_id_number || "e.g. 29801011234567"}
                        />

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-end">
                          <div>
                            <label className="block text-[11px] font-bold uppercase text-[var(--color-text-muted)] mb-1">
                              ID / Passport Front {idFrontPreview && '✓'}
                            </label>
                            <label className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white hover:bg-[var(--color-secondary-surface)] border border-[var(--color-border)] rounded-lg text-xs font-bold text-[var(--color-sapphire)] cursor-pointer transition-all min-h-[44px]">
                              <Upload className="w-4 h-4 text-[var(--color-sapphire)]" />
                              <span className="truncate">{idFrontPreview ? 'Front Photo Attached' : 'Attach Front Photo'}</span>
                              <input
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={(e) => handleIdPhotoUpload(e, 'front')}
                              />
                            </label>
                          </div>

                          <div>
                            <label className="block text-[11px] font-bold uppercase text-[var(--color-text-muted)] mb-1">
                              ID / Passport Back {idBackPreview && '✓'}
                            </label>
                            <label className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white hover:bg-[var(--color-secondary-surface)] border border-[var(--color-border)] rounded-lg text-xs font-bold text-[var(--color-sapphire)] cursor-pointer transition-all min-h-[44px]">
                              <Upload className="w-4 h-4 text-[var(--color-sapphire)]" />
                              <span className="truncate">{idBackPreview ? 'Back Photo Attached' : 'Attach Back Photo'}</span>
                              <input
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={(e) => handleIdPhotoUpload(e, 'back')}
                              />
                            </label>
                          </div>
                        </div>

                        {(idFrontPreview || idBackPreview) && (
                          <div className="flex items-center gap-4 pt-1">
                            {idFrontPreview && (
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-bold text-[var(--color-text-muted)]">Front:</span>
                                <img
                                  src={idFrontPreview}
                                  alt="Front Preview"
                                  onClick={() => setZoomedImage(idFrontPreview)}
                                  className="h-14 w-22 object-cover rounded-lg border border-[var(--color-border)] shadow-xs cursor-pointer hover:scale-105 transition-transform"
                                />
                              </div>
                            )}
                            {idBackPreview && (
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-bold text-[var(--color-text-muted)]">Back:</span>
                                <img
                                  src={idBackPreview}
                                  alt="Back Preview"
                                  onClick={() => setZoomedImage(idBackPreview)}
                                  className="h-14 w-22 object-cover rounded-lg border border-[var(--color-border)] shadow-xs cursor-pointer hover:scale-105 transition-transform"
                                />
                              </div>
                            )}
                          </div>
                        )}

                        <Button
                          type="submit"
                          variant="primary"
                          size="default"
                          disabled={idUploading || !idFrontPreview}
                          isLoading={idUploading}
                          className="w-full mt-2"
                        >
                          <ShieldCheck className="w-4 h-4 mr-1.5" />
                          <span>Submit ID Verification to Compliance</span>
                        </Button>
                      </form>
                    )}
                  </div>
                )}

              {/* Chat Message Stream */}
              <div className="flex-1 p-5 overflow-y-auto space-y-3.5 bg-[var(--color-hover-surface)] max-h-[420px]">
                {(!selectedTicket.messages || selectedTicket.messages.length === 0) && selectedTicket.description && (
                  <div className="flex justify-end items-end gap-2.5">
                    <div className="max-w-md rounded-2xl rounded-tr-sm bg-[var(--color-sapphire)] text-white p-4 shadow-sm space-y-1">
                      <div className="flex items-center justify-between gap-2 text-[10px] font-bold opacity-90">
                        <span>You (Inquiry)</span>
                        <span className="font-mono text-[9px]">
                          {new Date(selectedTicket.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-white leading-relaxed whitespace-pre-wrap text-xs font-medium">{selectedTicket.description}</p>
                    </div>

                    <div className="w-8 h-8 rounded-lg bg-[var(--color-sapphire)] text-[var(--color-gold)] font-bold text-xs flex items-center justify-center shrink-0 shadow-xs">
                      {customer?.name?.charAt(0) || user?.full_name?.charAt(0) || 'U'}
                    </div>
                  </div>
                )}

                {selectedTicket.messages?.map((msg: SupportMessageItem) => {
                  const isMe = msg.sender_role === 'CUSTOMER';
                  const isSystem = msg.sender_role === 'SYSTEM';

                  if (isSystem) {
                    return (
                      <div key={msg.id} className="flex justify-center my-2">
                        <div className="px-4 py-1.5 rounded-full bg-white border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text-secondary)] flex items-center gap-2 shadow-xs">
                          <ShieldCheck className="w-4 h-4 text-[var(--color-sapphire)]" />
                          <span>{msg.message_text}</span>
                        </div>
                      </div>
                    );
                  }

                  const imageUrls = msg.attachment_url?.split('|||').filter(Boolean) || [];

                  return (
                    <div
                      key={msg.id}
                      className={`flex items-end gap-2.5 ${isMe ? 'justify-end' : 'justify-start'}`}
                    >
                      {!isMe && (
                        <div className="w-8 h-8 rounded-lg bg-white border border-[var(--color-border)] text-[var(--color-sapphire)] flex items-center justify-center shrink-0 shadow-xs">
                          <ShieldCheck className="w-4 h-4 text-[var(--color-sapphire)]" />
                        </div>
                      )}

                      <div
                        className={`max-w-md rounded-2xl text-xs shadow-xs transition-all overflow-hidden ${
                          isMe
                            ? 'rounded-tr-sm bg-[var(--color-sapphire)] text-white'
                            : 'rounded-tl-sm bg-white text-[var(--color-text-primary)] border border-[var(--color-border)]'
                        }`}
                      >
                        <div className="px-4 pt-3 pb-1 flex items-center justify-between gap-3 text-[10px]">
                          <span className="font-bold flex items-center gap-1">
                            {!isMe && <ShieldCheck className="w-3.5 h-3.5 text-[var(--color-sapphire)]" />}
                            {msg.sender_name} {!isMe && `[${msg.sender_role}]`}
                          </span>
                          <span className="opacity-75 text-[9px] font-mono">
                            {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>

                        <p className={`px-4 py-2 leading-relaxed whitespace-pre-wrap font-medium ${isMe ? 'text-white' : 'text-[var(--color-text-primary)]'}`}>
                          {msg.message_text}
                        </p>

                        {imageUrls.length > 0 && renderPhotoGrid(imageUrls)}
                      </div>

                      {isMe && (
                        <div className="w-8 h-8 rounded-lg bg-[var(--color-sapphire)] text-[var(--color-gold)] font-bold text-xs flex items-center justify-center shrink-0 shadow-xs">
                          {customer?.name?.charAt(0) || user?.full_name?.charAt(0) || 'U'}
                        </div>
                      )}
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input Bar */}
              {!isCaseResolved ? (
                <form onSubmit={handleSendMessage} className="p-3.5 border-t border-[var(--color-border)] bg-white space-y-2">
                  {/* Chat File Attachment Chips */}
                  {chatAttachments.length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap pb-1">
                      {chatAttachments.map((att, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[var(--color-secondary-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] font-medium"
                        >
                          <Paperclip className="w-3 h-3 text-[var(--color-sapphire)]" />
                          <span className="max-w-[120px] truncate">{att.name}</span>
                          <button
                            type="button"
                            onClick={() => setChatAttachments((prev) => prev.filter((_, i) => i !== idx))}
                            className="p-0.5 hover:text-rose-600 cursor-pointer"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    <label className="p-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-secondary-surface)] hover:bg-[var(--color-border)]/50 text-[var(--color-sapphire)] cursor-pointer transition-all">
                      <Paperclip className="w-4 h-4" />
                      <input
                        type="file"
                        multiple
                        accept="image/*"
                        className="hidden"
                        onChange={handleMultiChatFiles}
                      />
                    </label>

                    <input
                      type="text"
                      value={messageText}
                      onChange={(e) => setMessageText(e.target.value)}
                      placeholder="Type your response to compliance desk..."
                      className="flex-1 px-4 py-2.5 bg-[var(--color-secondary-surface)] focus:bg-white text-[var(--color-text-primary)] rounded-lg border border-[var(--color-border)] focus:border-[var(--color-royal-blue)] focus:outline-none text-xs"
                    />

                    <Button
                      type="submit"
                      variant="primary"
                      size="sm"
                      isLoading={isSending}
                      disabled={!messageText.trim() && chatAttachments.length === 0}
                    >
                      <Send className="w-4 h-4 mr-1" />
                      <span>Send</span>
                    </Button>
                  </div>
                </form>
              ) : (
                <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-secondary-surface)] text-center text-xs text-[var(--color-text-secondary)] font-medium">
                  This support ticket is marked as <strong>RESOLVED</strong>. If you require further assistance, please open a new support ticket.
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-[var(--color-text-secondary)] space-y-3">
              <LifeBuoy className="h-12 w-12 text-[var(--color-text-muted)]" />
              <p className="text-sm font-semibold text-[var(--color-sapphire)]">Select a ticket to view conversation</p>
              <p className="text-xs font-medium text-center max-w-sm">
                Choose an existing support ticket on the left or create a new ticket for identity verification and transfer recovery.
              </p>
            </div>
          )}
        </Card>
      </div>

      {/* NEW SUPPORT TICKET MODAL */}
      {isNewTicketModalOpen && (
        <Modal
          isOpen={isNewTicketModalOpen}
          onClose={() => setIsNewTicketModalOpen(false)}
          title="Open New Support Ticket"
          subtitle="Submit an inquiry or identity verification request to the Compliance Desk"
          maxWidth="lg"
        >
          <form onSubmit={handleCreateTicket} className="space-y-4 text-xs">
            {newTicketError && (
              <Alert
                variant="danger"
                icon={<AlertCircle className="w-4 h-4" />}
                message={newTicketError}
              />
            )}

            <Select
              label="Issue Category"
              value={newTicketData.issue_type}
              onChange={(e) => {
                const val = e.target.value;
                setNewTicketData((prev) => ({
                  ...prev,
                  issue_type: val,
                  subject:
                    val === 'TRANSFER_BLOCKED'
                      ? 'Transfer Password Blocked — Requesting Identity Verification'
                      : val === 'FORGOTTEN_TRANSFER_PASSWORD'
                      ? 'Forgotten Transfer Password — Identity Verification & Reset Request'
                      : prev.subject,
                }));
              }}
              options={[
                { value: 'TRANSFER_BLOCKED', label: 'Transfer Password Blocked (3 Incorrect Attempts)' },
                { value: 'FORGOTTEN_TRANSFER_PASSWORD', label: 'Forgotten Transfer Password' },
                { value: 'ACCOUNT_DISCREPANCY', label: 'Transaction / Account Discrepancy' },
                { value: 'GENERAL_INQUIRY', label: 'General Banking Inquiry' },
              ]}
            />

            <Input
              label="Ticket Subject"
              type="text"
              required
              value={newTicketData.subject}
              onChange={(e) => setNewTicketData((prev) => ({ ...prev, subject: e.target.value }))}
              placeholder="Summary of issue"
            />

            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Detailed Description</label>
              <textarea
                rows={3}
                required
                value={newTicketData.description}
                onChange={(e) => setNewTicketData((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Explain your situation in detail..."
                className="w-full px-4 py-2.5 bg-white text-[var(--color-text-primary)] rounded-lg border border-[var(--color-border)] focus:border-[var(--color-royal-blue)] focus:outline-none text-xs font-sans"
              />
            </div>

            <Select
              label="Urgency Priority"
              value={newTicketData.priority}
              onChange={(e) => setNewTicketData((prev) => ({ ...prev, priority: e.target.value }))}
              options={[
                { value: 'HIGH', label: 'High Priority (Immediate Review)' },
                { value: 'MEDIUM', label: 'Medium Priority' },
                { value: 'LOW', label: 'Low Priority' },
              ]}
            />

            {/* Optional ID Attachment inside modal */}
            <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-3">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-sapphire)] block">
                Attach National ID / Passport (Recommended for Fast Resolution)
              </span>

              <Input
                label="National ID Number (14 Digits)"
                type="text"
                maxLength={14}
                value={modalNationalId}
                onChange={(e) => setModalNationalId(e.target.value)}
                placeholder={customer?.national_id_number || '29801011234567'}
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white hover:bg-[var(--color-secondary-surface)] border border-[var(--color-border)] rounded-lg text-xs font-bold text-[var(--color-sapphire)] cursor-pointer min-h-[44px]">
                  <Upload className="w-4 h-4 text-[var(--color-sapphire)]" />
                  <span className="truncate">{modalIdFront ? 'Front Attached ✓' : 'Attach Front ID'}</span>
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => handleModalPhotoUpload(e, 'front')}
                  />
                </label>

                <label className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white hover:bg-[var(--color-secondary-surface)] border border-[var(--color-border)] rounded-lg text-xs font-bold text-[var(--color-sapphire)] cursor-pointer min-h-[44px]">
                  <Upload className="w-4 h-4 text-[var(--color-sapphire)]" />
                  <span className="truncate">{modalIdBack ? 'Back Attached ✓' : 'Attach Back ID'}</span>
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => handleModalPhotoUpload(e, 'back')}
                  />
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--color-border)]">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsNewTicketModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={newTicketLoading}
              >
                <Plus className="w-4 h-4 mr-1.5" />
                <span>Create Support Ticket</span>
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* ZOOMED IMAGE MODAL */}
      {zoomedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setZoomedImage(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] bg-white rounded-2xl p-2 shadow-2xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setZoomedImage(null)}
              className="absolute top-4 right-4 p-2 rounded-full bg-[var(--color-sapphire)] text-white hover:bg-black transition-colors z-10 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
            <img
              src={zoomedImage}
              alt="Zoomed Verification Evidence"
              className="max-h-[85vh] w-auto object-contain rounded-xl"
            />
          </div>
        </div>
      )}
    </div>
  );
};
