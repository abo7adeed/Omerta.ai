import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Inbox } from 'lucide-react';
import { Button } from './Button';

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`p-10 text-center flex flex-col items-center justify-center space-y-3 bg-[#FFFFFF] border border-[#E0DDD6] rounded-[16px] ${className}`}
    >
      <div className="w-12 h-12 rounded-[14px] bg-[#F4F1EC] text-[#002D72] flex items-center justify-center">
        <Icon className="w-6 h-6 stroke-[2]" />
      </div>
      <div className="space-y-1 max-w-sm">
        <h4 className="text-sm font-bold text-[#002D72]">{title}</h4>
        <p className="text-xs text-[#64748B] leading-relaxed">{description}</p>
      </div>
      {actionLabel && onAction && (
        <Button onClick={onAction} variant="secondary" size="sm" className="mt-2">
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
