import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { MobileNav } from './MobileNav';
import {
  Search,
  ArrowRight,
  ShieldAlert,
  Users,
  Wallet,
  Smartphone,
  KeyRound,
  ShieldCheck,
  Check,
  AlertCircle,
  Eye,
  EyeOff,
  Lock,
} from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

export const AppLayout: React.FC = () => {
  const { user, customer, refreshCustomerProfile } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  // Global Set Transfer Password Modal State
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [newTransferPassword, setNewTransferPassword] = useState('');
  const [confirmTransferPassword, setConfirmTransferPassword] = useState('');
  const [showPasswordText, setShowPasswordText] = useState(false);
  const [passwordModalLoading, setPasswordModalLoading] = useState(false);
  const [passwordModalError, setPasswordModalError] = useState<string | null>(null);
  const [passwordModalSuccess, setPasswordModalSuccess] = useState(false);

  const isCustomer = user?.role === 'CUSTOMER';
  const requirePasswordChange = Boolean(isCustomer && customer?.require_transfer_password_change);

  // Periodic check of customer profile status
  useEffect(() => {
    if (!isCustomer) return;
    refreshCustomerProfile();
    const interval = setInterval(() => {
      refreshCustomerProfile();
    }, 5000);
    return () => clearInterval(interval);
  }, [isCustomer]);

  // Global keyboard shortcut for ⌘K search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchOpen(false);
    navigate(`/admin/transactions?search=${encodeURIComponent(searchQuery.trim())}`);
  };

  const handleChangeTransferPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordModalError(null);

    if (!newTransferPassword) {
      setPasswordModalError('Please enter a new transfer password.');
      return;
    }
    if (newTransferPassword.length < 8) {
      setPasswordModalError('Transfer password must be at least 8 characters long.');
      return;
    }
    if (newTransferPassword !== confirmTransferPassword) {
      setPasswordModalError('New transfer password and confirmation do not match.');
      return;
    }

    setPasswordModalLoading(true);
    try {
      await api.changeTransferPassword({
        new_transfer_password: newTransferPassword,
        confirm_transfer_password: confirmTransferPassword,
      });

      setPasswordModalSuccess(true);
      await refreshCustomerProfile();

      setTimeout(() => {
        setPasswordModalOpen(false);
        setPasswordModalSuccess(false);
        setNewTransferPassword('');
        setConfirmTransferPassword('');
      }, 1800);
    } catch (err: any) {
      setPasswordModalError(err.message || 'Failed to update transfer password. Please try again.');
    } finally {
      setPasswordModalLoading(false);
    }
  };

  const quickLinks = [
    { label: 'Risk Review Queue', path: '/admin/risk-monitoring', icon: ShieldAlert },
    { label: 'Transactions Dossier', path: '/admin/transactions', icon: ArrowRight },
    { label: 'Customer Directory', path: '/admin/customers', icon: Users },
    { label: 'Account Directory', path: '/admin/accounts', icon: Wallet },
    { label: 'Device Intelligence', path: '/admin/devices', icon: Smartphone },
  ];

  return (
    <div className="min-h-screen bg-[#FFF8E1] text-[#0F172A] flex relative">
      {/* Sidebar Navigation */}
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />

      {/* Main Workspace Frame */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-200 ${
          collapsed ? 'md:ml-20' : 'md:ml-64'
        }`}
      >
        <Header collapsed={collapsed} onOpenSearch={() => setSearchOpen(true)} />

        {/* TOP PERSISTENT NOTIFICATION BAR: TRANSFER PRIVILEGES RESTORED */}
        {requirePasswordChange && (
          <div className="mt-20 mx-4 sm:mx-8 mb-2 bg-[#FFF9E6] border border-[#FFE082] rounded-[14px] p-4 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xs z-20">
            <div className="flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-[10px] bg-[#FEF3C7] text-[#B45309] flex items-center justify-center shrink-0 border border-[#FDE68A]">
                <KeyRound className="w-5 h-5 stroke-[2.2]" />
              </div>
              <div className="space-y-0.5">
                <p className="text-xs font-bold text-[#002D72] flex items-center gap-2">
                  <span>Action Required: Transfer Privileges Restored</span>
                  <span className="px-2 py-0.5 rounded-full bg-[#FEF3C7] text-[#854D0E] text-[10px] font-mono font-bold">
                    Transfers Locked
                  </span>
                </p>
                <p className="text-xs text-[#475569] leading-tight font-medium">
                  Compliance has verified your identity and restored account access. Please set your new Transfer Password to activate money movement.
                </p>
              </div>
            </div>

            <Button
              type="button"
              size="sm"
              variant="primary"
              onClick={() => {
                setPasswordModalError(null);
                setPasswordModalOpen(true);
              }}
              className="shrink-0"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Set Transfer Password</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        )}

        <main
          className={`flex-1 p-4 sm:p-6 md:p-8 max-w-7xl w-full mx-auto space-y-6 pb-24 md:pb-8 ${
            requirePasswordChange ? 'mt-2' : 'mt-16'
          }`}
        >
          <Outlet />
        </main>

        {/* Mobile Navigation */}
        <MobileNav />
      </div>

      {/* Global Search Modal (⌘K) */}
      <Modal
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        title="Global Intelligence Search"
        subtitle="Search transactions, accounts, customers, devices or alerts across Omerta.ai"
        maxWidth="lg"
      >
        <form onSubmit={handleSearchSubmit} className="space-y-4">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="e.g. TXN-001, ACC-1001, DEV-123, Cairo Tech..."
            autoFocus
            leftIcon={<Search className="h-4 w-4 text-[#002D72]" />}
          />

          <div className="pt-2">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] mb-2">
              Quick Shortcuts
            </p>
            <div className="space-y-1">
              {quickLinks.map((item) => (
                <button
                  key={item.path}
                  type="button"
                  onClick={() => {
                    setSearchOpen(false);
                    navigate(item.path);
                  }}
                  className="w-full flex items-center justify-between p-2.5 rounded-[8px] text-xs font-semibold text-[#475569] hover:bg-[#F4F1EC] hover:text-[#002D72] transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2.5">
                    <item.icon className="h-4 w-4 text-[#002D72]" />
                    <span>{item.label}</span>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-[#94A3B8]" />
                </button>
              ))}
            </div>
          </div>
        </form>
      </Modal>

      {/* GLOBAL SET NEW TRANSFER PASSWORD MODAL */}
      {passwordModalOpen && (
        <Modal
          isOpen={passwordModalOpen}
          onClose={() => setPasswordModalOpen(false)}
          title="Set New Transfer Password"
          subtitle="Compliance Restoration: Please set a new transfer password to complete reactivation"
          maxWidth="md"
        >
          <form onSubmit={handleChangeTransferPassword} className="space-y-4 text-xs">
            {passwordModalSuccess ? (
              <div className="p-4 rounded-[12px] bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] flex items-center gap-3">
                <Check className="w-5 h-5 shrink-0 text-[#10B981] stroke-[3]" />
                <div className="space-y-0.5">
                  <p className="font-bold text-[#065F46] text-sm">Transfer Password Updated Successfully!</p>
                  <p className="text-xs text-[#065F46] font-medium">
                    Your transfer access is now ACTIVE. You can make money transfers freely.
                  </p>
                </div>
              </div>
            ) : (
              <>
                {passwordModalError && (
                  <div className="p-3 rounded-[10px] bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B] flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-[#DC2626]" />
                    <span className="font-semibold">{passwordModalError}</span>
                  </div>
                )}

                <div className="p-3 rounded-[10px] bg-[#EBF3FC] border border-[#BFDBFE] text-[#002D72] flex items-start gap-2.5">
                  <ShieldCheck className="w-4.5 h-4.5 text-[#002D72] shrink-0 mt-0.5" />
                  <p className="text-xs leading-relaxed text-[#475569] font-medium">
                    Your account ownership was verified by Compliance. Set your new dedicated transfer password below to enable Send Money.
                  </p>
                </div>

                <Input
                  label="New Transfer Password (Min 8 Characters)"
                  type={showPasswordText ? 'text' : 'password'}
                  required
                  value={newTransferPassword}
                  onChange={(e) => setNewTransferPassword(e.target.value)}
                  placeholder="Enter new transfer password"
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowPasswordText(!showPasswordText)}
                      className="p-1 hover:text-[#002D72] cursor-pointer"
                    >
                      {showPasswordText ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  }
                />

                <Input
                  label="Confirm New Transfer Password"
                  type={showPasswordText ? 'text' : 'password'}
                  required
                  value={confirmTransferPassword}
                  onChange={(e) => setConfirmTransferPassword(e.target.value)}
                  placeholder="Repeat new transfer password"
                />

                <div className="flex items-center justify-end gap-3 pt-2">
                  <Button
                    type="submit"
                    variant="primary"
                    size="md"
                    isLoading={passwordModalLoading}
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>Save &amp; Reactivate Transfers</span>
                  </Button>
                </div>
              </>
            )}
          </form>
        </Modal>
      )}
    </div>
  );
};
