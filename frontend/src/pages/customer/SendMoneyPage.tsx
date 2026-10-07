import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Send,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  ArrowLeft,
  Copy,
  Check,
  RotateCcw,
  Lock,
  Eye,
  EyeOff,
  ChevronDown,
  AlertTriangle,
  RefreshCw,
  Smartphone,
  Hash,
  KeyRound,
} from 'lucide-react';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { collectNetworkTelemetry } from '../../utils/telemetry';
import {
  Card,
  Button,
  Input,
  Select,
  Modal,
  Alert,
} from '../../components/ui';
import type { CustomerAccount, RecipientLookupResult, TransferReceipt } from '../../types';

interface CountryOption {
  code: string;
  name: string;
  dialCode: string;
  flag: string;
}

const COUNTRY_OPTIONS: CountryOption[] = [
  { code: 'EG', name: 'Egypt', dialCode: '+20', flag: '🇪🇬' },
  { code: 'SA', name: 'Saudi Arabia', dialCode: '+966', flag: '🇸🇦' },
  { code: 'AE', name: 'United Arab Emirates', dialCode: '+971', flag: '🇦🇪' },
  { code: 'KW', name: 'Kuwait', dialCode: '+965', flag: '🇰🇼' },
  { code: 'QA', name: 'Qatar', dialCode: '+974', flag: '🇶🇦' },
  { code: 'BH', name: 'Bahrain', dialCode: '+973', flag: '🇧🇭' },
  { code: 'OM', name: 'Oman', dialCode: '+968', flag: '🇴🇲' },
  { code: 'JO', name: 'Jordan', dialCode: '+962', flag: '🇯🇴' },
  { code: 'LB', name: 'Lebanon', dialCode: '+961', flag: '🇱🇧' },
  { code: 'IQ', name: 'Iraq', dialCode: '+964', flag: '🇮🇶' },
  { code: 'US', name: 'United States', dialCode: '+1', flag: '🇺🇸' },
  { code: 'GB', name: 'United Kingdom', dialCode: '+44', flag: '🇬🇧' },
  { code: 'DE', name: 'Germany', dialCode: '+49', flag: '🇩🇪' },
  { code: 'FR', name: 'France', dialCode: '+33', flag: '🇫🇷' },
  { code: 'IT', name: 'Italy', dialCode: '+39', flag: '🇮🇹' },
  { code: 'TR', name: 'Turkey', dialCode: '+90', flag: '🇹🇷' },
  { code: 'JP', name: 'Japan', dialCode: '+81', flag: '🇯🇵' },
];

