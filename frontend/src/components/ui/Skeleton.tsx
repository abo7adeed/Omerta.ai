import React from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'rectangular' | 'circular';
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'rectangular',
  ...props
}) => {
  const variantStyles = {
    text: 'h-4 w-full rounded-[6px]',
    rectangular: 'rounded-[12px]',
    circular: 'rounded-full',
  };

  return (
    <div
      className={`animate-pulse bg-[#EBE7DF] ${variantStyles[variant]} ${className}`}
      {...props}
    />
  );
};
