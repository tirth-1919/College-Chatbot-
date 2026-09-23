import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { useAdminAuth } from '../context/AdminAuthContext';
import {
  BookOpen, Globe, Users, Cpu, AlertTriangle, GitMerge,
  Image, TrendingUp, Activity, Database, Zap, RefreshCw,
  CheckCircle, XCircle, Clock, Server, Wifi, Building2, UploadCloud,
  Mail, Phone, ExternalLink, ShieldCheck
} from 'lucide-react';

function MetricCard({ label, value, sub, icon: Icon, color = '#f08518', trend }) {
  return (
    <div className="glass-card" style={{ padding: '20px 22px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {label}
        </span>
        <div style={{
          width: 34, height: 34, borderRadius: 8,
          background: `rgba(${color === '#f08518' ? '240,133,24' : color === '#10b981' ? '16,185,129' : color === '#ef4444' ? '239,68,68' : '99,102,241'},0.15)`,
          border: `1px solid rgba(${color === '#f08518' ? '240,133,24' : color === '#10b981' ? '16,185,129' : color === '#ef4444' ? '239,68,68' : '99,102,241'},0.3)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <Icon size={16} color={color} />
        </div>
      </div>
      <div style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function LiveMonitorBanner({ data }) {
  if (!data) return null;
  return (
    <div className="glass-card" style={{
      padding: '12px 20px', marginBottom: 24,
      background: 'rgba(16,185,129,0.06)',
      border: '1px solid rgba(16,185,129,0.2)',
      display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#10b981', display: 'block' }} className="pulse-live" />
        <span style={{ fontWeight: 700, color: '#34d399', fontSize: '0.85rem' }}>LIVE</span>
      </div>
      {[
        { label: 'Sessions', val: data.active_sessions, icon: Users },
        { label: 'Gaps', val: data.unresolved_gaps, icon: GitMerge },
        { label: 'Conflicts', val: data.unresolved_conflicts, icon: AlertTriangle },
        { label: 'Circuit Open', val: data.circuit_open_models, icon: Zap },
        { label: 'DB', val: data.database_status, icon: Database },
        { label: 'Redis', val: data.redis_status, icon: Server },
      ].map(({ label, val, icon: Icon }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem' }}>
          <Icon size={13} color="var(--text-dim)" />
          <span style={{ color: 'var(--text-muted)' }}>{label}:</span>
          <strong style={{ color: '#f8fafc' }}>{val}</strong>
        </div>
      ))}
      <div style={{ marginLeft: 'auto', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
        Updated {new Date(data.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}

export default function DashboardView({ onNavChange }) {
  const { user } = useAdminAuth();
  const [metrics, setMetrics] = useState(null);
  const [currentCollege, setCurrentCollege] = useState(null);
  const [liveData, setLiveData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.getMetrics().then(setMetrics).catch(() => {}).finally(() => setLoading(false));

    if (user?.role === 'COLLEGE_ADMIN' || user?.college_id) {
      adminApi.getCurrentCollege().then(setCurrentCollege).catch(() => {});
    }

    // EventSource cannot send Authorization headers, so consume the SSE stream
    // through fetch instead of exposing the admin token in the URL.
    const controller = new AbortController();
    const consumeStream = async () => {
      const response = await adminApi.authFetch('/api/v1/admin/monitoring/live-stream', {
        signal: controller.signal,
      });
      if (!response.ok || !response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (!controller.signal.aborted) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';
        for (const event of events) {
          const dataLine = event.split('\n').find(line => line.startsWith('data: '));
          if (dataLine) {
            try { setLiveData(JSON.parse(dataLine.slice(6))); } catch {}
          }
        }
      }
    };
    consumeStream().catch(() => {});
    return () => controller.abort();
  }, [user]);

  const refresh = () => {
    setLoading(true);
    adminApi.getMetrics().then(setMetrics).finally(() => setLoading(false));
    if (user?.role === 'COLLEGE_ADMIN' || user?.college_id) {
      adminApi.getCurrentCollege().then(setCurrentCollege).catch(() => {});
    }
  };

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
      <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
        <Activity size={32} style={{ marginBottom: 12, opacity: 0.5 }} />
        <div>Loading dashboard metrics...</div>
      </div>
    </div>
  );

  const counts = metrics?.counts || {};
  const ai = metrics?.ai_telemetry || {};
  const isSuperAdmin = user?.role === 'SUPER_ADMIN';
  const collegeName = currentCollege?.name || user?.college_name || (isSuperAdmin ? 'Platform Super Admin' : 'College Assistant');

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 14 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 4 }}>
            {isSuperAdmin ? 'Platform Super Admin Dashboard' : `${collegeName} Control Center`}
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            {isSuperAdmin
              ? 'Multi-College SaaS Governance & System Telemetry'
              : `${currentCollege?.code || 'Tenant'} · Institutional AI Assistant Operations`}
          </p>
        </div>
        <button className="btn-secondary" onClick={refresh} style={{ gap: 8 }}>
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      {/* College Profile Banner for College Admin */}
      {!isSuperAdmin && currentCollege && (
        <div className="glass-card" style={{
          padding: '20px 24px', marginBottom: 24,
          background: 'linear-gradient(135deg, rgba(11,10,62,0.6), rgba(26,35,69,0.5))',
          border: '1px solid rgba(240,133,24,0.3)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <Building2 size={22} color="#f08518" />
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>{currentCollege.name}</h2>
              <span style={{
                background: 'rgba(240,133,24,0.15)', color: '#f08518', border: '1px solid rgba(240,133,24,0.3)',
                padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 700
              }}>
                {currentCollege.code}
              </span>
              <span style={{
                background: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)',
                padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4
              }}>
                <ShieldCheck size={12} /> ACTIVE TENANT
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              {currentCollege.official_website && (
                <a href={currentCollege.official_website} target="_blank" rel="noreferrer" style={{ color: '#f08518', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <ExternalLink size={13} /> {currentCollege.official_website}
                </a>
              )}
              {currentCollege.official_email && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Mail size={13} color="var(--text-dim)" /> {currentCollege.official_email}
                </span>
              )}
              {currentCollege.city && (
                <span>{currentCollege.city}, {currentCollege.state}</span>
              )}
              {currentCollege.university_affiliation && (
                <span>Affiliation: {currentCollege.university_affiliation}</span>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            {onNavChange && (
              <button
                className="btn-primary"
                onClick={() => onNavChange('smart_upload')}
                style={{ gap: 8, padding: '10px 18px', fontSize: '0.85rem' }}
              >
                <UploadCloud size={16} />
                Smart Upload Documents
              </button>
            )}
          </div>
        </div>
      )}

      {/* Super Admin Quick Bar */}
      {isSuperAdmin && onNavChange && (
        <div className="glass-card" style={{
          padding: '16px 20px', marginBottom: 24,
          background: 'linear-gradient(135deg, rgba(240,133,24,0.1), rgba(11,10,62,0.4))',
          border: '1px solid rgba(240,133,24,0.3)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12
        }}>
          <div>
            <strong style={{ color: '#fff', fontSize: '0.95rem' }}>Super Admin Governance</strong>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: '2px 0 0' }}>
              Inspect pending registrations, approve colleges, and provision credentials
            </p>
          </div>
          <button
            className="btn-primary"
            onClick={() => onNavChange('approval_center')}
            style={{ gap: 8 }}
          >
            <Building2 size={16} />
            Open Approval Center
          </button>
        </div>
      )}

      <LiveMonitorBanner data={liveData} />

      {/* Primary metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <MetricCard label="Knowledge Entities" value={counts.entities ?? '—'} sub="Verified institutional facts" icon={BookOpen} />
        <MetricCard label="Official Images" value={counts.verified_images ?? '—'} sub="Verified campus media" icon={Image} color="#6366f1" />
        <MetricCard label="Documents" value={counts.documents ?? '—'} sub="RAG-indexed files" icon={Database} color="#10b981" />
        <MetricCard label="Registered Users" value={counts.users ?? '—'} sub="Students & admins" icon={Users} color="#6366f1" />
        <MetricCard label="Conversations" value={counts.conversations ?? '—'} sub="Total sessions" icon={Activity} color="#10b981" />
        <MetricCard label="Knowledge Gaps" value={counts.knowledge_gaps ?? '—'} sub="Awaiting resolution" icon={GitMerge} color={counts.knowledge_gaps > 5 ? '#ef4444' : '#f08518'} />
        <MetricCard label="Conflicts" value={counts.conflicts ?? '—'} sub="Unresolved discrepancies" icon={AlertTriangle} color={counts.conflicts > 0 ? '#ef4444' : '#10b981'} />
        <MetricCard label="Web Pages" value={counts.website_pages ?? '—'} sub={currentCollege?.official_website ? `Crawled ${currentCollege.official_website.replace(/^https?:\/\//, '')}` : 'Crawled institutional pages'} icon={Globe} color="#6366f1" />
      </div>

      {/* AI Telemetry */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 14, color: 'var(--text-muted)' }}>
          AI Telemetry (Last 24h)
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 14 }}>
          {[
            { label: 'Active Models', val: ai.active_models ?? '—', color: '#10b981' },
            { label: 'Circuit Healthy', val: ai.circuit_healthy ?? '—', color: '#10b981' },
            { label: 'Circuit Open', val: ai.circuit_open ?? 0, color: (ai.circuit_open > 0) ? '#ef4444' : '#10b981' },
            { label: 'Requests 24h', val: ai.requests_24h ?? 0, color: '#f08518' },
            { label: 'Failures 24h', val: ai.failures_24h ?? 0, color: (ai.failures_24h > 0) ? '#ef4444' : '#10b981' },
            { label: 'Failovers 24h', val: ai.failovers_24h ?? 0, color: '#f59e0b' },
            { label: 'Avg Latency', val: ai.avg_latency_ms !== undefined ? `${ai.avg_latency_ms}ms` : '—', color: '#6366f1' },
          ].map(m => (
            <div key={m.label} className="glass-card" style={{ padding: '14px 18px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase' }}>{m.label}</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: m.color }}>{m.val}</div>
            </div>
          ))}
        </div>
      </div>

      {/* System health badges (P1-16: Dynamic based on real telemetry) */}
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 14 }}>System Status</div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {[
            {
              label: 'Knowledge DB',
              status: liveData?.database_status === 'ONLINE' ? 'healthy' : (liveData ? 'warning' : 'neutral')
            },
            {
              label: 'AI Router',
              status: liveData ? (liveData.circuit_open_models > 0 ? 'warning' : 'healthy') : 'neutral'
            },
            {
              label: 'RAG Engine',
              status: counts.documents > 0 ? 'healthy' : 'neutral'
            },
            {
              label: 'Live Telemetry',
              status: liveData ? 'healthy' : 'neutral'
            },
            {
              label: 'Redis Cache',
              status: liveData?.redis_status === 'ONLINE' ? 'healthy' : 'neutral'
            },
          ].map(({ label, status }) => (
            <div key={label} className={`badge badge-${status}`}>
              {status === 'healthy' && <CheckCircle size={11} />}
              {status === 'warning' && <AlertTriangle size={11} />}
              {status === 'neutral' && <Clock size={11} />}
              {label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
