import React from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  options?: Array<SelectOption | string>;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, helperText, children, options, className = '', id, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-[11px] font-bold uppercase tracking-wider text-[#475569]"
          >
            {label}
            {props.required && <span className="text-rose-600 ml-1">*</span>}
          </label>
        )}
        <div className="relative flex items-center">
          <select
            id={selectId}
            ref={ref}
            className={`w-full min-h-[44px] appearance-none bg-white border rounded-[10px] px-3.5 pr-10 py-2 text-sm text-[#0F172A] transition-all duration-200 outline-none cursor-pointer ${
              error
                ? 'border-rose-400 focus:border-rose-500 focus:ring-3 focus:ring-rose-100'
                : 'border-[#E0DDD6] focus:border-[#1E88E5] focus:ring-3 focus:ring-[#1E88E5]/15'
            } ${className}`}
            {...props}
          >
            {options
              ? options.map((opt) => {
                  const val = typeof opt === 'string' ? opt : opt.value;
                  const lbl = typeof opt === 'string' ? opt : opt.label;
                  return (
                    <option key={val} value={val}>
                      {lbl}
                    </option>
                  );
                })
              : children}
          </select>
          <div className="absolute right-3.5 flex items-center pointer-events-none text-[#64748B]">
            <ChevronDown className="h-4 w-4" />
          </div>
        </div>
        {error && (
          <p className="text-xs font-semibold text-rose-600 mt-1">{error}</p>
        )}
        {helperText && !error && (
          <p className="text-xs text-[#64748B] mt-1">{helperText}</p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';
