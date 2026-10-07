import React from 'react';

export type BadgeVariant =
  | 'active'
  | 'success'
  | 'info'
  | 'pending'
  | 'expired'
  | 'critical'
  | 'gold'
  | 'sapphire'
  | 'emerald'
  | 'royal'
  | 'danger'
  | 'rose'
  | 'neutral'
  | 'blue';

export interface StatusBadgeProps {
  status?: string;
  variant?: BadgeVariant;
  children?: React.ReactNode;
  className?: string;
  type?: 'transaction' | 'review' | 'case' | 'general';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  icon?: React.ReactNode;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  children,
  className = '',
  size = 'md',
  dot,
  icon,
}) => {
  const norm = (status || (typeof children === 'string' ? children : '') || 'UNKNOWN').toUpperCase();

  // Determine variant automatically from status text if not explicitly provided
  const resolvedVariant: BadgeVariant = variant || (() => {
    switch (norm) {
      case 'ACTIVE':
      case 'SETTLED':
      case 'SUBMITTED':
      case 'ACTION_REQUIRED':
        return 'active';
      case 'COMPLETED':
      case 'RESOLVED':
      case 'CLOSED':
      case 'APPROVED':
      case 'VERIFIED':
      case 'SUCCESS':
      case 'LOW':
        return 'success';
      case 'UNDER_INVESTIGATION':
      case 'IN_REVIEW':
      case 'ANALYZING':
      case 'INVESTIGATION':
      case 'QUOTED':
        return 'info';
      case 'REQUIRES_REVIEW':
      case 'OPEN':
      case 'NEW':
      case 'PENDING':
      case 'PENDING_REVIEW':
      case 'PENDING_IDV':
      case 'SECURITY_HOLD':
      case 'RESTORATION_REQUIRED':
      case 'PROCESSING':
        return 'gold';
      case 'EXPIRED':
      case 'INACTIVE':
      case 'ARCHIVED':
        return 'expired';
      case 'ESCALATED':
      case 'REJECTED':
      case 'BLOCKED':
      case 'FLAGGED':
      case 'FAILED':
      case 'CRITICAL':
      case 'HIGH':
        return 'critical';
      default:
        return 'pending';
    }
  })();

  const styles: Record<BadgeVariant, string> = {
    active: 'bg-[#FFF9E6] text-[#002D72] border-[#FFE082]',
    gold: 'bg-[#FEF3C7] text-[#854D0E] border-[#FDE68A]',
    success: 'bg-[#ECFDF5] text-[#065F46] border-[#A7F3D0]',
    emerald: 'bg-[#10B981] text-white border-transparent shadow-xs',
    info: 'bg-[#EBF3FC] text-[#002D72] border-[#BFDBFE]',
    blue: 'bg-[#EFF6FF] text-[#1E88E5] border-[#BFDBFE]',
    sapphire: 'bg-[#002D72] text-white border-transparent',
    royal: 'bg-[#EFF6FF] text-[#1E88E5] border-[#BFDBFE]',
    pending: 'bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]',
    neutral: 'bg-[#F8FAFC] text-[#475569] border-[#E2E8F0]',
    expired: 'bg-[#F8FAFC] text-[#64748B] border-[#E2E8F0]',
    critical: 'bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]',
    danger: 'bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]',
    rose: 'bg-[#FFF1F2] text-[#9F1239] border-[#FECDD3]',
  };

  const sizeStyles: Record<'sm' | 'md' | 'lg', string> = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-[11px] px-3 py-1',
    lg: 'text-[12px] px-3.5 py-1.5',
  };

  const displayText = children || norm.replace(/_/g, ' ');

  return (
    <span
      className={`inline-flex items-center justify-center gap-1.5 font-bold uppercase tracking-wider rounded-full border ${sizeStyles[size]} ${styles[resolvedVariant]} transition-colors duration-150 ${className}`}
    >
      {dot && (
        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80 shrink-0" />
      )}
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{displayText}</span>
    </span>
  );
};
