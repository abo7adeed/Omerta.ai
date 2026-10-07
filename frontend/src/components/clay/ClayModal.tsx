import React from 'react';
import { Modal } from '../ui/Modal';
import type { ModalProps } from '../ui/Modal';

export interface ClayModalProps extends ModalProps {}

export const ClayModal: React.FC<ClayModalProps> = (props) => {
  return <Modal {...props} />;
};
