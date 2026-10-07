import React from 'react';
import type { LucideIcon } from 'lucide-react';

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  description?: string;
  change?: string;
  isPositive?: boolean;
  icon?: LucideIcon | React.ReactNode;
  variant?: 'default' | 'sapphire' | 'gold' | 'emerald' | 'amber' | 'blue' | 'rose' | 'alert' | 'cyan' | 'purple' | 'pink';
  onClick?: () => void;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  description,
  change,
  isPositive,
  icon,
  variant = 'default',
  onClick,
  className = '',
}) => {
  const iconThemes: Record<string, { bg: string; text: string; border: string }> = {
    sapphire: { bg: 'bg-[#EBF3FC]', text: 'text-[#002D72]', border: 'border-[#BFDBFE]' },
    gold: { bg: 'bg-[#FFF9E6]', text: 'text-[#F9A825]', border: 'border-[#FFE082]' },
    emerald: { bg: 'bg-[#ECFDF5]', text: 'text-[#10B981]', border: 'border-[#A7F3D0]' },
    amber: { bg: 'bg-[#FFFBEB]', text: 'text-[#D97706]', border: 'border-[#FDE68A]' },
    blue: { bg: 'bg-[#EFF6FF]', text: 'text-[#1E88E5]', border: 'border-[#BFDBFE]' },
    rose: { bg: 'bg-[#FEF2F2]', text: 'text-[#DC2626]', border: 'border-[#FECACA]' },
    alert: { bg: 'bg-[#FFFBEB]', text: 'text-[#D97706]', border: 'border-[#FDE68A]' },
    cyan: { bg: 'bg-[#EFF6FF]', text: 'text-[#1E88E5]', border: 'border-[#BFDBFE]' },
    purple: { bg: 'bg-[#EBF3FC]', text: 'text-[#002D72]', border: 'border-[#BFDBFE]' },
    pink: { bg: 'bg-[#FFF9E6]', text: 'text-[#F9A825]', border: 'border-[#FFE082]' },
    default: { bg: 'bg-[#EBF3FC]', text: 'text-[#002D72]', border: 'border-[#BFDBFE]' },
  };

  const theme = iconThemes[variant] || iconThemes.default;

  return (
    <div
      onClick={onClick}
      className={`bg-white border border-[#E0DDD6] rounded-[16px] p-5 shadow-xs transition-all duration-200 ${
        onClick
          ? 'cursor-pointer hover:border-[#D1CD06] hover:shadow-md hover:-translate-y-0.5'
          : ''
      } ${className}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
          {title}
        </span>
        {icon && (
          <div
            className={`w-9 h-9 rounded-[10px] ${theme.bg} ${theme.border} ${theme.text} border flex items-center justify-center shrink-0 shadow-xs`}
          >
            {React.isValidElement(icon) ? (
              icon
            ) : typeof icon === 'function' || (typeof icon === 'object' && icon !== null) ? (
              React.createElement(icon as any, { className: 'w-4.5 h-4.5 stroke-[2.2]' })
            ) : null}
          </div>
        )}
      </div>

      <div className="space-y-1">
        <div className="text-2xl font-bold tracking-tight text-[#002D72]">
          {value}
        </div>

        {(subtitle || change || description) && (
          <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
            {change && (
              <span
                className={`font-semibold px-2 py-0.5 rounded-[6px] text-[11px] ${
                  isPositive === true
                    ? 'bg-[#ECFDF5] text-[#065F46]'
                    : isPositive === false
                    ? 'bg-[#FEF2F2] text-[#991B1B]'
                    : 'bg-[#F4F1EC] text-[#475569]'
                }`}
              >
                {change}
              </span>
            )}
            {subtitle && (
              <span className="text-[#64748B] font-medium truncate">
                {subtitle}
              </span>
            )}
            {description && !subtitle && (
              <span className="text-[#64748B] font-medium truncate">
                {description}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
