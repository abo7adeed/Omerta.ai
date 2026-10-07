import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Building2,
  User,
  Mail,
  Lock,
  Wallet,
  AlertCircle,
  Eye,
  EyeOff,
  ArrowRight,
  ShieldCheck,
  KeyRound,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

interface CountryOption {
  code: string;
  name: string;
  flag: string;
  dialCode: string;
  currency: string;
  samplePhone: string;
}

const COUNTRIES: CountryOption[] = [
  { code: 'EG', name: 'Egypt', flag: '🇪🇬', dialCode: '+20', currency: 'EGP', samplePhone: '010 1234 5678' },
  { code: 'SA', name: 'Saudi Arabia', flag: '🇸🇦', dialCode: '+966', currency: 'SAR', samplePhone: '50 123 4567' },
  { code: 'AE', name: 'United Arab Emirates', flag: '🇦🇪', dialCode: '+971', currency: 'AED', samplePhone: '50 123 4567' },
  { code: 'US', name: 'United States', flag: '🇺🇸', dialCode: '+1', currency: 'USD', samplePhone: '(555) 234-5678' },
  { code: 'GB', name: 'United Kingdom', flag: '🇬🇧', dialCode: '+44', currency: 'GBP', samplePhone: '7911 123456' },
  { code: 'DE', name: 'Germany', flag: '🇩🇪', dialCode: '+49', currency: 'EUR', samplePhone: '151 12345678' },
];

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [selectedCountry, setSelectedCountry] = useState<CountryOption>(COUNTRIES[0]);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    username: '',
    national_id_number: '',
    password: '',
    confirm_password: '',
    transfer_password: '',
    confirm_transfer_password: '',
    preferred_currency: 'EGP',
    initial_balance: 50000,
    device_consent: true,
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showTransferPassword, setShowTransferPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleCountryChange = (countryCode: string) => {
    const c = COUNTRIES.find((item) => item.code === countryCode) || COUNTRIES[0];
    setSelectedCountry(c);
    setFormData((prev) => ({
      ...prev,
      preferred_currency: c.currency,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.device_consent) {
      setError('You must accept the Banking Terms of Service and Device Security Consent.');
      return;
    }
    if (!formData.national_id_number.trim()) {
      setError('National ID Number is required for KYC compliance.');
      return;
    }
    if (formData.password !== formData.confirm_password) {
      setError('Account password and confirmation do not match.');
      return;
    }
    if (formData.password.length < 8) {
      setError('Account login password must be at least 8 characters long.');
      return;
    }
    if (!formData.transfer_password) {
      setError('Transfer password is required for money movement.');
      return;
    }
    if (formData.transfer_password !== formData.confirm_transfer_password) {
      setError('Transfer password and confirmation do not match.');
      return;
    }
    if (formData.transfer_password.length < 8) {
      setError('Dedicated transfer password must be at least 8 characters long.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const fullPhone = phoneNumber ? `${selectedCountry.dialCode} ${phoneNumber.trim()}` : '';
      await register({
        ...formData,
        phone: fullPhone,
        country: selectedCountry.name,
      });
      navigate('/customer/dashboard');
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check details.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FFF8E1] flex flex-col justify-between p-4 sm:p-8">
      {/* Header */}
      <header className="max-w-6xl w-full mx-auto flex items-center justify-between py-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-[10px] bg-[#002D72] text-[#F9A825] flex items-center justify-center shadow-xs">
            <Building2 className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div>
            <div className="text-xl font-bold tracking-tight text-[#002D72]">
              OMERTA<span className="text-[#F9A825]">.AI</span>
            </div>
            <div className="text-[10px] text-[#64748B] tracking-wider uppercase font-bold">
              Account Registration &amp; KYC
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-[8px] bg-white border border-[#E0DDD6]">
          <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
          <span className="text-xs font-semibold text-[#002D72]">Instant Verification</span>
        </div>
      </header>

      {/* Main Registration Form */}
      <main className="flex-1 flex items-center justify-center py-8">
        <Card className="w-full max-w-2xl p-6 sm:p-8 space-y-6 shadow-md">
          <div className="text-center space-y-1">
            <h1 className="text-2xl font-bold text-[#002D72] tracking-tight">
              Open Corporate Banking Account
            </h1>
            <p className="text-xs text-[#64748B] font-medium">
              Create your financial account with automated AML protection &amp; dedicated transfer keys
            </p>
          </div>

          {error && (
            <div className="p-3.5 rounded-[10px] bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B] text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-[#DC2626]" />
              <span className="font-semibold">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            {/* Identity Details */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <Input
                label="Full Legal Name"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                placeholder="e.g. Tariq Mansour"
                leftIcon={<User className="w-4 h-4 text-[#64748B]" />}
              />
              <Input
                label="Corporate Email Address"
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value, username: e.target.value })}
                placeholder="e.g. tariq@omerta.ai"
                leftIcon={<Mail className="w-4 h-4 text-[#64748B]" />}
              />
            </div>

            {/* Country & Phone */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#475569] mb-1.5">
                  Country of Residence
                </label>
                <select
                  value={selectedCountry.code}
                  onChange={(e) => handleCountryChange(e.target.value)}
                  className="w-full h-11 bg-white border border-[#E0DDD6] rounded-[10px] px-3.5 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
                >
                  {COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.flag} {c.name} ({c.dialCode})
                    </option>
                  ))}
                </select>
              </div>

              <Input
                label="Mobile Phone Number"
                required
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder={selectedCountry.samplePhone}
              />
            </div>

            {/* National ID for KYC */}
            <Input
              label="National ID / Passport Number (KYC Compliance)"
              required
              value={formData.national_id_number}
              onChange={(e) => setFormData({ ...formData, national_id_number: e.target.value })}
              placeholder="e.g. 29801011234567"
              leftIcon={<ShieldCheck className="w-4 h-4 text-[#002D72]" />}
            />

            {/* Login Passwords */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2 border-t border-[#E0DDD6]">
              <Input
                label="Account Login Password"
                type={showPassword ? 'text' : 'password'}
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="Min 8 characters"
                leftIcon={<Lock className="w-4 h-4 text-[#64748B]" />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="p-1 text-[#64748B] hover:text-[#002D72] cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                }
              />

              <Input
                label="Confirm Login Password"
                type={showPassword ? 'text' : 'password'}
                required
                value={formData.confirm_password}
                onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                placeholder="Repeat login password"
              />
            </div>

            {/* Dedicated Transfer Passwords */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2 border-t border-[#E0DDD6]">
              <Input
                label="Dedicated Transfer Password (Money Movement)"
                type={showTransferPassword ? 'text' : 'password'}
                required
                value={formData.transfer_password}
                onChange={(e) => setFormData({ ...formData, transfer_password: e.target.value })}
                placeholder="Required to send funds"
                leftIcon={<KeyRound className="w-4 h-4 text-[#F9A825]" />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowTransferPassword(!showTransferPassword)}
                    className="p-1 text-[#64748B] hover:text-[#002D72] cursor-pointer"
                  >
                    {showTransferPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                }
              />

              <Input
                label="Confirm Transfer Password"
                type={showTransferPassword ? 'text' : 'password'}
                required
                value={formData.confirm_transfer_password}
                onChange={(e) => setFormData({ ...formData, confirm_transfer_password: e.target.value })}
                placeholder="Repeat transfer password"
              />
            </div>

            {/* Currency & Demo Balance */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2 border-t border-[#E0DDD6]">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#475569] mb-1.5">
                  Account Currency
                </label>
                <select
                  value={formData.preferred_currency}
                  onChange={(e) => setFormData({ ...formData, preferred_currency: e.target.value })}
                  className="w-full h-11 bg-white border border-[#E0DDD6] rounded-[10px] px-3.5 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
                >
                  <option value="EGP">EGP — Egyptian Pound</option>
                  <option value="USD">USD — US Dollar</option>
                  <option value="SAR">SAR — Saudi Riyal</option>
                  <option value="AED">AED — UAE Dirham</option>
                  <option value="EUR">EUR — Euro</option>
                  <option value="GBP">GBP — British Pound</option>
                </select>
              </div>

              <Input
                label="Initial Demo Deposit Balance"
                type="number"
                min="1000"
                max="500000"
                step="1000"
                value={formData.initial_balance}
                onChange={(e) => setFormData({ ...formData, initial_balance: Number(e.target.value) })}
                leftIcon={<Wallet className="w-4 h-4 text-[#10B981]" />}
              />
            </div>

            {/* Consent Checkbox */}
            <label className="flex items-start gap-2.5 pt-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.device_consent}
                onChange={(e) => setFormData({ ...formData, device_consent: e.target.checked })}
                className="mt-0.5 rounded text-[#002D72] focus:ring-[#1E88E5]"
              />
              <span className="text-[11px] text-[#475569] leading-tight">
                I accept the <span className="font-bold text-[#002D72]">Banking Terms of Service</span>, Privacy Policy, and consent to real-time risk intelligence fingerprinting for fraud protection.
              </span>
            </label>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              className="w-full mt-4"
            >
              <span>Create Account &amp; Access Banking</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </form>

          <div className="pt-4 border-t border-[#E0DDD6] text-center">
            <p className="text-xs text-[#64748B]">
              Already have an Omerta.ai account?{' '}
              <Link to="/login" className="font-bold text-[#002D72] hover:text-[#1E88E5] hover:underline">
                Sign In
              </Link>
            </p>
          </div>
        </Card>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl w-full mx-auto text-center py-2 text-[11px] text-[#64748B]">
        Omerta.ai Financial Crime &amp; Banking Operations © 2026. All rights reserved.
      </footer>
    </div>
  );
};
