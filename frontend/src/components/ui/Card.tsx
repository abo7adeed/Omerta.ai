import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'ivory' | 'highlighted' | 'interactive';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', variant = 'default', children, ...props }, ref) => {
    const variants = {
      default: 'bg-white border-[#E0DDD6] shadow-sm',
      secondary: 'bg-[#F4F1EC] border-[#E0DDD6]',
      ivory: 'bg-[#FFF8E1] border-[#E0DDD6]',
      highlighted: 'bg-white border-[#E0DDD6] border-l-4 border-l-[#F9A825] shadow-sm',
      interactive:
        'bg-white border-[#E0DDD6] shadow-sm hover:border-[#D1CD06] hover:shadow-md transition-all duration-200 cursor-pointer',
    };

    return (
      <div
        ref={ref}
        className={`rounded-[16px] border ${variants[variant]} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export const CardHeader = ({
  className = '',
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={`p-5 sm:p-6 border-b border-[#E0DDD6] flex flex-col space-y-1.5 ${className}`} {...props}>
    {children}
  </div>
);

export const CardTitle = ({
  className = '',
  children,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={`text-lg sm:text-xl font-bold tracking-tight text-[#002D72] flex items-center gap-2 ${className}`} {...props}>
    {children}
  </h3>
);

export const CardDescription = ({
  className = '',
  children,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) => (
  <p className={`text-xs text-[#64748B] font-medium leading-relaxed ${className}`} {...props}>
    {children}
  </p>
);

export const CardContent = ({
  className = '',
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={`p-5 sm:p-6 ${className}`} {...props}>
    {children}
  </div>
);

export const CardFooter = ({
  className = '',
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={`p-5 sm:p-6 border-t border-[#E0DDD6] bg-[#F4F1EC]/40 rounded-b-[16px] flex items-center justify-between gap-4 ${className}`} {...props}>
    {children}
  </div>
);
