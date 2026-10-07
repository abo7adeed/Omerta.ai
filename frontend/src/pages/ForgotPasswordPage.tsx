import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowRight, ShieldCheck, ArrowLeft, CheckCircle2, AlertCircle, Copy, Check, Building2 } from 'lucide-react';
import { api } from '../api/client';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<any | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await api.forgotPassword(email.trim());
      setSuccessData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to submit password reset request.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (url: string) => {
    navigator.clipboard.writeText(url);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#FFF8E1] flex flex-col justify-between p-4 sm:p-8">
      {/* Header Branding */}
      <header className="max-w-md w-full mx-auto flex items-center justify-between py-2">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-[10px] bg-[#002D72] text-[#F9A825] flex items-center justify-center shadow-xs">
            <Building2 className="w-4.5 h-4.5 stroke-[2.2]" />
          </div>
          <div className="text-lg font-bold text-[#002D72]">
            OMERTA<span className="text-[#F9A825]">.AI</span>
          </div>
        </div>
      </header>

      {/* Main Card */}
      <main className="flex-1 flex items-center justify-center py-8">
        <Card className="w-full max-w-md p-6 sm:p-8 space-y-6 shadow-md">
          <div className="text-center space-y-1">
            <h1 className="text-2xl font-bold text-[#002D72] tracking-tight">
              Reset Account Password
            </h1>
            <p className="text-xs text-[#64748B] font-medium">
              Enter your account email or username to receive a secure recovery token.
            </p>
          </div>

          {!successData ? (
            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              {error && (
                <div className="p-3.5 rounded-[10px] bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B] flex items-center gap-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0 text-[#DC2626]" />
                  <span className="font-semibold">{error}</span>
                </div>
              )}

              <Input
                label="Account Email Address or Username"
                type="text"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. user@omerta.ai"
                leftIcon={<Mail className="h-4 w-4 text-[#64748B]" />}
                autoFocus
              />

              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={loading}
                disabled={!email.trim()}
                className="w-full mt-2"
              >
                <span>Send Password Reset Email</span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </form>
          ) : (
            <div className="space-y-4 text-center">
              <div className="mx-auto w-12 h-12 rounded-full bg-[#ECFDF5] border border-[#A7F3D0] flex items-center justify-center text-[#10B981]">
                <CheckCircle2 className="h-6 w-6 stroke-[2.5]" />
              </div>

              <div>
                <h3 className="text-base font-bold text-[#002D72]">
                  Recovery Token Dispatched
                </h3>
                <p className="text-xs text-[#64748B] mt-1 font-medium">
                  If an account matches <span className="font-bold text-[#0F172A]">{email}</span>, a secure recovery email has been sent.
                </p>
              </div>

              {successData.reset_url && (
                <div className="p-3.5 rounded-[10px] bg-[#F4F1EC] border border-[#E0DDD6] text-left space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#002D72]">
                    Local Demo Recovery Shortcut:
                  </span>
                  <div className="flex items-center justify-between gap-2 bg-white p-2 rounded-[8px] border border-[#E0DDD6]">
                    <span className="font-mono text-[11px] text-[#002D72] truncate">
                      {successData.reset_url}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(successData.reset_url)}
                      className="p-1 text-[#64748B] hover:text-[#002D72] cursor-pointer shrink-0"
                    >
                      {copiedLink ? <Check className="w-4 h-4 text-[#10B981]" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                  <Link
                    to={successData.reset_url.replace(/^https?:\/\/[^/]+/, '')}
                    className="w-full py-2 bg-[#002D72] text-white text-xs font-bold text-center rounded-[8px] block hover:bg-[#001F52] transition-colors"
                  >
                    Open Reset Password Form
                  </Link>
                </div>
              )}
            </div>
          )}

          <div className="pt-4 border-t border-[#E0DDD6] text-center">
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-[#002D72] hover:text-[#1E88E5] hover:underline"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Sign In</span>
            </Link>
          </div>
        </Card>
      </main>

      <footer className="max-w-md w-full mx-auto text-center py-2 text-[11px] text-[#64748B]">
        Omerta.ai Financial Crime &amp; Banking Operations © 2026.
      </footer>
    </div>
  );
};
