import React from 'react';
import { Input } from '../ui/Input';
import type { InputProps } from '../ui/Input';

export interface ClayInputProps extends InputProps {}

export const ClayInput = React.forwardRef<HTMLInputElement, ClayInputProps>((props, ref) => {
  return <Input ref={ref} {...props} />;
});

ClayInput.displayName = 'ClayInput';
