import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ArrowLeftRight,
  ShieldAlert,
  FolderSearch,
  Users,
  Wallet,
  Smartphone,
  Share2,
  FileBarChart,
  BarChart3,
  ScrollText,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Send,
  UserCheck,
  Building2,
  Bot,
  LifeBuoy,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  const { user } = useAuth();
  const role = user?.role || 'CUSTOMER';
  const isCustomer = role === 'CUSTOMER';

  const customerNavItems: NavItem[] = [
    { to: '/customer/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/customer/accounts', label: 'Accounts', icon: Wallet },
    { to: '/customer/transfer', label: 'Send Money', icon: Send },
    { to: '/customer/transactions', label: 'Transactions', icon: ArrowLeftRight },
    { to: '/customer/support', label: 'Support & Tickets', icon: LifeBuoy },
    { to: '/customer/security', label: 'Security & Sessions', icon: ShieldCheck },
    { to: '/customer/profile', label: 'Customer Profile', icon: UserCheck },
  ];

  const investigatorNavItems: NavItem[] = [
    { to: '/admin/investigations', label: 'Investigations', icon: FolderSearch },
    { to: '/admin/support-cases', label: 'Cases & Tickets', icon: LifeBuoy },
    { to: '/admin/network-analysis', label: 'Network Intelligence', icon: Share2 },
    { to: '/admin/ai-assistant', label: 'AI Forensics Copilot', icon: Bot, badge: 'RAG' },
    { to: '/admin/audit-logs', label: 'Audit Trail', icon: ScrollText },
  ];

  const analystNavItems: NavItem[] = [
    { to: '/admin/dashboard', label: 'Executive Dashboard', icon: LayoutDashboard },
    { to: '/admin/risk-monitoring', label: 'Risk Monitoring', icon: ShieldAlert, badge: '>40%' },
    { to: '/admin/transactions', label: 'Transactions', icon: ArrowLeftRight },
    { to: '/admin/support-cases', label: 'Cases & Tickets', icon: LifeBuoy },
    { to: '/admin/investigations', label: 'Investigations', icon: FolderSearch },
    { to: '/admin/reports', label: 'Reports', icon: FileBarChart },
    { to: '/admin/ai-assistant', label: 'AI Forensics Copilot', icon: Bot, badge: 'RAG' },
  ];

  const auditorNavItems: NavItem[] = [
    { to: '/admin/support-cases', label: 'Cases & Tickets', icon: LifeBuoy },
    { to: '/admin/audit-logs', label: 'Audit Logs', icon: ScrollText },
    { to: '/admin/reports', label: 'Compliance Reports', icon: FileBarChart },
    { to: '/admin/transactions', label: 'Transactions (Audit)', icon: ArrowLeftRight },
    { to: '/admin/investigations', label: 'Investigations (Audit)', icon: FolderSearch },
  ];

  const adminNavItems: NavItem[] = [
    { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/admin/risk-monitoring', label: 'Risk Monitoring', icon: ShieldAlert, badge: '>40%' },
    { to: '/admin/transactions', label: 'Transactions', icon: ArrowLeftRight },
    { to: '/admin/investigations', label: 'Investigations', icon: FolderSearch },
    { to: '/admin/support-cases', label: 'Cases & Tickets', icon: LifeBuoy },
    { to: '/admin/customers', label: 'Customers', icon: Users },
    { to: '/admin/accounts', label: 'Accounts', icon: Wallet },
    { to: '/admin/devices', label: 'Device Intelligence', icon: Smartphone },
    { to: '/admin/network-analysis', label: 'Network Intelligence', icon: Share2 },
    { to: '/admin/reports', label: 'Reports', icon: FileBarChart },
    { to: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/admin/audit-logs', label: 'Audit Trail', icon: ScrollText },
    { to: '/admin/ai-assistant', label: 'AI Forensics Copilot', icon: Bot, badge: 'RAG' },
    { to: '/admin/settings', label: 'Settings', icon: Settings },
  ];

  let navItems: NavItem[] = customerNavItems;
  if (role === 'ADMINISTRATOR' || role === 'SUB_ADMINISTRATOR') {
    navItems = adminNavItems;
  } else if (role === 'SENIOR_INVESTIGATOR' || role === 'INVESTIGATOR') {
    navItems = investigatorNavItems;
  } else if (role === 'FRAUD_ANALYST') {
    navItems = analystNavItems;
  } else if (role === 'AUDITOR' || role === 'COMPLIANCE_AUDITOR') {
    navItems = auditorNavItems;
  }

  return (
    <aside
      className={`fixed left-0 top-0 bottom-0 z-40 flex flex-col bg-white border-r border-[#E0DDD6] shadow-xs transition-all duration-200 ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-[#E0DDD6]">
        <NavLink
          to={isCustomer ? '/customer/dashboard' : '/admin/dashboard'}
          className="flex items-center gap-3 overflow-hidden group"
        >
          <div className="flex items-center justify-center h-10 w-10 min-w-[2.5rem] rounded-[10px] bg-[#002D72] text-[#F9A825] shadow-xs transition-transform group-hover:scale-105">
            {isCustomer ? (
              <Building2 className="h-5 w-5 stroke-[2.2]" />
            ) : (
              <ShieldCheck className="h-5 w-5 stroke-[2.2]" />
            )}
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-base font-extrabold tracking-tight text-[#002D72]">
                OMERTA<span className="text-[#F9A825]">.AI</span>
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B]">
                {isCustomer ? 'Corporate Banking' : 'Financial Intelligence'}
              </span>
            </div>
          )}
        </NavLink>
        <button
          onClick={onToggle}
          className="hidden md:flex p-1.5 text-[#64748B] hover:text-[#002D72] rounded-[8px] hover:bg-[#F4F1EC] transition-colors cursor-pointer"
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-[10px] text-xs font-semibold transition-all duration-150 group relative ${
                isActive
                  ? 'bg-[#FFF9E6] text-[#002D72] font-bold border-l-4 border-l-[#F9A825] shadow-xs'
                  : 'text-[#475569] hover:text-[#002D72] hover:bg-[#F4F1EC]'
              } ${collapsed ? 'justify-center px-2' : ''}`
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={`h-4.5 w-4.5 min-w-[1.125rem] transition-colors ${
                    isActive ? 'text-[#002D72]' : 'text-[#64748B] group-hover:text-[#002D72]'
                  }`}
                />
                {!collapsed && (
                  <span className="flex-1 truncate tracking-tight">{item.label}</span>
                )}
                {!collapsed && item.badge && (
                  <span
                    className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded-full ${
                      isActive
                        ? 'bg-[#F9A825] text-[#002D72]'
                        : 'bg-[#F4F1EC] text-[#002D72] border border-[#E0DDD6]'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Sidebar Footer */}
      <div className="p-3 border-t border-[#E0DDD6] bg-[#F4F1EC]/60">
        {!collapsed ? (
          <div className="p-2.5 rounded-[10px] bg-white border border-[#E0DDD6] shadow-xs space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#64748B] font-bold uppercase tracking-wider">System State</span>
              <span className="inline-flex items-center gap-1 font-bold text-[#065F46] text-[10px] uppercase bg-[#ECFDF5] px-2 py-0.5 rounded-full border border-[#A7F3D0]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#10B981] animate-pulse" />
                Protected
              </span>
            </div>
            <p className="text-[11px] text-[#475569] font-medium leading-tight truncate">
              {isCustomer ? 'AML Shield Active' : 'Real-time Risk Engine 24/7'}
            </p>
          </div>
        ) : (
          <div className="flex justify-center" title="Platform Protected">
            <div className="h-2.5 w-2.5 rounded-full bg-[#10B981] animate-pulse" />
          </div>
        )}
      </div>
    </aside>
  );
};
