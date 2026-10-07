import React from 'react';
import { Button } from '../ui/Button';

export interface ClayButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'white' | 'danger' | 'ghost' | 'emerald' | 'amber' | 'blue';
  size?: 'sm' | 'default' | 'lg' | 'icon';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const ClayButton = React.forwardRef<HTMLButtonElement, ClayButtonProps>(
  (
    {
      children,
      className = '',
      variant = 'primary',
      size = 'default',
      isLoading = false,
      leftIcon,
      rightIcon,
      ...props
    },
    ref
  ) => {
    const mappedVariant = (() => {
      switch (variant) {
        case 'secondary':
        case 'white':
          return 'secondary';
        case 'danger':
          return 'danger';
        case 'ghost':
          return 'ghost';
        case 'emerald':
          return 'emerald';
        case 'blue':
          return 'sapphire';
        case 'amber':
        case 'primary':
        default:
          return 'primary';
      }
    })();

    const mappedSize = size === 'default' ? 'md' : size;

    return (
      <Button
        ref={ref}
        variant={mappedVariant}
        size={mappedSize}
        isLoading={isLoading}
        leftIcon={leftIcon}
        rightIcon={rightIcon}
        className={className}
        {...props}
      >
        {children}
      </Button>
    );
  }
);

ClayButton.displayName = 'ClayButton';
