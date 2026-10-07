import React, { useState } from 'react';
import {
  Search,
  Bell,
  UserCheck,
  Activity,
  LogOut,
  ChevronDown,
  Copy,
  Check,
  Send,
  Building2,
  ShieldCheck,
  Lock,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';

interface HeaderProps {
  collapsed: boolean;
  onOpenSearch: () => void;
}

export const Header: React.FC<HeaderProps> = ({ collapsed, onOpenSearch }) => {
  const { user, customer, logout } = useAuth();
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();

  const isCustomer = user?.role === 'CUSTOMER';

  const handleCopyUserNumber = () => {
    if (customer?.omerta_user_number) {
      navigator.clipboard.writeText(customer.omerta_user_number);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <header
      className={`fixed top-0 right-0 z-30 flex items-center justify-between h-16 px-6 bg-white border-b border-[#E0DDD6] shadow-xs transition-all duration-200 ${
        collapsed ? 'left-20' : 'left-64'
      }`}
    >
      {/* Left section */}
      <div className="flex items-center gap-3 flex-1 max-w-lg">
        {isCustomer ? (
          <div className="flex items-center gap-3">
            {customer?.omerta_user_number && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-[8px] bg-[#F4F1EC] border border-[#E0DDD6]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                  User ID:
                </span>
                <span className="text-xs font-mono font-bold text-[#002D72]">
                  {customer.omerta_user_number}
                </span>
                <button
                  onClick={handleCopyUserNumber}
                  className="p-1 text-[#64748B] hover:text-[#002D72] rounded-[6px] hover:bg-white transition-colors cursor-pointer"
                  title="Copy Omerta User Number for transfers"
                  aria-label="Copy Omerta User Number"
                >
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-[#10B981] stroke-[3]" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            )}
            <button
              onClick={() => navigate('/customer/transfer')}
              className="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-[8px] bg-[#F9A825] hover:bg-[#E6951A] text-[#002D72] text-xs font-bold shadow-xs transition-all cursor-pointer"
            >
              <Send className="h-3.5 w-3.5 stroke-[2.2]" />
              <span>Send Money</span>
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenSearch}
            className="flex items-center justify-between w-full px-3.5 py-2 rounded-[10px] bg-[#F4F1EC] border border-[#E0DDD6] text-xs font-medium text-[#64748B] hover:text-[#002D72] hover:border-[#1E88E5] transition-all cursor-pointer"
          >
            <div className="flex items-center gap-2.5">
              <Search className="h-4 w-4 text-[#002D72]" />
              <span className="truncate">Search transactions, accounts, customers, devices...</span>
            </div>
            <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono font-bold text-[#002D72] bg-white rounded-[6px] border border-[#E0DDD6] shadow-xs">
              ⌘K
            </kbd>
          </button>
        )}
      </div>

      {/* Header Right Actions */}
      <div className="flex items-center gap-3">
        {/* Status Indicator */}
        {!isCustomer ? (
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-[8px] bg-[#FFF9E6] border border-[#FFE082] text-xs font-semibold text-[#002D72]">
            <Activity className="h-3.5 w-3.5 text-[#F9A825] animate-pulse" />
            <span>Human Review Queue:</span>
            <span className="font-mono font-bold text-[#B45309]">&gt; 40.00%</span>
          </div>
        ) : (
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-[8px] bg-[#ECFDF5] border border-[#A7F3D0] text-xs font-semibold text-[#065F46]">
            <span className="h-2 w-2 rounded-full bg-[#10B981] animate-pulse" />
            <span>Banking Status:</span>
            <span className="font-bold text-[#065F46]">ACTIVE</span>
          </div>
        )}

        {/* Review Queue Alerts Icon (Analyst / Admin) */}
        {!isCustomer && (
          <button
            onClick={() => navigate('/admin/risk-monitoring')}
            className="relative p-2 text-[#475569] hover:text-[#002D72] rounded-[8px] hover:bg-[#F4F1EC] transition-colors border border-[#E0DDD6] bg-white cursor-pointer"
            title="Review Queue Alerts"
            aria-label="Alerts"
          >
            <Bell className="h-4.5 w-4.5" />
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#F9A825]" />
          </button>
        )}

        {/* User Profile Menu Dropdown */}
        <div className="relative">
          <button
            onClick={() => setRoleMenuOpen(!roleMenuOpen)}
            className="flex items-center gap-2.5 p-1.5 pl-3 rounded-[10px] bg-white border border-[#E0DDD6] hover:border-[#1E88E5] transition-all text-left cursor-pointer"
          >
            <div className="hidden sm:flex flex-col text-right leading-tight">
              <span className="text-xs font-bold text-[#002D72] truncate max-w-[140px]">
                {user?.full_name || 'Corporate User'}
              </span>
              <span className="text-[10px] font-semibold text-[#64748B] uppercase tracking-wider">
                {user?.role?.replace('_', ' ') || 'CUSTOMER'}
              </span>
            </div>
            <div className="h-8 w-8 rounded-[8px] bg-[#002D72] text-[#F9A825] font-bold flex items-center justify-center text-xs shadow-xs">
              {isCustomer ? (
                <Building2 className="h-4 w-4 stroke-[2.2]" />
              ) : (
                <UserCheck className="h-4 w-4 stroke-[2.2]" />
              )}
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-[#64748B] hidden sm:block" />
          </button>

          {/* User Account Dropdown */}
          {roleMenuOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white border border-[#E0DDD6] p-2.5 shadow-lg z-50 animate-in fade-in zoom-in-95 duration-100 rounded-[12px]">
              <div className="px-3 py-2 border-b border-[#E0DDD6]">
                <p className="text-xs font-bold text-[#002D72] truncate">{user?.full_name}</p>
                <p className="text-[11px] text-[#64748B] truncate font-mono mt-0.5">
                  {isCustomer && customer?.omerta_user_number
                    ? customer.omerta_user_number
                    : user?.email}
                </p>
                <div className="mt-1.5 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#EBF3FC] text-[#002D72] border border-[#BFDBFE]">
                  {user?.role?.replace('_', ' ')}
                </div>
              </div>

              <div className="py-1.5 space-y-0.5">
                {isCustomer ? (
                  <>
                    <button
                      onClick={() => {
                        navigate('/customer/dashboard');
                        setRoleMenuOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 rounded-[8px] text-xs font-semibold text-[#475569] hover:bg-[#F4F1EC] hover:text-[#002D72] transition-colors flex items-center gap-2.5 cursor-pointer"
                    >
                      <Activity className="h-4 w-4 text-[#002D72]" />
                      <span>Account Dashboard</span>
                    </button>
                    <button
                      onClick={() => {
                        navigate('/customer/transfer');
                        setRoleMenuOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 rounded-[8px] text-xs font-semibold text-[#475569] hover:bg-[#F4F1EC] hover:text-[#002D72] transition-colors flex items-center gap-2.5 cursor-pointer"
                    >
                      <Send className="h-4 w-4 text-[#F9A825]" />
                      <span>Send Money</span>
                    </button>
                    <button
                      onClick={() => {
                        navigate('/customer/security');
                        setRoleMenuOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 rounded-[8px] text-xs font-semibold text-[#475569] hover:bg-[#F4F1EC] hover:text-[#002D72] transition-colors flex items-center gap-2.5 cursor-pointer"
                    >
                      <ShieldCheck className="h-4 w-4 text-[#10B981]" />
                      <span>Security &amp; Devices</span>
                    </button>
                    <button
                      onClick={() => {
                        navigate('/customer/profile');
                        setRoleMenuOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 rounded-[8px] text-xs font-semibold text-[#475569] hover:bg-[#F4F1EC] hover:text-[#002D72] transition-colors flex items-center gap-2.5 cursor-pointer"
                    >
                      <UserCheck className="h-4 w-4 text-[#1E88E5]" />
                      <span>Customer Profile</span>
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => {
                        navigate('/admin/dashboard');
                        setRoleMenuOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 rounded-[8px] text-xs font-semibold text-[#475569] hover:bg-[#F4F1EC] hover:text-[#002D72] transition-colors flex items-center gap-2.5 cursor-pointer"
                    >
                      <Activity className="h-4 w-4 text-[#002D72]" />
                      <span>Financial Dashboard</span>
                    </button>
                    <button
                      onClick={() => {
                        navigate('/admin/risk-monitoring');
                        setRoleMenuOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 rounded-[8px] text-xs font-semibold text-[#475569] hover:bg-[#F4F1EC] hover:text-[#002D72] transition-colors flex items-center gap-2.5 cursor-pointer"
                    >
                      <ShieldCheck className="h-4 w-4 text-[#F9A825]" />
                      <span>Risk Monitoring</span>
                    </button>
                    <button
                      onClick={() => {
                        navigate('/admin/audit-logs');
                        setRoleMenuOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 rounded-[8px] text-xs font-semibold text-[#475569] hover:bg-[#F4F1EC] hover:text-[#002D72] transition-colors flex items-center gap-2.5 cursor-pointer"
                    >
                      <Lock className="h-4 w-4 text-[#1E88E5]" />
                      <span>Audit Trail</span>
                    </button>
                  </>
                )}
              </div>

              <div className="pt-2 mt-1 border-t border-[#E0DDD6]">
                <button
                  onClick={() => {
                    logout();
                    navigate('/login');
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] text-xs font-bold text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Log out session</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
