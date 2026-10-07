import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Smartphone,
  Laptop,
  Globe,
  AlertTriangle,
  LogOut,
  ToggleLeft,
  ToggleRight,
  Info,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Radio,
} from 'lucide-react';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { collectNetworkTelemetry } from '../../utils/telemetry';
import {
  Card,
  Button,
} from '../../components/ui';
import type { CustomerSession } from '../../types';

export const CustomerSecurityPage: React.FC = () => {
  const { customer } = useAuth();
  const [sessions, setSessions] = useState<CustomerSession[]>([]);
  const [consent, setConsent] = useState(customer?.device_consent ?? true);
  const [isLoading, setIsLoading] = useState(true);
  const [isProbing, setIsProbing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [secondsRemaining, setSecondsRemaining] = useState(30);

  const fetchSessions = async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    try {
      const res = await api.getCustomerSessions();
      setSessions(res);
    } catch {
      // Fallback
      setSessions([
        {
          session_id: 'SESS-CURRENT',
          device_label: 'Desktop (macOS / Chrome)',
          platform: 'macOS',
          observed_country: 'EG',
          is_vpn: false,
          is_active: true,
          started_at: new Date().toISOString(),
        },
      ]);
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  const probeAndUpdateTelemetry = async () => {
    setIsProbing(true);
    try {
      const declared = customer?.declared_country || 'EG';
      const telemetry = await collectNetworkTelemetry(declared);
      await api.sendTelemetryHeartbeat({
        client_ip: telemetry.ip,
        country: telemetry.country,
        is_vpn: telemetry.is_vpn,
        isp: telemetry.isp,
        org: telemetry.org,
        browser_timezone: telemetry.browser_timezone,
        ip_timezone: telemetry.ip_timezone,
        user_agent: telemetry.user_agent,
      });
      await fetchSessions(false);
      setSecondsRemaining(30);
    } catch (e) {
      console.warn('Telemetry probe notice:', e);
    } finally {
      setIsProbing(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchSessions();
  }, []);

  // 30-Second recurring countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          probeAndUpdateTelemetry();
          return 30;
        }
        return prev - 1;
      });
    }, 1000);

    const handleSync = () => {
      fetchSessions(false);
      setSecondsRemaining(30);
    };
    window.addEventListener('omerta_telemetry_synced', handleSync);

    return () => {
      clearInterval(timer);
      window.removeEventListener('omerta_telemetry_synced', handleSync);
    };
  }, [customer?.declared_country]);

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await api.revokeCustomerSession(sessionId);
      setMsg(`Session ${sessionId} has been revoked successfully.`);
      fetchSessions();
    } catch {
      setMsg(`Could not revoke session.`);
    }
  };

  const handleToggleConsent = async () => {
    const nextConsent = !consent;
    setConsent(nextConsent);
    try {
      await api.updateCustomerConsent(nextConsent);
      setMsg(`Privacy consent settings updated.`);
    } catch {
      setMsg(`Failed to update consent settings.`);
    }
  };

  if (isLoading && sessions.length === 0) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-[var(--color-text-secondary)]">
        <Loader2 className="h-10 w-10 animate-spin text-[var(--color-sapphire)] mb-4" />
        <p className="text-sm font-semibold text-[var(--color-sapphire)]">Loading active sessions &amp; telemetry...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <Card className="p-6 md:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-5">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-sapphire)] flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[var(--color-sapphire)] text-[var(--color-gold)] shadow-sm">
              <ShieldCheck className="h-6 w-6 stroke-[2.2]" />
            </div>
            <span>Security &amp; Device Center</span>
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2 font-medium">
            Review your authorized devices, active login sessions, and privacy telemetry settings
          </p>
        </div>

        {/* 30-Second Live Telemetry Heartbeat Status Banner */}
        <div className="flex items-center gap-3 p-3 rounded-xl bg-[var(--color-secondary-surface)] border border-[var(--color-border)] text-xs shrink-0">
          <div className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-bold text-[var(--color-sapphire)] text-[11px]">
              <Radio className="w-3.5 h-3.5 text-[var(--color-sapphire)]" />
              <span>30s Telemetry Radar</span>
            </div>
            <p className="text-[10px] text-[var(--color-text-muted)] font-medium">
              Next check in <span className="font-mono font-bold text-[var(--color-sapphire)]">{secondsRemaining}s</span>
            </p>
          </div>
          <Button
            onClick={probeAndUpdateTelemetry}
            disabled={isProbing}
            variant="secondary"
            size="sm"
            className="ml-1 min-h-[36px]"
            title="Perform immediate network and VPN telemetry probe"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isProbing ? 'animate-spin text-[var(--color-sapphire)]' : ''}`} />
            <span>{isProbing ? 'Probing...' : 'Probe'}</span>
          </Button>
        </div>
      </Card>

      {msg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-xs text-emerald-950 flex items-center gap-2.5 font-bold">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
          <span>{msg}</span>
        </div>
      )}

      {/* Privacy & Consent Section */}
      <Card className="p-6 md:p-8 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-[var(--color-sapphire)] flex items-center gap-2">
              <Info className="h-5 w-5 text-[var(--color-sapphire)]" />
              <span>Device &amp; Session Telemetry Consent</span>
            </h3>
            <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed max-w-2xl font-medium">
              Omerta.ai can use limited device and session information to help secure your account,
              identify unusual sign-ins, and support transaction reviews. We collect only necessary,
              pseudonymous signals and never use covert tracking.
            </p>
          </div>

          <button
            onClick={handleToggleConsent}
            className="flex items-center gap-2 p-1 text-[var(--color-sapphire)] hover:opacity-80 transition-transform cursor-pointer shrink-0"
            title="Toggle Privacy Consent"
            aria-label="Toggle Privacy Consent"
          >
            {consent ? (
              <ToggleRight className="h-9 w-9 text-emerald-600" />
            ) : (
              <ToggleLeft className="h-9 w-9 text-[var(--color-text-muted)]" />
            )}
          </button>
        </div>

        <div className="pt-4 border-t border-[var(--color-border)] flex items-center justify-between text-xs">
          <span className="text-[var(--color-text-muted)] font-bold">Consent Status:</span>
          <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${consent ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' : 'bg-amber-100 text-amber-800 border border-amber-300'}`}>
            {consent ? 'Telemetry Collection Granted' : 'Telemetry Opted-Out'}
          </span>
        </div>
      </Card>

      {/* Active & Recent Sessions */}
      <Card className="p-6 md:p-8 space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-[var(--color-sapphire)] flex items-center gap-2">
            <Smartphone className="h-5 w-5 text-[var(--color-sapphire)]" />
            <span>Active &amp; Recent Sessions</span>
          </h3>
          <span className="text-xs text-[var(--color-text-muted)] font-semibold">
            Single-active-session policy enforced
          </span>
        </div>

        <div className="space-y-4">
          {sessions.map((s, idx) => {
            const isCurrent = idx === 0 && s.is_active;
            const displayLabel = s.device_label || (s.browser && s.os ? `${s.browser} on ${s.os}` : 'Web Client');
            
            return (
              <div
                key={s.session_id || idx}
                className={`p-5 rounded-xl border transition-all ${
                  isCurrent
                    ? 'bg-blue-50/40 border-[var(--color-sapphire)]/40 shadow-xs'
                    : 'bg-white border-[var(--color-border)]'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div
                      className={`p-3 rounded-xl shrink-0 ${
                        s.is_vpn
                          ? 'bg-amber-100 text-amber-800'
                          : isCurrent
                          ? 'bg-blue-100 text-[var(--color-sapphire)]'
                          : 'bg-[var(--color-secondary-surface)] text-[var(--color-text-muted)]'
                      }`}
                    >
                      {s.platform?.toLowerCase().includes('mac') ||
                      s.platform?.toLowerCase().includes('win') ||
                      s.platform?.toLowerCase().includes('linux') ? (
                        <Laptop className="h-6 w-6 stroke-[2.2]" />
                      ) : (
                        <Smartphone className="h-6 w-6 stroke-[2.2]" />
                      )}
                    </div>

                    <div className="space-y-2.5 flex-1">
                      {/* Device Title & Status Badges */}
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-[var(--color-sapphire)]">
                          {displayLabel}
                        </span>

                        {isCurrent && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300">
                            Current Session
                          </span>
                        )}

                        {s.is_active && !isCurrent && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-100 text-[var(--color-sapphire)] border border-blue-200">
                            Active Session
                          </span>
                        )}

                        {!s.is_active && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-[var(--color-secondary-surface)] text-[var(--color-text-muted)] border border-[var(--color-border)]">
                            Terminated / Revoked
                          </span>
                        )}

                        {/* VPN vs Direct Connection Badge */}
                        {s.is_vpn ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" /> VPN / Proxy (Exit: {s.observed_country})
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                            <Globe className="h-3 w-3" /> Direct ({s.observed_country || 'EG'})
                          </span>
                        )}
                      </div>

                      {/* Explicit Metadata Grid */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
                        <div className="bg-[var(--color-secondary-surface)] p-2.5 rounded-lg border border-[var(--color-border)]">
                          <span className="text-[var(--color-text-muted)] block text-[10px] uppercase font-bold">OS</span>
                          <span className="font-bold text-[var(--color-text-primary)]">{s.os || s.platform || 'Linux'}</span>
                        </div>
                        <div className="bg-[var(--color-secondary-surface)] p-2.5 rounded-lg border border-[var(--color-border)]">
                          <span className="text-[var(--color-text-muted)] block text-[10px] uppercase font-bold">Browser</span>
                          <span className="font-bold text-[var(--color-text-primary)]">{s.browser || 'Google Chrome'}</span>
                        </div>
                        <div className="bg-[var(--color-secondary-surface)] p-2.5 rounded-lg border border-[var(--color-border)]">
                          <span className="text-[var(--color-text-muted)] block text-[10px] uppercase font-bold">IP Address</span>
                          <span className="font-mono font-bold text-[var(--color-sapphire)]">{s.ip_address || '127.0.0.1'}</span>
                        </div>
                        <div className="bg-[var(--color-secondary-surface)] p-2.5 rounded-lg border border-[var(--color-border)]">
                          <span className="text-[var(--color-text-muted)] block text-[10px] uppercase font-bold">Sign-in</span>
                          <span className="font-bold text-[var(--color-text-primary)]">{s.started_at ? new Date(s.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent'}</span>
                        </div>
                      </div>

                      {/* Security Notice */}
                      {s.security_notice && (
                        <div
                          className={`mt-2 p-3 rounded-lg text-xs flex items-start gap-2.5 font-medium ${
                            s.is_vpn
                              ? 'bg-amber-50 text-amber-950 border border-amber-300'
                              : 'bg-emerald-50 text-emerald-950 border border-emerald-300'
                          }`}
                        >
                          {s.is_vpn ? (
                            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-600" />
                          ) : (
                            <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5 text-emerald-600" />
                          )}
                          <span className="leading-relaxed font-medium">{s.security_notice}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {!isCurrent && s.is_active && (
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleRevokeSession(s.session_id)}
                      className="self-start md:self-auto"
                    >
                      <LogOut className="h-3.5 w-3.5 mr-1" />
                      <span>Revoke</span>
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};
