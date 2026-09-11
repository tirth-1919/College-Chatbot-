import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import {
  BookOpen, Globe, Users, Cpu, AlertTriangle, GitMerge,
  Image, TrendingUp, Activity, Database, Zap, RefreshCw,
  CheckCircle, XCircle, Clock, Server, Wifi
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

export default function DashboardView() {
  const [metrics, setMetrics] = useState(null);
  const [liveData, setLiveData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.getMetrics().then(setMetrics).catch(() => {}).finally(() => setLoading(false));

    // SSE live stream
    const es = new EventSource('/api/v1/admin/monitoring/live-stream');
    es.onmessage = e => {
      try { setLiveData(JSON.parse(e.data)); } catch {}
    };
    return () => es.close();
  }, []);

  const refresh = () => {
    setLoading(true);
    adminApi.getMetrics().then(setMetrics).finally(() => setLoading(false));
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

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 4 }}>System Dashboard</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Ahmedabad Institute of Technology · AI Assistant Operations
          </p>
        </div>
        <button className="btn-secondary" onClick={refresh} style={{ gap: 8 }}>
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      <LiveMonitorBanner data={liveData} />

      {/* Primary metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <MetricCard label="Knowledge Entities" value={counts.entities || 0} sub="Verified institutional facts" icon={BookOpen} />
        <MetricCard label="Official Images" value={counts.verified_images || 0} sub="Verified campus media" icon={Image} color="#6366f1" />
        <MetricCard label="Documents" value={counts.documents || 0} sub="RAG-indexed files" icon={Database} color="#10b981" />
        <MetricCard label="Registered Users" value={counts.users || 0} sub="Students & admins" icon={Users} color="#6366f1" />
        <MetricCard label="Conversations" value={counts.conversations || 0} sub="Total sessions" icon={Activity} color="#10b981" />
        <MetricCard label="Knowledge Gaps" value={counts.knowledge_gaps || 0} sub="Awaiting resolution" icon={GitMerge} color={counts.knowledge_gaps > 5 ? '#ef4444' : '#f08518'} />
        <MetricCard label="Conflicts" value={counts.conflicts || 0} sub="Unresolved discrepancies" icon={AlertTriangle} color={counts.conflicts > 0 ? '#ef4444' : '#10b981'} />
        <MetricCard label="Web Pages" value={counts.website_pages || 0} sub="Crawled aitindia.in" icon={Globe} color="#6366f1" />
      </div>

      {/* AI Telemetry */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 14, color: 'var(--text-muted)' }}>
          AI Telemetry (Last 24h)
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 14 }}>
          {[
            { label: 'Active Models', val: ai.active_models || 0, color: '#10b981' },
            { label: 'Circuit Healthy', val: ai.circuit_healthy || 0, color: '#10b981' },
            { label: 'Circuit Open', val: ai.circuit_open || 0, color: ai.circuit_open > 0 ? '#ef4444' : '#10b981' },
            { label: 'Requests 24h', val: ai.requests_24h || 0, color: '#f08518' },
            { label: 'Failures 24h', val: ai.failures_24h || 0, color: ai.failures_24h > 0 ? '#ef4444' : '#10b981' },
            { label: 'Failovers 24h', val: ai.failovers_24h || 0, color: '#f59e0b' },
            { label: 'Avg Latency', val: `${ai.avg_latency_ms || 0}ms`, color: '#6366f1' },
          ].map(m => (
            <div key={m.label} className="glass-card" style={{ padding: '14px 18px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase' }}>{m.label}</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: m.color }}>{m.val}</div>
            </div>
          ))}
        </div>
      </div>

      {/* System health badges */}
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 14 }}>System Status</div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {[
            { label: 'Knowledge DB', status: 'healthy' },
            { label: 'AI Router', status: ai.circuit_open > 0 ? 'warning' : 'healthy' },
            { label: 'RAG Engine', status: 'healthy' },
            { label: 'Image Pipeline', status: 'healthy' },
            { label: 'Audit Logging', status: 'healthy' },
            { label: 'Semantic Cache', status: 'neutral' },
            { label: 'Website Crawler', status: 'healthy' },
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
