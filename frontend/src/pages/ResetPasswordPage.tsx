import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Lock, ArrowRight, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import { Card, Button, Input, Alert } from '../components/ui';

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setError('Missing or invalid password reset token. Please request a new reset link.');
    }
  }, [token]);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match. Please verify.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await api.resetPassword({
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setIsSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to update password. Your reset token may have expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-ivory)] flex flex-col justify-center items-center p-4 sm:p-6 font-sans">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-[var(--color-sapphire)] text-white shadow-sm mb-2">
            <ShieldCheck className="h-8 w-8 text-[var(--color-gold)] stroke-[2.2]" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-sapphire)]">
            Create New Password
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] font-medium">
            Enter a secure new password for your Omerta.ai banking account.
          </p>
        </div>

        {/* Form Card */}
        <Card className="p-6 sm:p-8 space-y-5">
          {!isSuccess ? (
            <form onSubmit={handleReset} className="space-y-4">
              {error && (
                <Alert
                  variant="danger"
                  icon={<AlertCircle className="h-4 w-4" />}
                  message={error}
                />
              )}

              <Input
                label="New Password (min 8 characters)"
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new strong password"
                icon={<Lock className="h-4 w-4 text-[var(--color-sapphire)]" />}
              />

              <Input
                label="Confirm New Password"
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                icon={<Lock className="h-4 w-4 text-[var(--color-sapphire)]" />}
              />

              <Button
                type="submit"
                variant="primary"
                isLoading={loading}
                disabled={!token || newPassword.length < 8}
                className="w-full mt-2"
              >
                <span>Confirm &amp; Reset Password</span>
                <ArrowRight className="h-4 w-4 ml-1.5" />
              </Button>

              <div className="pt-2 text-center">
                <Link
                  to="/login"
                  className="text-xs font-semibold text-[var(--color-royal-blue)] hover:underline"
                >
                  Return to Sign In
                </Link>
              </div>
            </form>
          ) : (
            <div className="space-y-4 text-center py-4">
              <div className="mx-auto w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shadow-sm">
                <CheckCircle2 className="h-8 w-8 text-emerald-600 stroke-[2.5]" />
              </div>

              <div>
                <h3 className="text-base font-bold text-[var(--color-sapphire)]">
                  Password Successfully Changed!
                </h3>
                <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 font-medium leading-relaxed">
                  All active sessions have been securely updated. Redirecting you to sign in...
                </p>
              </div>

              <div className="pt-2">
                <Link
                  to="/login"
                  className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg bg-[var(--color-gold)] text-[var(--color-sapphire)] text-xs font-bold shadow-sm hover:brightness-105 transition-all"
                >
                  <span>Proceed to Sign In</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
