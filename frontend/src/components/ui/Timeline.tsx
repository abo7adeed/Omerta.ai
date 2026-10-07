import React from 'react';
import { Check } from 'lucide-react';

export interface TimelineItem {
  id: string | number;
  title: string;
  description?: React.ReactNode;
  timestamp?: string;
  status: 'completed' | 'active' | 'pending';
  icon?: React.ReactNode;
}

export interface TimelineProps {
  items: TimelineItem[];
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({ items, className = '' }) => {
  return (
    <div className={`relative pl-8 space-y-6 ${className}`}>
      {/* Vertical Connecting Track */}
      <div className="absolute top-2 bottom-2 left-3.5 w-0.5 bg-[#D1D5DB]" />

      {items.map((item, idx) => {
        const isLast = idx === items.length - 1;

        return (
          <div key={item.id} className="relative flex items-start gap-4">
            {/* Node Circle */}
            <div className="absolute -left-8 mt-0.5 flex items-center justify-center">
              {item.status === 'completed' && (
                <div className="w-7 h-7 rounded-full bg-[#ECFDF5] border-2 border-[#10B981] flex items-center justify-center text-[#10B981] shadow-xs">
                  {item.icon || <Check className="w-3.5 h-3.5 stroke-[3]" />}
                </div>
              )}
              {item.status === 'active' && (
                <div className="w-7 h-7 rounded-full bg-[#FFF9E6] border-2 border-[#F9A825] flex items-center justify-center shadow-[0_0_0_4px_rgba(249,168,37,0.2)]">
                  <div className="w-2.5 h-2.5 rounded-full bg-[#F9A825]" />
                </div>
              )}
              {item.status === 'pending' && (
                <div className="w-7 h-7 rounded-full bg-white border-2 border-[#D1D5DB] flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-[#D1D5DB]" />
                </div>
              )}
            </div>

            {/* Content Box */}
            <div className="flex-1 space-y-1 bg-white p-4 rounded-[12px] border border-[#E0DDD6] shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <h4 className="text-sm font-bold text-[#002D72]">{item.title}</h4>
                {item.timestamp && (
                  <span className="text-[11px] font-mono text-[#64748B]">
                    {item.timestamp}
                  </span>
                )}
              </div>
              {item.description && (
                <div className="text-xs text-[#475569] leading-relaxed pt-0.5">
                  {item.description}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
