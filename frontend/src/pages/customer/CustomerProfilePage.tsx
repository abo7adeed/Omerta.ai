import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  Copy,
  Check,
  Globe,
  Wallet,
  ShieldCheck,
  Mail,
  Calendar,
  Phone,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import {
  Card,
  Button,
} from '../../components/ui';
import type { CustomerProfile } from '../../types';

const COUNTRY_NAMES: Record<string, { label: string; flag: string }> = {
  EG: { label: 'Egypt (EG)', flag: '🇪🇬' },
  SA: { label: 'Saudi Arabia (SA)', flag: '🇸🇦' },
  AE: { label: 'United Arab Emirates (AE)', flag: '🇦🇪' },
  US: { label: 'United States (US)', flag: '🇺🇸' },
  GB: { label: 'United Kingdom (GB)', flag: '🇬🇧' },
  DE: { label: 'Germany (DE)', flag: '🇩🇪' },
  FR: { label: 'France (FR)', flag: '🇫🇷' },
  CA: { label: 'Canada (CA)', flag: '🇨🇦' },
  KW: { label: 'Kuwait (KW)', flag: '🇰🇼' },
  QA: { label: 'Qatar (QA)', flag: '🇶🇦' },
};

export const CustomerProfilePage: React.FC = () => {
  const { user, customer } = useAuth();
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [copied, setCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true);
      try {
        const res = await api.getCustomerProfile();
        setProfile(res);
      } catch {
        setProfile(customer);
      } finally {
        setIsLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const handleCopyUserNumber = () => {
    const num = profile?.omerta_user_number || customer?.omerta_user_number;
    if (num) {
      navigator.clipboard.writeText(num);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const currentProfile = profile || customer;
  const countryCode = currentProfile?.declared_country || 'EG';
  const countryInfo = COUNTRY_NAMES[countryCode] || { label: `${countryCode}`, flag: '🌐' };

  if (isLoading && !currentProfile) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-[var(--color-text-secondary)]">
        <Loader2 className="h-10 w-10 animate-spin text-[var(--color-sapphire)] mb-4" />
        <p className="text-sm font-semibold text-[var(--color-sapphire)]">Loading customer profile...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <Card className="p-6 md:p-8">
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-sapphire)] flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-[var(--color-sapphire)] text-[var(--color-gold)] shadow-sm">
            <UserCheck className="h-6 w-6 stroke-[2.2]" />
          </div>
          <span>Customer Profile</span>
        </h1>
        <p className="text-xs text-[var(--color-text-secondary)] mt-2 font-medium">
          Your verified banking identity, phone credentials, and unique Omerta transfer identifier
        </p>
      </Card>

      {/* Main Profile Card */}
      <Card className="p-6 md:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-2xl bg-[var(--color-sapphire)] text-[var(--color-gold)] font-extrabold flex items-center justify-center text-2xl shadow-sm">
              {currentProfile?.name?.charAt(0) || user?.full_name?.charAt(0) || 'C'}
            </div>
            <div>
              <h2 className="text-xl font-bold text-[var(--color-sapphire)]">{currentProfile?.name || user?.full_name}</h2>
              <p className="text-xs text-[var(--color-text-secondary)] flex items-center gap-1.5 mt-1 font-medium">
                <Mail className="h-4 w-4 text-[var(--color-royal-blue)]" />
                <span>{currentProfile?.email || user?.email}</span>
              </p>
            </div>
          </div>

          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            {currentProfile?.status || 'ACTIVE'}
          </span>
        </div>

        {/* Unique Omerta User Number Box */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)]">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                Unique Omerta User Number
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-100 text-[var(--color-sapphire)] border border-blue-200">
                P2P Transfer ID
              </span>
            </div>
            <p className="font-mono text-xl font-extrabold text-[var(--color-sapphire)] tracking-wider">
              {currentProfile?.omerta_user_number || 'OMR-1092-4821'}
            </p>
            <p className="text-xs text-[var(--color-text-secondary)] font-medium">
              Share this identifier or your registered mobile phone with other users to receive transfers.
            </p>
          </div>

          <Button
            size="sm"
            variant="secondary"
            onClick={handleCopyUserNumber}
            className="shrink-0"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 text-emerald-600 mr-1.5" />
                <span className="text-emerald-700 font-bold">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 text-[var(--color-sapphire)] mr-1.5" />
                <span>Copy Number</span>
              </>
            )}
          </Button>
        </div>

        {/* Profile Attributes */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Registered Mobile Phone */}
          <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] flex items-center gap-1.5">
              <Phone className="h-4 w-4 text-[var(--color-sapphire)]" /> Registered Mobile Phone
            </span>
            <p className="text-sm font-bold font-mono text-[var(--color-sapphire)] flex items-center gap-2">
              <span>{countryInfo.flag}</span>
              <span>{currentProfile?.phone || '+20 10 1111 2222'}</span>
            </p>
            <p className="text-[11px] text-[var(--color-text-secondary)] font-medium">
              Verified mobile identifier for direct phone transfers.
            </p>
          </div>

          {/* Account Verification Tier */}
          <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-emerald-600" /> Verification Status
            </span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-emerald-700">Tier 1 Verified</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300">
                Full Access
              </span>
            </div>
            <p className="text-[11px] text-[var(--color-text-secondary)] font-medium">
              Standard banking tier with peer-to-peer sending &amp; receiving.
            </p>
          </div>

          {/* Declared Country */}
          <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] flex items-center gap-1.5">
              <Globe className="h-4 w-4 text-[var(--color-royal-blue)]" /> Declared Country
            </span>
            <p className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-2">
              <span>{countryInfo.flag}</span>
              <span>{countryInfo.label}</span>
            </p>
            <p className="text-[11px] text-[var(--color-text-secondary)] font-medium">
              Primary banking jurisdiction for regional clearing.
            </p>
          </div>

          {/* Preferred Currency */}
          <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] flex items-center gap-1.5">
              <Wallet className="h-4 w-4 text-[var(--color-gold)]" /> Preferred Currency
            </span>
            <p className="text-sm font-bold text-[var(--color-sapphire)]">
              {currentProfile?.preferred_currency || 'EGP'}
            </p>
            <p className="text-[11px] text-[var(--color-text-secondary)] font-medium">
              Default denomination for new accounts and transfers.
            </p>
          </div>

          {/* Member Since */}
          <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-1.5 sm:col-span-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] flex items-center gap-1.5">
              <Calendar className="h-4 w-4 text-[var(--color-sapphire)]" /> Member Since
            </span>
            <p className="text-sm font-bold text-[var(--color-text-primary)]">
              {currentProfile?.member_since
                ? new Date(currentProfile.member_since).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })
                : 'January 2026'}
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
