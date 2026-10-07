import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from 'lucide-react';

export interface AlertProps {
  variant?: 'info' | 'success' | 'warning' | 'danger';
  title?: string;
  children?: React.ReactNode;
  message?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  variant = 'info',
  title,
  children,
  message,
  icon,
  className = '',
}) => {
  const configs = {
    info: {
      bg: 'bg-[#EBF3FC]',
      border: 'border-[#BFDBFE]',
      text: 'text-[#002D72]',
      icon: Info,
      iconColor: 'text-[#1E88E5]',
    },
    success: {
      bg: 'bg-[#ECFDF5]',
      border: 'border-[#A7F3D0]',
      text: 'text-[#065F46]',
      icon: CheckCircle2,
      iconColor: 'text-[#10B981]',
    },
    warning: {
      bg: 'bg-[#FFF9E6]',
      border: 'border-[#FFE082]',
      text: 'text-[#92400E]',
      icon: AlertTriangle,
      iconColor: 'text-[#F9A825]',
    },
    danger: {
      bg: 'bg-[#FEF2F2]',
      border: 'border-[#FECACA]',
      text: 'text-[#991B1B]',
      icon: AlertCircle,
      iconColor: 'text-[#DC2626]',
    },
  };

  const config = configs[variant];
  const DefaultIcon = config.icon;
  const content = children || message;

  return (
    <div
      className={`p-4 rounded-[12px] border ${config.bg} ${config.border} flex items-start gap-3 ${className}`}
    >
      {icon ? (
        <div className={`shrink-0 mt-0.5 ${config.iconColor}`}>{icon}</div>
      ) : (
        <DefaultIcon className={`w-5 h-5 ${config.iconColor} shrink-0 mt-0.5`} />
      )}
      <div className="space-y-0.5 flex-1">
        {title && (
          <h5 className={`text-xs font-bold ${config.text}`}>{title}</h5>
        )}
        {content && (
          <div className={`text-xs font-medium leading-relaxed ${config.text}`}>
            {content}
          </div>
        )}
      </div>
    </div>
  );
};
