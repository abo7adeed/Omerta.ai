import React from 'react';

export interface TabItem {
  id: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  count?: number | string;
  badge?: string;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  className = '',
}) => {
  return (
    <div className={`border-b border-[#E0DDD6] flex items-center gap-2 overflow-x-auto ${className}`}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const Icon = tab.icon;

        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold whitespace-nowrap transition-all duration-150 border-b-2 cursor-pointer ${
              isActive
                ? 'border-[#F9A825] text-[#002D72] font-bold bg-white/40'
                : 'border-transparent text-[#64748B] hover:text-[#002D72] hover:border-[#CBD5E1]'
            }`}
          >
            {tab.icon && (
              React.isValidElement(tab.icon) ? (
                tab.icon
              ) : (
                <tab.icon
                  className={`h-4 w-4 transition-colors ${
                    isActive ? 'text-[#F9A825]' : 'text-[#94A3B8]'
                  }`}
                />
              )
            )}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={`text-[11px] px-2 py-0.5 rounded-full font-mono font-bold ${
                  isActive
                    ? 'bg-[#FEF3C7] text-[#854D0E]'
                    : 'bg-[#F1F5F9] text-[#64748B]'
                }`}
              >
                {tab.count}
              </span>
            )}
            {tab.badge && (
              <span className="text-[10px] uppercase px-1.5 py-0.5 rounded font-bold bg-[#EBF3FC] text-[#002D72]">
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
