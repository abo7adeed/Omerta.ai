import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Lock,
  Mail,
  ArrowRight,
  AlertCircle,
  Building2,
  Eye,
  EyeOff,
  ShieldCheck,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, sessionError } = useAuth();

  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasActiveSessionConflict, setHasActiveSessionConflict] = useState<boolean>(false);

  const doLogin = async (force: boolean = false) => {
    if (!username.trim() || !password.trim()) {
      setError('Please enter your email/username and password.');
      return;
    }

    setLoading(true);
    setError(null);
    setHasActiveSessionConflict(false);

    try {
      const res = await login(username.trim(), password, force);
      const userRole = res?.user?.role || 'CUSTOMER';
      if (userRole === 'CUSTOMER') {
        navigate('/customer/dashboard');
      } else {
        navigate('/admin/dashboard');
      }
    } catch (err: any) {
      const errMsg = err.message || 'Invalid credentials or login failure.';
      setError(errMsg);
      if (
        errMsg.toLowerCase().includes('active session') ||
        errMsg.toLowerCase().includes('concurrent') ||
        err.data?.detail?.error === 'CONCURRENT_SESSION_DENIED'
      ) {
        setHasActiveSessionConflict(true);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    doLogin(false);
  };

  const handleForceLogin = () => {
    doLogin(true);
  };

  const effectiveError = error || sessionError;

  return (
    <div className="min-h-screen bg-[#FFF8E1] flex flex-col justify-between p-4 sm:p-8">
      {/* Header Branding */}
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
              Financial Crime Intelligence Platform
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-[8px] bg-white border border-[#E0DDD6] shadow-xs">
          <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
          <span className="text-xs font-semibold text-[#002D72]">System Protected</span>
        </div>
      </header>

      {/* Main Login Card */}
      <main className="flex-1 flex items-center justify-center py-8">
        <Card className="w-full max-w-md p-6 sm:p-8 space-y-6 shadow-md">
          <div className="text-center space-y-1">
            <h1 className="text-2xl font-bold text-[#002D72] tracking-tight">
              Sign In to Your Account
            </h1>
            <p className="text-xs text-[#64748B] font-medium">
              Access your corporate banking ledger &amp; intelligence portal
            </p>
          </div>

          {effectiveError && (
            <div className="p-3.5 rounded-[10px] bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B] text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-[#DC2626] mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold">{effectiveError}</span>
                {hasActiveSessionConflict && (
                  <p className="text-[11px] text-[#991B1B]">
                    Another session is active. You can terminate it and proceed below.
                  </p>
                )}
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <Input
              label="Email or Username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. user@omerta.ai"
              leftIcon={<Mail className="w-4 h-4 text-[#64748B]" />}
            />

            <Input
              label="Password"
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              leftIcon={<Lock className="w-4 h-4 text-[#64748B]" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="p-1 text-[#64748B] hover:text-[#002D72] cursor-pointer"
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              }
            />

            <div className="flex items-center justify-between pt-1">
              <Link
                to="/forgot-password"
                className="text-xs font-semibold text-[#1E88E5] hover:text-[#1976D2] hover:underline"
              >
                Forgot Password?
              </Link>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={loading}
              className="w-full mt-2"
            >
              <span>Sign In</span>
              <ArrowRight className="w-4 h-4" />
            </Button>

            {hasActiveSessionConflict && (
              <Button
                type="button"
                variant="secondary"
                size="md"
                onClick={handleForceLogin}
                isLoading={loading}
                className="w-full border-amber-600 text-amber-800 hover:bg-amber-50"
              >
                <span>Terminate Other Sessions &amp; Force Login</span>
              </Button>
            )}
          </form>

          <div className="pt-4 border-t border-[#E0DDD6] space-y-2">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] text-center">
              Quick Demo Access
            </p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setUsername('admin@omerta.ai');
                  setPassword('AdminPass123!');
                }}
                className="px-2.5 py-1.5 rounded-[8px] bg-[#F4F1EC] hover:bg-[#EBF3FC] text-[#002D72] border border-[#E0DDD6] hover:border-[#BFDBFE] text-xs font-semibold text-center transition-all cursor-pointer"
              >
                Admin (Executive)
              </button>
              <button
                type="button"
                onClick={() => {
                  setUsername('analyst@omerta.ai');
                  setPassword('AnalystPass123!');
                }}
                className="px-2.5 py-1.5 rounded-[8px] bg-[#F4F1EC] hover:bg-[#EBF3FC] text-[#002D72] border border-[#E0DDD6] hover:border-[#BFDBFE] text-xs font-semibold text-center transition-all cursor-pointer"
              >
                Fraud Analyst
              </button>
              <button
                type="button"
                onClick={() => {
                  setUsername('investigator@omerta.ai');
                  setPassword('InvestigatorPass123!');
                }}
                className="px-2.5 py-1.5 rounded-[8px] bg-[#F4F1EC] hover:bg-[#EBF3FC] text-[#002D72] border border-[#E0DDD6] hover:border-[#BFDBFE] text-xs font-semibold text-center transition-all cursor-pointer"
              >
                Lead Investigator
              </button>
              <button
                type="button"
                onClick={() => {
                  setUsername('ziad@omerta.ai');
                  setPassword('Customer@2026!');
                }}
                className="px-2.5 py-1.5 rounded-[8px] bg-[#F4F1EC] hover:bg-[#FFF9E6] text-[#002D72] border border-[#E0DDD6] hover:border-[#FFE082] text-xs font-semibold text-center transition-all cursor-pointer"
              >
                Customer Portal
              </button>
            </div>
          </div>

          <div className="pt-2 border-t border-[#E0DDD6] text-center">
            <p className="text-xs text-[#64748B]">
              Don&apos;t have an account?{' '}
              <Link
                to="/register"
                className="font-bold text-[#002D72] hover:text-[#1E88E5] hover:underline"
              >
                Register Corporate Account
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
