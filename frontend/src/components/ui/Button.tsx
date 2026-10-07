import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'sapphire' | 'tertiary' | 'danger' | 'ghost' | 'emerald' | 'success' | 'outline';
  size?: 'sm' | 'md' | 'lg' | 'icon' | 'default';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className = '',
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-bold tracking-tight rounded-[10px] transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-offset-1 select-none disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none active:scale-[0.98]';

    const variants = {
      primary:
        'bg-[#F9A825] text-[#002D72] hover:bg-[#E6951A] focus:ring-[#F9A825]/40 shadow-sm hover:shadow',
      secondary:
        'bg-transparent border-2 border-[#002D72] text-[#002D72] hover:bg-[#002D72]/5 focus:ring-[#002D72]/30',
      outline:
        'bg-transparent border-2 border-[#002D72] text-[#002D72] hover:bg-[#002D72]/5 focus:ring-[#002D72]/30',
      sapphire:
        'bg-[#002D72] text-white hover:bg-[#001F52] focus:ring-[#002D72]/40 shadow-sm hover:shadow',
      tertiary:
        'text-[#1E88E5] hover:text-[#1976D2] hover:bg-[#1E88E5]/10 focus:ring-[#1E88E5]/30',
      danger:
        'bg-rose-50 border border-rose-200 text-rose-700 hover:bg-rose-100 focus:ring-rose-400/30',
      ghost:
        'text-[#475569] hover:text-[#002D72] hover:bg-[#F4F1EC] focus:ring-slate-300',
      emerald:
        'bg-[#10B981] text-white hover:bg-[#059669] focus:ring-[#10B981]/40 shadow-sm',
      success:
        'bg-[#10B981] text-white hover:bg-[#059669] focus:ring-[#10B981]/40 shadow-sm',
    };

    const resolvedSize = size === 'default' ? 'md' : size;

    const sizes = {
      sm: 'h-9 px-3.5 text-xs gap-1.5',
      md: 'min-h-[44px] px-5 text-sm gap-2',
      lg: 'h-12 px-6 text-base gap-2.5',
      icon: 'h-11 w-11 p-0',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${baseStyles} ${variants[variant]} ${sizes[resolvedSize]} ${className}`}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-current" />
        ) : (
          leftIcon
        )}
        {children}
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';
