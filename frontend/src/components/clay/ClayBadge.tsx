import React from 'react';
import { StatusBadge } from '../ui/StatusBadge';
import type { BadgeVariant } from '../ui/StatusBadge';

export interface ClayBadgeProps {
  variant?: 'primary' | 'purple' | 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'glass' | 'emerald';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  pulse?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const ClayBadge: React.FC<ClayBadgeProps> = ({
  variant = 'primary',
  size = 'md',
  dot,
  icon,
  children,
  className = '',
}) => {
  const variantMap: Record<string, BadgeVariant> = {
    primary: 'sapphire',
    purple: 'sapphire',
    success: 'emerald',
    emerald: 'emerald',
    warning: 'gold',
    danger: 'rose',
    info: 'blue',
    neutral: 'neutral',
    glass: 'neutral',
  };

  const statusVariant = variantMap[variant] || 'sapphire';

  return (
    <StatusBadge
      variant={statusVariant}
      size={size}
      dot={dot}
      icon={icon}
      className={className}
    >
      {children}
    </StatusBadge>
  );
};
