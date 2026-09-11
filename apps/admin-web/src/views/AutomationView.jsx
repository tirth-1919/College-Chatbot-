import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Play, RefreshCw, AlertOctagon, CheckCircle2, Clock, ShieldAlert, Cpu, Activity } from 'lucide-react';

export default function AutomationView() {
  const [jobs, setJobs] = useState([]);
  const [deadLetters, setDeadLetters] = useState([]);
  const [workerStatus, setWorkerStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggeringJob, setTriggeringJob] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [jobsRes, dlqRes, workerRes] = await Promise.all([
        adminApi.getAutomationJobs().catch(() => ({ jobs: [] })),
        adminApi.getDeadLetters().catch(() => ({ dead_letters: [] })),
        adminApi.getWorkerStatus().catch(() => null)
      ]);
      setJobs(jobsRes.jobs || []);
      setDeadLetters(dlqRes.dead_letters || []);
      setWorkerStatus(workerRes);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleTrigger = async (jobType) => {
    setTriggeringJob(jobType);
    try {
      const res = await adminApi.triggerJob(jobType);
      setActionMessage(`Job '${jobType}' enqueued. ID: ${res.job_id}`);
      fetchData();
    } catch (err) {
      setActionMessage(`Failed to trigger ${jobType}: ${err.message}`);
    } finally {
      setTriggeringJob(null);
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const handleRetryDLQ = async (jobId) => {
    try {
      await adminApi.retryDeadLetter(jobId);
      setActionMessage(`Job ${jobId} re-queued from Dead Letter Queue.`);
      fetchData();
    } catch (err) {
      setActionMessage(`Retry failed: ${err.message}`);
    }
  };

  const handleCancelDLQ = async (jobId) => {
    try {
      await adminApi.cancelDeadLetter(jobId);
      setActionMessage(`Job ${jobId} cancelled.`);
      fetchData();
    } catch (err) {
      setActionMessage(`Cancel failed: ${err.message}`);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            Automation Engine & Workers
          </h1>
          <p style={{ margin: '6px 0 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Production-grade task orchestrator running 24 automated institutional jobs with distributed locking & DLQ.
          </p>
        </div>
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

      {actionMessage && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 20,
          background: 'rgba(240, 133, 24, 0.15)', border: '1px solid #f08518',
          color: '#f08518', fontSize: '0.875rem'
        }}>
          {actionMessage}
        </div>
      )}

      {/* Worker Pool Status Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16, marginBottom: 24 }}>
        <div style={{ background: 'var(--card-bg)', padding: 18, borderRadius: 10, border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <Cpu size={20} color="#3b82f6" />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Worker Status</span>
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: workerStatus?.is_running ? '#10b981' : '#ef4444' }}>
            {workerStatus?.is_running ? 'RUNNING (HEALTHY)' : 'STOPPED'}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            ID: {workerStatus?.worker_id || 'N/A'}
          </div>
        </div>

        <div style={{ background: 'var(--card-bg)', padding: 18, borderRadius: 10, border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <Activity size={20} color="#10b981" />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Queue Depth</span>
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {workerStatus?.queue_depth ?? 0} Pending
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Registered handlers: {workerStatus?.registered_jobs_count ?? 24}
          </div>
        </div>

        <div style={{ background: 'var(--card-bg)', padding: 18, borderRadius: 10, border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <AlertOctagon size={20} color="#ef4444" />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Dead-Letter Queue</span>
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: deadLetters.length > 0 ? '#ef4444' : '#10b981' }}>
            {deadLetters.length} Failed
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Requires admin attention
          </div>
        </div>
      </div>

      {/* Dead-Letter Queue Section if any */}
      {deadLetters.length > 0 && (
        <div style={{
          background: 'var(--card-bg)', borderRadius: 10, border: '1px solid rgba(239, 68, 68, 0.4)',
          padding: 20, marginBottom: 28
        }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#ef4444', margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShieldAlert size={20} />
            Dead-Letter Queue (Failed Operations)
          </h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: 10 }}>Job ID</th>
                  <th style={{ padding: 10 }}>Type</th>
                  <th style={{ padding: 10 }}>Error Class</th>
                  <th style={{ padding: 10 }}>Error Details</th>
                  <th style={{ padding: 10 }}>Attempts</th>
                  <th style={{ padding: 10 }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {deadLetters.map((dl) => (
                  <tr key={dl.job_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: 10, fontFamily: 'monospace' }}>{dl.job_id}</td>
                    <td style={{ padding: 10, fontWeight: 600 }}>{dl.job_type}</td>
                    <td style={{ padding: 10, color: '#ef4444' }}>{dl.error_class || 'PERMANENT'}</td>
                    <td style={{ padding: 10, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{dl.error}</td>
                    <td style={{ padding: 10 }}>{dl.retry_count}/{dl.max_retries}</td>
                    <td style={{ padding: 10, display: 'flex', gap: 8 }}>
                      <button
                        onClick={() => handleRetryDLQ(dl.job_id)}
                        style={{
                          padding: '4px 10px', background: '#10b981', color: '#fff',
                          border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: '0.75rem'
                        }}
                      >
                        Retry
                      </button>
                      <button
                        onClick={() => handleCancelDLQ(dl.job_id)}
                        style={{
                          padding: '4px 10px', background: '#64748b', color: '#fff',
                          border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: '0.75rem'
                        }}
                      >
                        Cancel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 24 Automated Jobs Registry Table */}
      <div style={{ background: 'var(--card-bg)', borderRadius: 10, border: '1px solid var(--border)', padding: 20 }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 16px' }}>
          Registered Automated Jobs (24 Subsystems)
        </h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '12px 10px' }}>Job Name</th>
                <th style={{ padding: '12px 10px' }}>Description</th>
                <th style={{ padding: '12px 10px' }}>Last Run Status</th>
                <th style={{ padding: '12px 10px' }}>Last Executed</th>
                <th style={{ padding: '12px 10px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const last = job.last_run;
                const statusColor = last?.status === 'SUCCEEDED' ? '#10b981' :
                                   last?.status === 'RUNNING' ? '#3b82f6' :
                                   last?.status === 'DEAD_LETTER' ? '#ef4444' : '#64748b';
                return (
                  <tr key={job.job_type} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px 10px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {job.job_type}
                    </td>
                    <td style={{ padding: '12px 10px', color: 'var(--text-muted)', fontSize: '0.8rem', maxWidth: 350 }}>
                      {job.description}
                    </td>
                    <td style={{ padding: '12px 10px' }}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 6,
                        padding: '3px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 600,
                        background: `${statusColor}20`, color: statusColor
                      }}>
                        {last?.status || 'IDLE'}
                      </span>
                    </td>
                    <td style={{ padding: '12px 10px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      {last?.completed_at ? new Date(last.completed_at).toLocaleTimeString() : 'Never'}
                    </td>
                    <td style={{ padding: '12px 10px', textAlign: 'right' }}>
                      <button
                        onClick={() => handleTrigger(job.job_type)}
                        disabled={triggeringJob === job.job_type}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: 6,
                          padding: '6px 12px', background: '#0b0a3e', color: '#f08518',
                          border: '1px solid #f08518', borderRadius: 6, cursor: 'pointer',
                          fontSize: '0.8rem', fontWeight: 600
                        }}
                      >
                        <Play size={12} fill="#f08518" />
                        {triggeringJob === job.job_type ? 'Triggering...' : 'Run Now'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
