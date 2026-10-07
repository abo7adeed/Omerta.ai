import React from 'react';
import type { RiskLevel } from '../../types';

export interface RiskBadgeProps {
  level: RiskLevel | string;
  score?: number;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  level,
  score,
  size = 'md',
  showScore = true,
  className = '',
}) => {
  const norm = (level || 'LOW').toUpperCase();

  const config: Record<
    string,
    { bg: string; text: string; border: string; dot: string; label: string }
  > = {
    LOW: {
      bg: 'bg-[#ECFDF5]',
      text: 'text-[#065F46]',
      border: 'border-[#A7F3D0]',
      dot: 'bg-[#10B981]',
      label: 'LOW',
    },
    MODERATE: {
      bg: 'bg-[#EBF3FC]',
      text: 'text-[#002D72]',
      border: 'border-[#BFDBFE]',
      dot: 'bg-[#1E88E5]',
      label: 'MEDIUM',
    },
    MEDIUM: {
      bg: 'bg-[#EBF3FC]',
      text: 'text-[#002D72]',
      border: 'border-[#BFDBFE]',
      dot: 'bg-[#1E88E5]',
      label: 'MEDIUM',
    },
    REQUIRES_REVIEW: {
      bg: 'bg-[#FFF9E6]',
      text: 'text-[#002D72]',
      border: 'border-[#FFE082]',
      dot: 'bg-[#F9A825]',
      label: 'REVIEW',
    },
    HIGH: {
      bg: 'bg-[#FEF3C7]',
      text: 'text-[#92400E]',
      border: 'border-[#FDE68A]',
      dot: 'bg-[#F59E0B]',
      label: 'HIGH',
    },
    CRITICAL: {
      bg: 'bg-[#FEF2F2]',
      text: 'text-[#991B1B]',
      border: 'border-[#FECACA]',
      dot: 'bg-[#DC2626]',
      label: 'CRITICAL',
    },
  };

  const style = config[norm] || config.LOW;

  const sizeClasses = {
    sm: 'px-2.5 py-0.5 text-[10px]',
    md: 'px-3 py-1 text-[11px]',
    lg: 'px-3.5 py-1.5 text-xs',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-bold uppercase tracking-wider rounded-full border ${style.bg} ${style.text} ${style.border} ${sizeClasses[size]} ${className}`}
    >
      <span className={`h-2 w-2 rounded-full ${style.dot} shrink-0`} />
      <span>{style.label}</span>
      {showScore && score !== undefined && (
        <span className="font-mono font-semibold ml-0.5 opacity-90">
          ({score.toFixed(0)}%)
        </span>
      )}
    </span>
  );
};
