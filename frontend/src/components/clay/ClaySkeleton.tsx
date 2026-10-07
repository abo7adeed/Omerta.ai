import React from 'react';
import { Skeleton } from '../ui/Skeleton';
import type { SkeletonProps } from '../ui/Skeleton';

export interface ClaySkeletonProps extends SkeletonProps {}

export const ClaySkeleton: React.FC<ClaySkeletonProps> = (props) => {
  return <Skeleton {...props} />;
};
