import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { AlertTriangle, ShieldAlert, CheckCircle, Bell, RefreshCw, Check } from 'lucide-react';

export default function AlertsView() {
  const [alerts, setAlerts] = useState([]);
  const [securityEvents, setSecurityEvents] = useState([]);
  const [activeTab, setActiveTab] = useState('alerts'); // 'alerts' or 'security'
  const [severityFilter, setSeverityFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [alertsRes, secRes] = await Promise.all([
        adminApi.getAlerts({ severity: severityFilter }).catch(() => ({ alerts: [] })),
        adminApi.getSecurityEvents().catch(() => ({ events: [] }))
      ]);
      setAlerts(alertsRes.alerts || []);
      setSecurityEvents(secRes.events || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [severityFilter]);

  const handleAcknowledge = async (id) => {
    try {
      await adminApi.acknowledgeAlert(id);
      setActionMessage('Alert acknowledged.');
      fetchData();
    } catch (err) {
      setActionMessage(`Error: ${err.message}`);
    }
  };

  const handleResolve = async (id) => {
    const notes = prompt('Enter resolution notes:');
    if (notes !== null) {
      try {
        await adminApi.resolveAlert(id, notes);
        setActionMessage('Alert resolved.');
        fetchData();
      } catch (err) {
        setActionMessage(`Error: ${err.message}`);
      }
    }
  };

  const getSeverityBadge = (sev) => {
    const color = sev === 'CRITICAL' ? '#ef4444' :
                  sev === 'ERROR' ? '#f97316' :
                  sev === 'WARNING' ? '#eab308' : '#3b82f6';
    return (
      <span style={{
        padding: '3px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 700,
        background: `${color}20`, color: color, border: `1px solid ${color}40`
      }}>
        {sev}
      </span>
    );
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            System Alerts & Security Events
          </h1>
          <p style={{ margin: '6px 0 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Real-time alerting for provider failures, queue thresholds, database health, and security intrusions.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            onClick={fetchData}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 16px', background: 'var(--card-bg)', border: '1px solid var(--border)',
              borderRadius: 8, color: 'var(--text-primary)', cursor: 'pointer'
            }}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {actionMessage && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 20,
          background: 'rgba(240, 133, 24, 0.15)', border: '1px solid #f08518',
          color: '#f08518', fontSize: '0.875rem'
        }}>
          {actionMessage}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 12, borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
        <button
          onClick={() => setActiveTab('alerts')}
          style={{
            padding: '10px 20px', background: 'none', border: 'none',
            borderBottom: activeTab === 'alerts' ? '2px solid #f08518' : '2px solid transparent',
            color: activeTab === 'alerts' ? '#f08518' : 'var(--text-muted)',
            fontWeight: 600, cursor: 'pointer'
          }}
        >
          System Alerts ({alerts.length})
        </button>
        <button
          onClick={() => setActiveTab('security')}
          style={{
            padding: '10px 20px', background: 'none', border: 'none',
            borderBottom: activeTab === 'security' ? '2px solid #f08518' : '2px solid transparent',
            color: activeTab === 'security' ? '#f08518' : 'var(--text-muted)',
            fontWeight: 600, cursor: 'pointer'
          }}
        >
          Security Events Log ({securityEvents.length})
        </button>
      </div>

      {activeTab === 'alerts' && (
        <div style={{ background: 'var(--card-bg)', borderRadius: 10, border: '1px solid var(--border)', padding: 20 }}>
          {alerts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              <CheckCircle size={48} color="#10b981" style={{ margin: '0 auto 12px' }} />
              <div>All systems healthy. No active alerts.</div>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                    <th style={{ padding: 12 }}>Severity</th>
                    <th style={{ padding: 12 }}>Source</th>
                    <th style={{ padding: 12 }}>Title & Message</th>
                    <th style={{ padding: 12 }}>Status</th>
                    <th style={{ padding: 12 }}>Created</th>
                    <th style={{ padding: 12, textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((a) => (
                    <tr key={a.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: 12 }}>{getSeverityBadge(a.severity)}</td>
                      <td style={{ padding: 12, fontWeight: 600 }}>{a.source}</td>
                      <td style={{ padding: 12, maxWidth: 380 }}>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{a.title}</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 4 }}>{a.message}</div>
                      </td>
                      <td style={{ padding: 12 }}>
                        <span style={{
                          padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem',
                          background: a.status === 'RESOLVED' ? '#10b98120' : '#ef444420',
                          color: a.status === 'RESOLVED' ? '#10b981' : '#ef4444'
                        }}>
                          {a.status}
                        </span>
                      </td>
                      <td style={{ padding: 12, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                      </td>
                      <td style={{ padding: 12, textAlign: 'right' }}>
                        {a.status === 'OPEN' && (
                          <div style={{ display: 'inline-flex', gap: 6 }}>
                            <button
                              onClick={() => handleAcknowledge(a.id)}
                              style={{
                                padding: '4px 8px', background: '#3b82f6', color: '#fff',
                                border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: '0.75rem'
                              }}
                            >
                              Ack
                            </button>
                            <button
                              onClick={() => handleResolve(a.id)}
                              style={{
                                padding: '4px 8px', background: '#10b981', color: '#fff',
                                border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: '0.75rem'
                              }}
                            >
                              Resolve
                            </button>
                          </div>
                        )}
                        {a.status === 'ACKNOWLEDGED' && (
                          <button
                            onClick={() => handleResolve(a.id)}
                            style={{
                              padding: '4px 8px', background: '#10b981', color: '#fff',
                              border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: '0.75rem'
                            }}
                          >
                            Resolve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'security' && (
        <div style={{ background: 'var(--card-bg)', borderRadius: 10, border: '1px solid var(--border)', padding: 20 }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: '0 0 16px', color: 'var(--text-primary)' }}>
            Security Incidents & Access Logs
          </h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: 12 }}>Event Type</th>
                  <th style={{ padding: 12 }}>Severity</th>
                  <th style={{ padding: 12 }}>IP Source</th>
                  <th style={{ padding: 12 }}>Details</th>
                  <th style={{ padding: 12 }}>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {securityEvents.map((ev) => (
                  <tr key={ev.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: 12, fontWeight: 600 }}>{ev.event_type}</td>
                    <td style={{ padding: 12 }}>{getSeverityBadge(ev.severity || 'INFO')}</td>
                    <td style={{ padding: 12, fontFamily: 'monospace' }}>{ev.source_ip || 'Internal'}</td>
                    <td style={{ padding: 12, color: 'var(--text-muted)' }}>{JSON.stringify(ev.details || {})}</td>
                    <td style={{ padding: 12, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {ev.created_at ? new Date(ev.created_at).toLocaleString() : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
