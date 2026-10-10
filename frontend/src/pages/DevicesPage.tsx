import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Smartphone,
  Search,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  ArrowUpRight,
  ArrowRightLeft,
  ShieldAlert,
  Globe,
  Monitor,
  User,
  Activity,
  Layers,
  Clock,
  Laptop,
} from 'lucide-react';
import { api } from '../api/client';
import type { DeviceItem } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { RiskBadge } from '../components/ui/RiskBadge';
import { Modal } from '../components/ui/Modal';
import { TableContainer, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/ui/Table';

export const DevicesPage: React.FC = () => {
  const navigate = useNavigate();
  const [devices, setDevices] = useState<DeviceItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [page, setPage] = useState(1);

  // Device detail modal state
  const [selectedDevice, setSelectedDevice] = useState<any | null>(null);

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const res = await api.getDevices({
        search,
        platform: platformFilter,
        page,
        page_size: 25,
      });
      setDevices(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load devices', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, [page, platformFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchDevices();
  };

  const handleOpenDetail = async (d: DeviceItem) => {
    try {
      const res = await api.getDeviceDetail(d.external_id);
      setSelectedDevice(res);
    } catch (err) {
      console.error('Failed to load device detail', err);
    }
  };

  const activeDevicesCount = devices.filter((d) => d.is_active_now).length;
  const multiAccountCount = devices.filter((d) => (d.account_count || 1) > 1).length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Page Header */}
      <Card className="p-6 sm:p-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F9A825] mb-1">
            <Smartphone className="w-4 h-4" />
            Hardware &amp; Telemetry Intelligence
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#002D72]">
            Device Intelligence &amp; Fingerprints
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-medium">
            Real-time monitored devices, browser telemetry, operating systems, and multi-account hardware links.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={fetchDevices}
            variant="primary"
            size="sm"
            leftIcon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Telemetry
          </Button>
        </div>
      </Card>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4 flex items-center gap-4 bg-white border-[#E0DDD6]">
          <div className="w-10 h-10 rounded-[10px] bg-[#EBF3FC] text-[#002D72] flex items-center justify-center shrink-0">
            <Monitor className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase text-[#64748B]">Monitored Hardware</div>
            <div className="text-xl font-bold text-[#002D72]">{total} Devices</div>
          </div>
        </Card>

        <Card className="p-4 flex items-center gap-4 bg-white border-[#E0DDD6]">
          <div className="w-10 h-10 rounded-[10px] bg-[#ECFDF5] text-[#065F46] flex items-center justify-center shrink-0">
            <Activity className="w-5 h-5 text-[#10B981]" />
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase text-[#64748B]">Active Online Sessions</div>
            <div className="text-xl font-bold text-[#065F46] flex items-center gap-2">
              <span>{activeDevicesCount} Live</span>
              <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] animate-pulse" />
            </div>
          </div>
        </Card>

        <Card className="p-4 flex items-center gap-4 bg-white border-[#E0DDD6]">
          <div className="w-10 h-10 rounded-[10px] bg-[#FEF2F2] text-[#991B1B] flex items-center justify-center shrink-0">
            <Layers className="w-5 h-5 text-[#DC2626]" />
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase text-[#64748B]">Shared Hardware Risk</div>
            <div className="text-xl font-bold text-[#DC2626]">{multiAccountCount} Multi-Account</div>
          </div>
        </Card>
      </div>

      {/* Search & Filters */}
      <Card className="p-5">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-3.5">
          <div className="sm:col-span-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search user name, device fingerprint, browser, IP..."
              leftIcon={<Search className="h-4 w-4 text-[#64748B]" />}
              className="h-10 text-xs"
            />
          </div>

          <div>
            <select
              value={platformFilter}
              onChange={(e) => {
                setPlatformFilter(e.target.value);
                setPage(1);
              }}
              className="w-full h-10 bg-white border border-[#E0DDD6] rounded-[10px] px-3 text-xs text-[#0F172A] font-medium outline-none focus:border-[#1E88E5] cursor-pointer"
            >
              <option value="">All Operating Systems</option>
              <option value="Linux">Linux</option>
              <option value="Windows">Windows</option>
              <option value="macOS">macOS</option>
              <option value="Android">Android</option>
              <option value="iOS">iOS</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Button type="submit" variant="sapphire" size="sm" className="h-10 flex-1 text-xs">
              Filter
            </Button>
            {(search || platformFilter) && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-10 px-3 text-xs text-[#64748B]"
                onClick={() => {
                  setSearch('');
                  setPlatformFilter('');
                  setPage(1);
                }}
              >
                Reset
              </Button>
            )}
          </div>
        </form>
      </Card>

      {/* Main Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base">Monitored Hardware Fingerprints</CardTitle>
            <CardDescription>
              Showing <span className="font-bold text-[#002D72]">{devices.length}</span> of{' '}
              <span className="font-bold text-[#002D72]">{total.toLocaleString()}</span> devices
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <TableContainer className="border-0 rounded-none rounded-b-[16px] shadow-none">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device ID / Status</TableHead>
                  <TableHead>User / Customer Name</TableHead>
                  <TableHead>Browser &amp; Operating System</TableHead>
                  <TableHead>IP / Location</TableHead>
                  <TableHead>Shared Accounts</TableHead>
                  <TableHead>Integrity</TableHead>
                  <TableHead>Risk Score</TableHead>
                  <TableHead>Last Seen</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.length > 0 ? (
                  devices.map((d) => (
                    <TableRow
                      key={d.external_id}
                      onClick={() => handleOpenDetail(d)}
                      className="cursor-pointer hover:bg-[#F8FAFC]"
                    >
                      {/* Device ID & Live indicator */}
                      <TableCell>
                        <div className="font-mono font-bold text-[#002D72] flex items-center gap-1.5">
                          {d.is_active_now ? (
                            <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse shrink-0" title="Active Live Session" />
                          ) : (
                            <span className="w-2 h-2 rounded-full bg-[#94A3B8] shrink-0" title="Offline / Inactive" />
                          )}
                          <span>{d.device_id || d.external_id}</span>
                        </div>
                        <div className="text-[11px] text-[#64748B]">
                          {d.is_active_now ? (
                            <span className="text-[#065F46] font-semibold text-[10px] uppercase">● Active Now</span>
                          ) : (
                            <span className="text-[#64748B] text-[10px] uppercase">Offline</span>
                          )}
                        </div>
                      </TableCell>

                      {/* Real User Name */}
                      <TableCell>
                        <div className="flex items-center gap-1.5 font-bold text-[#0F172A]">
                          <User className="w-3.5 h-3.5 text-[#F9A825]" />
                          <span>{d.user_name || 'System User'}</span>
                        </div>
                        {d.user_names && d.user_names.length > 1 && (
                          <div className="text-[10px] text-[#DC2626] font-medium mt-0.5">
                            +{d.user_names.length - 1} additional linked users
                          </div>
                        )}
                      </TableCell>

                      {/* Browser & OS */}
                      <TableCell>
                        <div className="font-bold text-[#0F172A] flex items-center gap-1.5">
                          {d.platform === 'macOS' || d.platform === 'iOS' ? (
                            <Laptop className="w-3.5 h-3.5 text-[#64748B]" />
                          ) : (
                            <Monitor className="w-3.5 h-3.5 text-[#64748B]" />
                          )}
                          <span>{d.browser || 'Web Browser'}</span>
                        </div>
                        <div className="text-[11px] text-[#64748B] font-mono">
                          {d.platform || 'Desktop'} · {d.model || 'Workstation'}
                        </div>
                      </TableCell>

                      {/* IP & Location */}
                      <TableCell>
                        <div className="font-mono text-xs font-semibold text-[#002D72]">
                          {d.ip_address || '127.0.0.1'}
                        </div>
                        <div className="text-[11px] text-[#64748B] flex items-center gap-1">
                          <Globe className="w-3 h-3 text-[#94A3B8]" />
                          <span>{d.location || 'Cairo, Egypt'}</span>
                        </div>
                      </TableCell>

                      {/* Shared Accounts */}
                      <TableCell>
                        <span
                          className={`font-bold font-mono px-2 py-0.5 rounded-full text-xs ${
                            (d.account_count || 0) > 1
                              ? 'bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]'
                              : (d.account_count || 0) === 1
                              ? 'bg-[#F1F5F9] text-[#002D72]'
                              : 'bg-[#F8FAFC] text-[#64748B]'
                          }`}
                        >
                          {(d.account_count || 0) > 0 ? `${d.account_count} Linked` : 'Standalone'}
                        </span>
                      </TableCell>

                      {/* Integrity */}
                      <TableCell>
                        {d.is_emulator || d.is_rooted ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#DC2626] bg-[#FEF2F2] border border-[#FECACA] px-2 py-0.5 rounded-full">
                            <AlertTriangle className="w-3 h-3" />
                            {d.is_emulator ? 'EMULATOR' : 'ROOTED'}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#065F46] bg-[#ECFDF5] border border-[#A7F3D0] px-2 py-0.5 rounded-full">
                            <CheckCircle className="w-3 h-3 text-[#10B981]" />
                            SECURE
                          </span>
                        )}
                      </TableCell>

                      {/* Risk Score */}
                      <TableCell>
                        <RiskBadge level={d.risk_level || 'LOW'} score={d.risk_score} />
                      </TableCell>

                      {/* Last Seen */}
                      <TableCell className="text-xs font-mono text-[#64748B]">
                        {d.last_seen_at
                          ? new Date(d.last_seen_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                          : 'Recent'}
                      </TableCell>

                      {/* Action */}
                      <TableCell className="text-right">
                        <Button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenDetail(d);
                          }}
                          variant="ghost"
                          size="sm"
                          className="h-8 px-2 text-[#002D72] hover:bg-[#EBF3FC]"
                        >
                          <ArrowUpRight className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-12 text-xs text-[#64748B]">
                      {loading ? 'Analyzing device records...' : 'No hardware fingerprints match criteria.'}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Device Detail Modal */}
      {selectedDevice && (
        <Modal
          isOpen={Boolean(selectedDevice)}
          onClose={() => setSelectedDevice(null)}
          title={`Device Dossier: ${selectedDevice.device_id || selectedDevice.external_id || selectedDevice.id}`}
          subtitle={`${selectedDevice.browser || 'Web Browser'} on ${selectedDevice.platform || 'System'} (${selectedDevice.model || 'Device'})`}
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            {/* Top KPI row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-[#F4F1EC] p-3.5 rounded-[12px] border border-[#E0DDD6]">
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Risk Score</span>
                <div className="mt-0.5">
                  <RiskBadge level={selectedDevice.risk_level || 'LOW'} score={selectedDevice.risk_score} />
                </div>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Platform / OS</span>
                <p className="font-bold text-[#002D72] mt-0.5">{selectedDevice.platform || 'Unknown'}</p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Hardware Integrity</span>
                <p className={`font-bold mt-0.5 ${selectedDevice.is_rooted || selectedDevice.is_emulator ? 'text-[#DC2626]' : 'text-[#065F46]'}`}>
                  {selectedDevice.is_rooted ? 'Rooted' : selectedDevice.is_emulator ? 'Virtual Emulator' : 'Genuine Hardware'}
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[#64748B]">Active Status</span>
                <p className="font-bold mt-0.5 flex items-center gap-1">
                  {selectedDevice.is_active_now ? (
                    <span className="text-[#065F46] flex items-center gap-1 font-bold">
                      <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
                      Online Now
                    </span>
                  ) : (
                    <span className="text-[#64748B] font-medium">Offline</span>
                  )}
                </p>
              </div>
            </div>

            {/* Real Telemetry Diagnostics */}
            <div className="p-4 bg-white rounded-[12px] border border-[#E0DDD6] space-y-3">
              <h5 className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-[#F9A825]" />
                Real Hardware &amp; Telemetry Diagnostics
              </h5>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[#475569]">
                <div>
                  <span className="font-bold text-[#0F172A]">Primary User:</span>
                  <p className="text-[#002D72] font-semibold">{selectedDevice.user_name || 'System User'}</p>
                </div>
                <div>
                  <span className="font-bold text-[#0F172A]">Browser:</span>
                  <p className="text-[#0F172A]">{selectedDevice.browser || 'Web Browser'}</p>
                </div>
                <div>
                  <span className="font-bold text-[#0F172A]">Hardware Model:</span>
                  <p className="text-[#0F172A]">{selectedDevice.model || 'Workstation'}</p>
                </div>
                <div>
                  <span className="font-bold text-[#0F172A]">Screen Resolution:</span>
                  <p className="text-[#0F172A]">{selectedDevice.screen_resolution || '1920×1080 (Full HD)'}</p>
                </div>
                <div>
                  <span className="font-bold text-[#0F172A]">Egress IP Address:</span>
                  <p className="font-mono text-[#002D72]">{selectedDevice.ip_address || '127.0.0.1'}</p>
                </div>
                <div>
                  <span className="font-bold text-[#0F172A]">Location Telemetry:</span>
                  <p className="text-[#0F172A]">{selectedDevice.location || 'Cairo, Egypt'}</p>
                </div>
                <div className="sm:col-span-2">
                  <span className="font-bold text-[#0F172A]">All Linked Users:</span>
                  <p className="text-[#002D72] font-medium">
                    {selectedDevice.user_names && selectedDevice.user_names.length > 0
                      ? selectedDevice.user_names.join(', ')
                      : (selectedDevice.user_name || 'None')}
                  </p>
                </div>
                <div className="sm:col-span-2">
                  <span className="font-bold text-[#0F172A]">User-Agent String:</span>
                  <p className="font-mono text-[10px] bg-[#F8FAFC] p-2 rounded border border-[#E2E8F0] break-all select-all text-[#334155] mt-1">
                    {selectedDevice.user_agent || 'Standard Web Browser User-Agent'}
                  </p>
                </div>
              </div>
            </div>

            {/* Associated Accounts */}
            {selectedDevice.associated_accounts && selectedDevice.associated_accounts.length > 0 && (
              <div className="p-4 bg-white rounded-[12px] border border-[#E0DDD6] space-y-2">
                <h5 className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider">
                  Associated Accounts ({selectedDevice.associated_accounts.length})
                </h5>
                <div className="divide-y divide-[#E0DDD6] max-h-32 overflow-y-auto">
                  {selectedDevice.associated_accounts.map((acc: any) => (
                    <div key={acc.external_id} className="py-1.5 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-mono font-bold text-[#002D72]">{acc.external_id}</span>
                        <span className="text-[#64748B] ml-2 font-medium">{acc.customer_name}</span>
                      </div>
                      <span className="font-mono font-semibold text-[#0F172A]">{acc.currency}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Sessions */}
            {selectedDevice.recent_sessions && selectedDevice.recent_sessions.length > 0 && (
              <div className="p-4 bg-white rounded-[12px] border border-[#E0DDD6] space-y-2">
                <h5 className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider">
                  Recent Device Sessions ({selectedDevice.recent_sessions.length})
                </h5>
                <div className="divide-y divide-[#E0DDD6] max-h-36 overflow-y-auto">
                  {selectedDevice.recent_sessions.map((sess: any) => (
                    <div key={sess.id} className="py-1.5 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-semibold text-[#0F172A]">{sess.customer}</span>
                        <span className="font-mono text-[11px] text-[#64748B] ml-2">({sess.ip_address})</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-[#64748B]">
                          {new Date(sess.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        {sess.is_active ? (
                          <span className="text-[10px] font-bold text-[#065F46] bg-[#ECFDF5] px-1.5 py-0.5 rounded">ACTIVE</span>
                        ) : (
                          <span className="text-[10px] text-[#64748B]">Ended</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Transactions Conducted on Device */}
            {selectedDevice.recent_transactions && selectedDevice.recent_transactions.length > 0 && (
              <div className="p-4 bg-white rounded-[12px] border border-[#E0DDD6] space-y-2">
                <h5 className="font-bold text-[#002D72] uppercase text-[11px] tracking-wider flex items-center gap-1.5">
                  <ArrowRightLeft className="w-3.5 h-3.5 text-[#002D72]" />
                  Transactions Conducted on Hardware ({selectedDevice.recent_transactions.length})
                </h5>
                <div className="divide-y divide-[#E0DDD6] max-h-44 overflow-y-auto">
                  {selectedDevice.recent_transactions.map((tx: any) => (
                    <div key={tx.external_id || tx.id} className="py-2 flex items-center justify-between text-xs">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-[#002D72]">{tx.external_id}</span>
                          <span className="text-[#64748B] text-[11px]">→</span>
                          <span className="font-medium text-[#0F172A]">{tx.counterparty || 'Counterparty'}</span>
                        </div>
                        {tx.timestamp && (
                          <div className="text-[10px] text-[#64748B] font-mono mt-0.5">
                            {new Date(tx.timestamp).toLocaleString()}
                          </div>
                        )}
                      </div>
                      <div className="text-right">
                        <span className="font-mono font-bold text-[#002D72] text-xs">
                          {Number(tx.amount || 0).toLocaleString()} {tx.currency || 'EGP'}
                        </span>
                        <div className="mt-0.5">
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#ECFDF5] text-[#065F46]">
                            {tx.status || 'COMPLETED'}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between gap-3 pt-3 border-t border-[#E0DDD6]">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  const devId = selectedDevice.external_id || selectedDevice.device_id || selectedDevice.id;
                  setSelectedDevice(null);
                  navigate(`/admin/network-analysis?entity=${encodeURIComponent(devId)}`);
                }}
              >
                <span>Inspect in Network Topology</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={() => setSelectedDevice(null)}
              >
                Close Dossier
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