export const SendMoneyPage: React.FC = () => {
  const { customer, refreshCustomerProfile } = useAuth();
  const navigate = useNavigate();

  // Multi-step transfer state: 1 = Recipient, 2 = Amount & Account, 3 = Confirm, 4 = Receipt
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Form states
  const [inputMode, setInputMode] = useState<'phone' | 'omerta_number'>('phone');
  const [selectedCountry, setSelectedCountry] = useState<CountryOption>(COUNTRY_OPTIONS[0]);
  const [countryDropdownOpen, setCountryDropdownOpen] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');

  const [phoneInput, setPhoneInput] = useState('');
  const [omertaNumberInput, setOmertaNumberInput] = useState('');

  const [lookupResult, setLookupResult] = useState<RecipientLookupResult | null>(null);
  const [isLookingUp, setIsLookingUp] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const [accounts, setAccounts] = useState<CustomerAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<CustomerAccount | null>(null);
  const [amount, setAmount] = useState<string>('');
  const [note, setNote] = useState<string>('');
  const [authPassword, setAuthPassword] = useState('');
  const [showAuthPassword, setShowAuthPassword] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<TransferReceipt | null>(null);
  const [copiedReceipt, setCopiedReceipt] = useState(false);

  // Security modals & status
  const [vpnModalOpen, setVpnModalOpen] = useState(false);
  const [vpnDetails, setVpnDetails] = useState<{ isp?: string; country?: string; org?: string; reason?: string } | null>(null);
  const [isRecheckingVpn, setIsRecheckingVpn] = useState(false);

  const [transferBlockedModalOpen, setTransferBlockedModalOpen] = useState(false);
  const [transferBlockedMessage, setTransferBlockedMessage] = useState<string>('');
  const [isTransferBlocked, setIsTransferBlocked] = useState<boolean>(false);

  // Restore & Set New Transfer Password Modal
  const [passwordChangeModalOpen, setPasswordChangeModalOpen] = useState(false);
  const [newTransferPassword, setNewTransferPassword] = useState('');
  const [confirmTransferPassword, setConfirmTransferPassword] = useState('');
  const [passwordModalLoading, setPasswordModalLoading] = useState(false);
  const [passwordModalError, setPasswordModalError] = useState<string | null>(null);
  const [passwordModalSuccess, setPasswordModalSuccess] = useState(false);
  const [showNewPasswordText, setShowNewPasswordText] = useState(false);

  // Load customer accounts and fresh profile status
  useEffect(() => {
    const fetchAccountsAndStatus = async () => {
      try {
        const [accRes, profileRes] = await Promise.allSettled([
          api.getCustomerAccounts(),
          api.getCustomerProfile(),
        ]);

        if (accRes.status === 'fulfilled') {
          setAccounts(accRes.value);
          if (accRes.value.length > 0) {
            setSelectedAccount(accRes.value[0]);
          }
        }
        if (profileRes.status === 'fulfilled' && profileRes.value) {
          if (profileRes.value.transfer_status === 'BLOCKED') {
            setIsTransferBlocked(true);
            setTransferBlockedModalOpen(true);
            setTransferBlockedMessage(
              'Transfers are currently locked due to 3 incorrect transfer password attempts. Please submit your National ID verification in Support to restore privileges.'
            );
          } else if (profileRes.value.require_transfer_password_change) {
            setPasswordChangeModalOpen(true);
          }
        }
      } catch {
        const fallback: CustomerAccount[] = [
          { account_id: 'ACC-1001', account_type: 'CHECKING', currency: 'EGP', balance: 50000.0, status: 'ACTIVE' },
        ];
        setAccounts(fallback);
        setSelectedAccount(fallback[0]);
      }
    };
    fetchAccountsAndStatus();
  }, []);

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
      if (refreshCustomerProfile) {
        await refreshCustomerProfile();
      }

      setTimeout(() => {
        setPasswordChangeModalOpen(false);
        setPasswordModalSuccess(false);
        setNewTransferPassword('');
        setConfirmTransferPassword('');
      }, 1800);
    } catch (err: any) {
      setPasswordModalError(err.message || 'Failed to update transfer password.');
    } finally {
      setPasswordModalLoading(false);
    }
  };

  const isPasswordChangeRequired = Boolean(customer?.require_transfer_password_change);

  // Quick recipient lookup handler
  const handleLookup = async (targetValue?: string) => {
    if (isTransferBlocked) {
      setLookupError('Transfer services are currently restricted due to security hold. Please contact support.');
      return;
    }

    if (isPasswordChangeRequired) {
      setPasswordModalError(null);
      setPasswordChangeModalOpen(true);
      setLookupError('Action Required: Please set your new transfer password first before sending money.');
      return;
    }

    let valueToQuery = '';
    if (targetValue) {
      valueToQuery = targetValue.trim();
    } else if (inputMode === 'phone') {
      const cleanPhoneDigits = phoneInput.replace(/\D/g, '').replace(/^0+/, '');
      if (!cleanPhoneDigits) {
        setLookupError('Please enter the recipient mobile phone number.');
        return;
      }
      valueToQuery = `${selectedCountry.dialCode}${cleanPhoneDigits}`;
    } else {
      valueToQuery = omertaNumberInput.trim().toUpperCase();
      if (!valueToQuery) {
        setLookupError('Please enter the recipient Omerta User Number (e.g. OMR-3847-1920).');
        return;
      }
    }

    const cleanUpper = valueToQuery.toUpperCase();
    if (
      cleanUpper === customer?.omerta_user_number ||
      (customer?.phone && valueToQuery.replace(/\s+/g, '') === customer.phone.replace(/\s+/g, ''))
    ) {
      setLookupError('You cannot transfer funds to your own account or phone number.');
      return;
    }

    setIsLookingUp(true);
    setLookupError(null);
    try {
      const res = await api.lookupRecipient(valueToQuery);
      setLookupResult(res);
      setStep(2);
    } catch (err: any) {
      setLookupError(err.message || 'Recipient not found. Please verify the mobile number or Omerta User Number.');
      setLookupResult(null);
    } finally {
      setIsLookingUp(false);
    }
  };

  // Quick preset buttons for amounts
  const handlePresetAmount = (fraction: number) => {
    if (!selectedAccount) return;
    const computed = (selectedAccount.balance * fraction).toFixed(2);
    setAmount(computed);
  };

  // Re-check VPN connection from modal
  const handleRecheckVpnConnection = async () => {
    setIsRecheckingVpn(true);
    try {
      const telemetry = await collectNetworkTelemetry('EG');
      if (!telemetry.is_vpn) {
        setVpnModalOpen(false);
        setVpnDetails(null);
        setSubmitError(null);
        handleExecuteTransfer();
      } else {
        setVpnDetails({
          isp: telemetry.isp,
          country: telemetry.country,
          org: telemetry.org,
          reason: telemetry.vpn_reason || 'Commercial VPN/Proxy tunnel still detected.',
        });
      }
    } finally {
      setIsRecheckingVpn(false);
    }
  };

  // Execute transfer
  const handleExecuteTransfer = async () => {
    if (!selectedAccount || !lookupResult || !amount) return;
    if (!authPassword) {
      setSubmitError('Please enter your dedicated transfer password to authorize the transfer.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const telemetry = await collectNetworkTelemetry('EG');

      if (telemetry.is_vpn) {
        setVpnDetails({
          isp: telemetry.isp,
          country: telemetry.country,
          org: telemetry.org,
          reason: telemetry.vpn_reason || 'Encrypted proxy or datacenter tunnel observed.',
        });
        setVpnModalOpen(true);
        setIsSubmitting(false);
        return;
      }

      const res = await api.initiateTransfer({
        sender_account_id: selectedAccount.account_id,
        recipient_user_number: lookupResult.omerta_user_number,
        amount: parseFloat(amount),
        currency: selectedAccount.currency,
        note: note.trim() || undefined,
        password: authPassword,
        is_vpn: telemetry.is_vpn,
        client_ip: telemetry.ip,
        country: telemetry.country,
        isp: telemetry.isp,
        org: telemetry.org,
        browser_timezone: telemetry.browser_timezone,
        ip_timezone: telemetry.ip_timezone,
      });

      setReceipt(res);
      setStep(4);
    } catch (err: any) {
      if (
        (err?.status === 403 || err?.status === 401) &&
        (err?.message?.includes('BLOCKED') ||
          err?.message?.includes('3 consecutive') ||
          err?.message?.includes('security hold') ||
          err?.data?.detail?.error === 'TRANSFER_BLOCKED_SECURITY_HOLD' ||
          err?.data?.detail?.error === 'TRANSFER_BLOCKED')
      ) {
        setIsTransferBlocked(true);
        setTransferBlockedMessage(
          err.message ||
            'Security Alert: You have entered your transfer password incorrectly 3 times. Money movement has been placed on security hold. You remain logged in. Please contact Customer Support to verify your identity and restore transfer access.'
        );
        setTransferBlockedModalOpen(true);
      } else if (err?.message?.includes('VPN') || err?.error === 'VPN_TRANSFER_BLOCKED') {
        setVpnDetails({
          isp: 'VPN / Datacenter Gateway',
          country: 'Commercial Proxy',
          reason: err.message,
        });
        setVpnModalOpen(true);
      } else {
        setSubmitError(err.message || 'Transfer failed. Please check your available balance and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyReceipt = () => {
    if (receipt) {
      const text = `Omerta.ai Transfer Receipt\nID: ${receipt.transfer_id}\nAmount: ${receipt.formatted_amount}\nTo: ${receipt.recipient.name} (${receipt.recipient.omerta_user_number})\nDate: ${new Date(receipt.created_at).toLocaleString()}`;
      navigator.clipboard.writeText(text);
      setCopiedReceipt(true);
      setTimeout(() => setCopiedReceipt(false), 2000);
    }
  };

  const resetForm = () => {
    setPhoneInput('');
    setOmertaNumberInput('');
    setLookupResult(null);
    setAmount('');
    setNote('');
    setAuthPassword('');
    setSubmitError(null);
    setReceipt(null);
    setStep(1);
  };

  const filteredCountries = COUNTRY_OPTIONS.filter(
    (c) =>
      c.name.toLowerCase().includes(countrySearch.toLowerCase()) ||
      c.dialCode.includes(countrySearch) ||
      c.code.toLowerCase().includes(countrySearch.toLowerCase())
  );

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Page Header */}
      <Card className="p-6 md:p-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-sapphire)] flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[var(--color-sapphire)] text-[var(--color-gold)] shadow-sm">
              <Send className="h-6 w-6 stroke-[2.2]" />
            </div>
            <span>Send Money</span>
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2 font-medium">
            Simulated peer-to-peer transfer by Mobile Number or Omerta User #
          </p>
        </div>

        {/* Step Indicator */}
        <div className="hidden sm:flex items-center gap-2 text-xs font-bold text-[var(--color-text-secondary)]">
          <span className={`px-3 py-1 rounded-full font-bold ${step >= 1 ? 'bg-[var(--color-gold)] text-[var(--color-sapphire)]' : 'bg-[var(--color-secondary-surface)] text-[var(--color-text-muted)]'}`}>1</span>
          <span className="text-[var(--color-border)]">―</span>
          <span className={`px-3 py-1 rounded-full font-bold ${step >= 2 ? 'bg-[var(--color-gold)] text-[var(--color-sapphire)]' : 'bg-[var(--color-secondary-surface)] text-[var(--color-text-muted)]'}`}>2</span>
          <span className="text-[var(--color-border)]">―</span>
          <span className={`px-3 py-1 rounded-full font-bold ${step >= 3 ? 'bg-[var(--color-gold)] text-[var(--color-sapphire)]' : 'bg-[var(--color-secondary-surface)] text-[var(--color-text-muted)]'}`}>3</span>
        </div>
      </Card>

      {/* Transfer Blocked Alert Card */}
      {isTransferBlocked && (
        <Card className="p-6 bg-rose-50/90 border-rose-300 space-y-4">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-rose-100 text-rose-700 shrink-0 mt-0.5">
              <AlertTriangle className="h-6 w-6 stroke-[2.2]" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-rose-950">
                Transfer Capabilities Suspended (Security Hold)
              </h3>
              <p className="text-xs text-rose-900 leading-relaxed font-medium">
                Money transfers are temporarily disabled following 3 failed transfer password attempts. Your login session is secure, and you can still view balances, transactions, and statements.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={() => navigate('/customer/support?reason=TRANSFER_BLOCKED')}
            >
              <span>Contact Support &amp; Verify ID</span>
              <ArrowRight className="h-4 w-4 ml-1.5" />
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => navigate('/customer/dashboard')}
            >
              Back to Dashboard
            </Button>
          </div>
        </Card>
      )}

      {/* Transfer Privileges Restored - Password Update Required Alert Card */}
      {isPasswordChangeRequired && !isTransferBlocked && (
        <Card className="p-6 bg-amber-50/90 border-amber-300 space-y-4">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-amber-100 text-amber-800 shrink-0 mt-0.5">
              <KeyRound className="w-6 h-6 stroke-[2.2]" />
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-amber-950">
                  Action Required: Set New Transfer Password
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-100 text-rose-800 border border-rose-200">
                  Send Money Disabled
                </span>
              </div>
              <p className="text-xs text-amber-900 leading-relaxed font-medium">
                Compliance has verified your identity and restored transfer privileges. Sending money remains disabled until you set your new transfer password.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => {
                setPasswordModalError(null);
                setPasswordChangeModalOpen(true);
              }}
            >
              <Lock className="h-4 w-4 mr-1.5" />
              <span>Set New Transfer Password Now</span>
              <ArrowRight className="h-4 w-4 ml-1.5" />
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => navigate('/customer/dashboard')}
            >
              Back to Dashboard
            </Button>
          </div>
        </Card>
      )}

      {/* STEP 1: Enter Recipient */}
      {step === 1 && (
        <Card className="p-6 md:p-8 space-y-6">
          {/* Mode Tabs */}
          <div className="flex items-center gap-2 p-1.5 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)]">
            <button
              type="button"
              onClick={() => {
                setInputMode('phone');
                setLookupError(null);
              }}
              className={`flex-1 py-2.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                inputMode === 'phone'
                  ? 'bg-[var(--color-sapphire)] text-white shadow-xs'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-sapphire)]'
              }`}
            >
              <Smartphone className="w-4 h-4" />
              <span>Mobile Phone</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setInputMode('omerta_number');
                setLookupError(null);
              }}
              className={`flex-1 py-2.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                inputMode === 'omerta_number'
                  ? 'bg-[var(--color-sapphire)] text-white shadow-xs'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-sapphire)]'
              }`}
            >
              <Hash className="w-4 h-4" />
              <span>Omerta User Number</span>
            </button>
          </div>

          {/* Phone Mode */}
          {inputMode === 'phone' ? (
            <div className="space-y-2.5">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                Recipient Country &amp; Mobile Phone
              </label>

              <div className="flex gap-2.5 items-center">
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setCountryDropdownOpen(!countryDropdownOpen)}
                    className="flex items-center gap-2 px-3.5 py-2.5 bg-white hover:bg-[var(--color-secondary-surface)] border border-[var(--color-border)] rounded-lg text-xs font-bold text-[var(--color-text-primary)] cursor-pointer shrink-0 min-h-[44px]"
                  >
                    <span className="text-xl leading-none">{selectedCountry.flag}</span>
                    <span className="font-mono text-[var(--color-sapphire)] font-bold">{selectedCountry.dialCode}</span>
                    <ChevronDown className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
                  </button>

                  {countryDropdownOpen && (
                    <div className="absolute left-0 top-full mt-2 w-72 max-h-64 overflow-y-auto bg-white border border-[var(--color-border)] rounded-xl shadow-lg z-50 p-2 space-y-1">
                      <div className="p-1 sticky top-0 bg-white z-10">
                        <Input
                          placeholder="Search country..."
                          value={countrySearch}
                          onChange={(e) => setCountrySearch(e.target.value)}
                          autoFocus
                        />
                      </div>
                      {filteredCountries.map((c) => (
                        <button
                          key={c.code}
                          type="button"
                          onClick={() => {
                            setSelectedCountry(c);
                            setCountryDropdownOpen(false);
                            setCountrySearch('');
                          }}
                          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                            selectedCountry.code === c.code
                              ? 'bg-blue-50 text-[var(--color-sapphire)] font-bold'
                              : 'text-[var(--color-text-primary)] hover:bg-[var(--color-secondary-surface)]'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-base">{c.flag}</span>
                            <span>{c.name}</span>
                          </div>
                          <span className="font-mono text-[11px] text-[var(--color-text-muted)]">{c.dialCode}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="relative flex-1">
                  <Input
                    type="tel"
                    value={phoneInput}
                    onChange={(e) => {
                      setPhoneInput(e.target.value);
                      setLookupError(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleLookup();
                      }
                    }}
                    placeholder="e.g. 10 2222 3333"
                    autoFocus
                  />
                </div>
              </div>

              <p className="text-[11px] text-[var(--color-text-secondary)] font-medium">
                Destination: <span className="text-[var(--color-sapphire)] font-bold">{selectedCountry.flag} {selectedCountry.name} ({selectedCountry.dialCode})</span>.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              <Input
                label="Recipient Omerta User Number"
                type="text"
                value={omertaNumberInput}
                onChange={(e) => {
                  setOmertaNumberInput(e.target.value);
                  setLookupError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleLookup();
                  }
                }}
                placeholder="e.g. OMR-3847-1920"
                autoFocus
              />
              <p className="text-[11px] text-[var(--color-text-secondary)] font-medium">
                Enter unique Omerta User Number (e.g. <span className="text-[var(--color-sapphire)] font-mono font-bold">OMR-3847-1920</span>).
              </p>
            </div>
          )}

          <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-[var(--color-sapphire)]">
              <ShieldCheck className="h-4 w-4 text-[var(--color-sapphire)]" />
              <span>Real-Time Ledger Verification</span>
            </div>
            <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed font-medium">
              Recipients are verified automatically against the database ledger. Double-entry funds transfer will credit the recipient instantly upon confirmation.
            </p>
          </div>

          {lookupError && (
            <Alert
              variant="danger"
              icon={<AlertCircle className="h-4 w-4" />}
              message={lookupError}
            />
          )}

          {isPasswordChangeRequired ? (
            <Button
              type="button"
              variant="primary"
              size="default"
              onClick={() => {
                setPasswordModalError(null);
                setPasswordChangeModalOpen(true);
              }}
              className="w-full"
            >
              <Lock className="h-4 w-4 mr-1.5" />
              <span>Set Transfer Password to Enable Transfers</span>
              <ArrowRight className="h-4 w-4 ml-1.5" />
            </Button>
          ) : (
            <Button
              type="button"
              variant="primary"
              size="default"
              onClick={() => handleLookup()}
              isLoading={isLookingUp}
              disabled={inputMode === 'phone' ? !phoneInput.trim() : !omertaNumberInput.trim()}
              className="w-full"
            >
              <span>Verify Recipient &amp; Continue</span>
              <ArrowRight className="h-4 w-4 ml-1.5" />
            </Button>
          )}
        </Card>
      )}

      {/* STEP 2: Amount & Account Selection */}
      {step === 2 && lookupResult && (
        <Card className="p-6 md:p-8 space-y-6">
          {/* Verified Recipient Banner */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-emerald-50/80 border border-emerald-300/80">
            <div className="flex items-center gap-3.5">
              <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700">
                <CheckCircle2 className="h-6 w-6 stroke-[2.2]" />
              </div>
              <div>
                <span className="text-sm font-bold text-[var(--color-sapphire)] block">
                  Verified: {lookupResult.display_name}
                </span>
                <div className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)] mt-0.5 font-medium">
                  <span className="font-mono text-[var(--color-sapphire)] font-bold">{lookupResult.omerta_user_number}</span>
                  {lookupResult.phone_masked && (
                    <>
                      <span>•</span>
                      <span className="font-mono text-emerald-700 font-bold">{lookupResult.phone_masked}</span>
                    </>
                  )}
                  <span>•</span>
                  <span>{lookupResult.country}</span>
                </div>
              </div>
            </div>

            <Button
              size="sm"
              variant="ghost"
              onClick={() => setStep(1)}
            >
              Change
            </Button>
          </div>

          {/* Source Account Selection */}
          <Select
            label="From Account"
            value={selectedAccount?.account_id}
            onChange={(e) => {
              const acc = accounts.find((a) => a.account_id === e.target.value);
              if (acc) setSelectedAccount(acc);
            }}
            options={accounts.map((acc) => ({
              value: acc.account_id,
              label: `${acc.account_type} (${acc.account_id}) — Available: ${acc.balance.toLocaleString()} ${acc.currency}`,
            }))}
          />

          {/* Amount Input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold">
              <label className="uppercase tracking-wider text-[var(--color-text-muted)]">Transfer Amount</label>
              <span className="text-[var(--color-text-secondary)]">
                Available: <strong className="text-[var(--color-sapphire)] font-mono">{selectedAccount?.balance.toLocaleString()} {selectedAccount?.currency}</strong>
              </span>
            </div>

            <Input
              type="number"
              step="0.01"
              min="1"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              icon={<span className="font-bold text-xs text-[var(--color-sapphire)]">{selectedAccount?.currency}</span>}
              autoFocus
            />

            {/* Preset Amount Chips */}
            <div className="grid grid-cols-4 gap-2 pt-1">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => handlePresetAmount(0.1)}
              >
                10%
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => handlePresetAmount(0.25)}
              >
                25%
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => handlePresetAmount(0.5)}
              >
                50%
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => handlePresetAmount(1.0)}
              >
                Max Balance
              </Button>
            </div>
          </div>

          {/* Optional Note */}
          <Input
            label="Transfer Reference / Note (Optional)"
            type="text"
            maxLength={100}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Shared expenses, invoice payment, gift..."
          />

          {submitError && (
            <Alert
              variant="danger"
              icon={<AlertCircle className="h-4 w-4" />}
              message={submitError}
            />
          )}

          <div className="flex items-center gap-3 pt-2">
            <Button
              type="button"
              variant="secondary"
              size="default"
              onClick={() => setStep(1)}
            >
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Back
            </Button>

            <Button
              type="button"
              variant="primary"
              size="default"
              onClick={() => setStep(3)}
              disabled={Boolean(!amount || parseFloat(amount) <= 0 || (selectedAccount && parseFloat(amount) > selectedAccount.balance))}
              className="flex-1"
            >
              <span>Review Details</span>
              <ArrowRight className="h-4 w-4 ml-1.5" />
            </Button>
          </div>
        </Card>
      )}

      {/* STEP 3: Review & Explicit Confirmation */}
      {step === 3 && lookupResult && selectedAccount && (
        <Card className="p-6 md:p-8 space-y-6">
          <div className="text-center py-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Total Transfer Amount</span>
            <div className="text-4xl font-extrabold text-[var(--color-sapphire)] font-mono my-2 font-tabular">
              {parseFloat(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {selectedAccount.currency}
            </div>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
              Fee: $0.00 (Zero Fee Demo)
            </span>
          </div>

          {/* Transfer Summary Table */}
          <div className="rounded-xl border border-[var(--color-border)] divide-y divide-[var(--color-border)] text-xs overflow-hidden bg-[var(--color-secondary-surface)]">
            <div className="p-3.5 flex justify-between items-center font-medium">
              <span className="text-[var(--color-text-muted)] font-bold">Recipient Name</span>
              <span className="font-bold text-[var(--color-sapphire)]">{lookupResult.display_name}</span>
            </div>
            <div className="p-3.5 flex justify-between items-center font-medium">
              <span className="text-[var(--color-text-muted)] font-bold">Recipient Identifier</span>
              <span className="font-mono font-bold text-[var(--color-sapphire)]">{lookupResult.omerta_user_number}</span>
            </div>
            {lookupResult.phone_masked && (
              <div className="p-3.5 flex justify-between items-center font-medium">
                <span className="text-[var(--color-text-muted)] font-bold">Recipient Phone</span>
                <span className="font-mono font-bold text-emerald-700">{lookupResult.phone_masked}</span>
              </div>
            )}
            <div className="p-3.5 flex justify-between items-center font-medium">
              <span className="text-[var(--color-text-muted)] font-bold">From Account</span>
              <span className="font-mono font-bold text-[var(--color-text-primary)]">{selectedAccount.account_id}</span>
            </div>
            {note && (
              <div className="p-3.5 flex justify-between items-center font-medium">
                <span className="text-[var(--color-text-muted)] font-bold">Note</span>
                <span className="text-[var(--color-text-primary)] italic">{note}</span>
              </div>
            )}
            <div className="p-3.5 flex justify-between items-center font-medium">
              <span className="text-[var(--color-text-muted)] font-bold">Ledger Integrity</span>
              <span className="text-emerald-700 font-bold flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" /> Atomic Double-Entry Commit
              </span>
            </div>
          </div>

          {/* Security Authorization: Password Confirmation */}
          <div className="space-y-2 text-left">
            <Input
              label="Security Authorization — Enter Transfer Password"
              type={showAuthPassword ? 'text' : 'password'}
              required
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              placeholder="Enter your dedicated transfer password"
              icon={
                <button
                  type="button"
                  onClick={() => setShowAuthPassword(!showAuthPassword)}
                  className="p-1 hover:text-[var(--color-sapphire)] cursor-pointer"
                >
                  {showAuthPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              }
              helperText="Notice: 3 consecutive incorrect attempts will place transfers on security hold."
              autoFocus
            />
          </div>

          {submitError && (
            <Alert
              variant="danger"
              icon={<AlertCircle className="h-4 w-4" />}
              message={submitError}
            />
          )}

          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="secondary"
              size="default"
              onClick={() => setStep(2)}
            >
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Back
            </Button>

            <Button
              type="button"
              variant="primary"
              size="default"
              onClick={handleExecuteTransfer}
              isLoading={isSubmitting}
              className="flex-1"
            >
              <Check className="h-4 w-4 mr-1.5 stroke-[3]" />
              <span>Authorize &amp; Send Money</span>
            </Button>
          </div>
        </Card>
      )}

      {/* STEP 4: Transfer Success Receipt */}
      {step === 4 && receipt && (
        <Card className="p-6 md:p-8 space-y-6 text-center">
          <div className="mx-auto h-16 w-16 rounded-2xl bg-emerald-50 border border-emerald-300 flex items-center justify-center text-emerald-700 shadow-sm">
            <Check className="h-8 w-8 stroke-[3]" />
          </div>

          <div>
            <h2 className="text-2xl font-extrabold text-[var(--color-sapphire)]">Transfer Executed Successfully</h2>
            <p className="text-xs text-[var(--color-text-secondary)] mt-1 font-medium">
              Funds debited from sender and credited to recipient in PostgreSQL ledger.
            </p>
          </div>

          {/* Detailed Receipt Card */}
          <div className="p-5 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] text-left space-y-3.5">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <span className="text-xs font-bold text-[var(--color-text-muted)]">Transfer Reference</span>
              <span className="font-mono font-extrabold text-xs text-[var(--color-sapphire)]">{receipt.transfer_id}</span>
            </div>

            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <span className="text-xs font-bold text-[var(--color-text-muted)]">Amount Transferred</span>
              <span className="font-mono font-extrabold text-lg text-emerald-700 font-tabular">
                {receipt.formatted_amount}
              </span>
            </div>

            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <span className="text-xs font-bold text-[var(--color-text-muted)]">Recipient</span>
              <div className="text-right">
                <span className="font-bold text-xs text-[var(--color-text-primary)] block">{receipt.recipient.name}</span>
                <span className="font-mono text-[11px] font-bold text-[var(--color-sapphire)]">{receipt.recipient.omerta_user_number}</span>
              </div>
            </div>

            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <span className="text-xs font-bold text-[var(--color-text-muted)]">Sender</span>
              <div className="text-right">
                <span className="font-bold text-xs text-[var(--color-text-primary)] block">{receipt.sender.name}</span>
                <span className="font-mono text-[11px] font-bold text-[var(--color-text-muted)]">{receipt.sender.omerta_user_number}</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--color-text-muted)]">Timestamp</span>
              <span className="text-xs font-mono font-bold text-[var(--color-text-secondary)]">
                {new Date(receipt.created_at).toLocaleString()}
              </span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Button
              variant="secondary"
              size="default"
              onClick={handleCopyReceipt}
            >
              {copiedReceipt ? <Check className="h-4 w-4 text-emerald-600 mr-1.5" /> : <Copy className="h-4 w-4 text-[var(--color-sapphire)] mr-1.5" />}
              <span>{copiedReceipt ? 'Copied Receipt' : 'Copy Receipt'}</span>
            </Button>

            <Button
              variant="primary"
              size="default"
              onClick={resetForm}
            >
              <RotateCcw className="h-4 w-4 mr-1.5" />
              <span>Send Another</span>
            </Button>

            <Button
              variant="ghost"
              size="default"
              onClick={() => navigate('/customer/dashboard')}
            >
              Back to Dashboard
            </Button>
          </div>
        </Card>
      )}

      {/* MODAL 1: VPN / PROXY CONNECTION ACTIVE POPUP */}
      {vpnModalOpen && (
        <Modal
          isOpen={vpnModalOpen}
          onClose={() => setVpnModalOpen(false)}
          title="VPN / Proxy Detected"
          subtitle="Compliance & Risk Policy Violation"
          maxWidth="md"
        >
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-950 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600 mt-0.5" />
              <div className="space-y-1">
                <p className="font-bold text-amber-950 text-sm">Please Disconnect Your VPN</p>
                <p className="text-amber-900 leading-relaxed font-medium">
                  For banking compliance and anti-fraud safeguards, transfers cannot be executed through commercial VPNs or proxy tunnels.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-2">
              <span className="text-[11px] font-bold text-[var(--color-text-muted)] uppercase">Observed Telemetry</span>
              <div className="flex justify-between items-center py-1 border-b border-[var(--color-border)]">
                <span className="text-[var(--color-text-muted)] font-medium">Exit Country</span>
                <span className="font-mono text-[var(--color-sapphire)] font-bold">{vpnDetails?.country || 'External'}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-[var(--color-border)]">
                <span className="text-[var(--color-text-muted)] font-medium">ISP / Gateway</span>
                <span className="font-bold text-[var(--color-text-primary)]">{vpnDetails?.isp || 'Hosting Gateway'}</span>
              </div>
              {vpnDetails?.reason && (
                <div className="text-[11px] text-amber-800 pt-1 font-medium">
                  Reason: {vpnDetails.reason}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setVpnModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={handleRecheckVpnConnection}
                isLoading={isRecheckingVpn}
              >
                <RefreshCw className="w-4 h-4 mr-1.5" />
                <span>Check Connection Again</span>
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 2: 3-WRONG TRANSFER PASSWORD SECURITY HOLD MODAL */}
      {transferBlockedModalOpen && (
        <Modal
          isOpen={transferBlockedModalOpen}
          onClose={() => setTransferBlockedModalOpen(false)}
          title="Transfer Access Suspended"
          subtitle="Security Hold Enforced (3 Failed Password Attempts)"
          maxWidth="md"
        >
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-rose-950 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 shrink-0 text-rose-600 mt-0.5" />
              <div className="space-y-1">
                <p className="font-bold text-rose-950 text-sm">Money Transfers Restricted</p>
                <p className="text-rose-900 leading-relaxed font-medium">
                  {transferBlockedMessage || 'You have entered your transfer password incorrectly 3 times. Transfers have been placed on security hold for your protection. You remain logged in.'}
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] space-y-2">
              <span className="text-[11px] font-bold text-[var(--color-text-muted)] uppercase">How to Restore Privileges</span>
              <ul className="list-disc pl-4 space-y-1.5 text-xs text-[var(--color-text-secondary)] font-medium">
                <li>Open a support ticket and upload a picture of your National ID or Passport.</li>
                <li>Compliance staff will verify your identity in the Helpdesk queue.</li>
                <li>Upon verification, you will set a new transfer password.</li>
              </ul>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setTransferBlockedModalOpen(false)}
              >
                Dismiss
              </Button>
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={() => {
                  setTransferBlockedModalOpen(false);
                  navigate('/customer/support?reason=TRANSFER_BLOCKED');
                }}
              >
                <span>Open Support Ticket</span>
                <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 3: RESTORE / SET NEW TRANSFER PASSWORD REQUIRED POPUP */}
      {passwordChangeModalOpen && (
        <Modal
          isOpen={passwordChangeModalOpen}
          onClose={() => setPasswordChangeModalOpen(false)}
          title="Set New Transfer Password"
          subtitle="Compliance Restoration: Please set a new transfer password to complete reactivation"
          maxWidth="md"
        >
          <form onSubmit={handleChangeTransferPassword} className="space-y-4 text-xs">
            {passwordModalSuccess ? (
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 flex items-center gap-3">
                <Check className="w-6 h-6 shrink-0 text-emerald-600 stroke-[3]" />
                <div className="space-y-0.5">
                  <p className="font-bold text-emerald-950 text-sm">Transfer Password Updated Successfully!</p>
                  <p className="text-xs text-emerald-800 font-medium">
                    Your transfer access is now ACTIVE. You can make money transfers freely.
                  </p>
                </div>
              </div>
            ) : (
              <>
                {passwordModalError && (
                  <Alert
                    variant="danger"
                    icon={<AlertCircle className="h-4 w-4" />}
                    message={passwordModalError}
                  />
                )}

                <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-[var(--color-sapphire)] flex items-start gap-3">
                  <ShieldCheck className="w-5 h-5 text-[var(--color-sapphire)] shrink-0 mt-0.5" />
                  <p className="text-xs leading-relaxed text-[var(--color-text-secondary)] font-medium">
                    Your account ownership was verified by Compliance. Set your new dedicated transfer password below to authorize transfers.
                  </p>
                </div>

                <Input
                  label="New Transfer Password (Min 8 Characters)"
                  type={showNewPasswordText ? 'text' : 'password'}
                  required
                  value={newTransferPassword}
                  onChange={(e) => setNewTransferPassword(e.target.value)}
                  placeholder="Enter new transfer password"
                  icon={
                    <button
                      type="button"
                      onClick={() => setShowNewPasswordText(!showNewPasswordText)}
                      className="p-1 hover:text-[var(--color-sapphire)] cursor-pointer"
                    >
                      {showNewPasswordText ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  }
                />

                <Input
                  label="Confirm New Transfer Password"
                  type={showNewPasswordText ? 'text' : 'password'}
                  required
                  value={confirmTransferPassword}
                  onChange={(e) => setConfirmTransferPassword(e.target.value)}
                  placeholder="Repeat new transfer password"
                />

                <div className="flex items-center justify-end gap-3 pt-3">
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={passwordModalLoading}
                  >
                    <ShieldCheck className="w-4 h-4 mr-1.5" />
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
