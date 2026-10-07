import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ArrowLeftRight,
  ShieldAlert,
  Wallet,
  UserCheck,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const MobileNav: React.FC = () => {
  const { user } = useAuth();
  const isCustomer = user?.role === 'CUSTOMER';

  const customerItems = [
    { to: '/customer/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/customer/transactions', label: 'Transactions', icon: ArrowLeftRight },
    { to: '/customer/accounts', label: 'Accounts', icon: Wallet },
    { to: '/customer/profile', label: 'Account', icon: UserCheck },
  ];

  const adminItems = [
    { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/admin/transactions', label: 'Transactions', icon: ArrowLeftRight },
    { to: '/admin/risk-monitoring', label: 'Risk', icon: ShieldAlert },
    { to: '/admin/accounts', label: 'Account', icon: Wallet },
  ];

  const navItems = isCustomer ? customerItems : adminItems;

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 h-[72px] bg-white border-t border-[#E0DDD6] px-4 flex items-center justify-around shadow-lg"
      aria-label="Mobile Navigation"
    >
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center gap-1 w-16 py-1 transition-colors ${
              isActive ? 'text-[#1E88E5]' : 'text-[#666666] hover:text-[#002D72]'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <item.icon
                className={`h-5 w-5 transition-transform ${
                  isActive ? 'scale-110 text-[#1E88E5]' : 'text-[#666666]'
                }`}
              />
              <span className="text-[9px] font-bold uppercase tracking-wider text-center truncate">
                {item.label}
              </span>
              {isActive && (
                <span className="w-1.5 h-1.5 rounded-full bg-[#1E88E5]" />
              )}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
};
