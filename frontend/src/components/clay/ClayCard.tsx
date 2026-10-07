import React from 'react';
import { Card } from '../ui/Card';

export interface ClayCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'sunken' | 'hero' | 'recessed' | 'interactive';
}

export const ClayCard = React.forwardRef<HTMLDivElement, ClayCardProps>(
  ({ children, className = '', variant = 'default', ...props }, ref) => {
    return (
      <Card
        ref={ref}
        variant={variant === 'interactive' ? 'interactive' : 'default'}
        className={className}
        {...props}
      >
        {children}
      </Card>
    );
  }
);

ClayCard.displayName = 'ClayCard';
