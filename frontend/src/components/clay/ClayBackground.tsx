import React from 'react';

export interface ClayBackgroundProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const ClayBackground: React.FC<ClayBackgroundProps> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <div
      className={`min-h-screen bg-[#FFF8E1] text-[#0F172A] flex flex-col relative selection:bg-[#F9A825]/30 selection:text-[#002D72] ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
