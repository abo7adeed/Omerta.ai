import React from 'react';
import { StatCard } from '../ui/StatCard';
import type { StatCardProps } from '../ui/StatCard';

export interface ClayStatProps extends StatCardProps {}

export const ClayStat: React.FC<ClayStatProps> = (props) => {
  return <StatCard {...props} />;
};
