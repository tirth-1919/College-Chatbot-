import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Award, RotateCcw, Play, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';

export default function EvaluationView() {
  const [evaluations, setEvaluations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await adminApi.getEvaluations();
      setEvaluations(res.evaluations || []);
    } catch (err) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunEvaluation = async () => {
    setEvaluating(true);
    try {
      const res = await adminApi.runEvaluation();
      setActionMessage(`Evaluation completed! Score: ${res.accuracy_score}% (${res.passed_queries}/${res.total_queries} passed)`);
      fetchData();
    } catch (err) {
      setActionMessage(`Evaluation failed: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  const latest = evaluations[0];

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            Automated Knowledge Evaluation & Rollback
          </h1>
          <p style={{ margin: '6px 0 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Automated golden test suite verifying all 16 academic domains: BCA, MCA, MBA, B.Tech, Fees, Faculty & Placements.
          </p>
        </div>
        <button
          onClick={handleRunEvaluation}
          disabled={evaluating}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 20px', background: '#0b0a3e', border: '1px solid #f08518',
            borderRadius: 8, color: '#f08518', fontWeight: 700, cursor: 'pointer'
          }}
        >
          <Play size={16} fill="#f08518" className={evaluating ? 'animate-spin' : ''} />
          {evaluating ? 'Evaluating Golden Suite...' : 'Run Golden Evaluation'}
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

      {/* Latest Evaluation Status */}
      {latest && (
        <div style={{
          background: 'var(--card-bg)', borderRadius: 10, border: '1px solid var(--border)',
          padding: 24, marginBottom: 24
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <span style={{
                padding: '3px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 700,
                background: latest.regression_detected ? '#ef444420' : '#10b98120',
                color: latest.regression_detected ? '#ef4444' : '#10b981',
                border: `1px solid ${latest.regression_detected ? '#ef4444' : '#10b981'}`
              }}>
                {latest.regression_detected ? 'REGRESSION DETECTED — PUBLISH BLOCKED' : 'QUALITY VERIFIED — READY TO PUBLISH'}
              </span>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 700, margin: '12px 0 4px', color: 'var(--text-primary)' }}>
                Accuracy Score: {latest.accuracy_score}% ({latest.passed_queries}/{latest.total_queries} passed)
              </h2>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Version: {latest.version_tag} | Evaluated by: {latest.evaluated_by} | {new Date(latest.created_at).toLocaleString()}
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 800, color: latest.accuracy_score >= 80 ? '#10b981' : '#f08518' }}>
                {latest.accuracy_score}%
              </div>
            </div>
          </div>

          {/* 16 Domains Score Grid */}
          <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '24px 0 12px', color: 'var(--text-primary)' }}>
            Domain Coverage Matrix (16 Core Academic Tracks)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
            {Object.entries(latest.domain_scores || {}).map(([domain, score]) => (
              <div
                key={domain}
                style={{
                  background: 'var(--bg-primary)', padding: '12px', borderRadius: 8,
                  border: '1px solid var(--border)'
                }}
              >
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 4 }}>{domain}</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: score >= 80 ? '#10b981' : score >= 50 ? '#f08518' : '#ef4444' }}>
                  {score}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Historical Evaluations Table */}
      <div style={{ background: 'var(--card-bg)', borderRadius: 10, border: '1px solid var(--border)', padding: 20 }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: '0 0 16px', color: 'var(--text-primary)' }}>
          Historical Evaluation Runs
        </h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: 12 }}>Version Tag</th>
                <th style={{ padding: 12 }}>Accuracy Score</th>
                <th style={{ padding: 12 }}>Pass / Total</th>
                <th style={{ padding: 12 }}>Regression Gating</th>
                <th style={{ padding: 12 }}>Evaluated At</th>
              </tr>
            </thead>
            <tbody>
              {evaluations.map((ev) => (
                <tr key={ev.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: 12, fontWeight: 600, fontFamily: 'monospace' }}>{ev.version_tag}</td>
                  <td style={{ padding: 12, fontWeight: 700, color: ev.accuracy_score >= 80 ? '#10b981' : '#f08518' }}>
                    {ev.accuracy_score}%
                  </td>
                  <td style={{ padding: 12 }}>{ev.passed_queries} / {ev.total_queries}</td>
                  <td style={{ padding: 12 }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem',
                      background: ev.regression_detected ? '#ef444420' : '#10b98120',
                      color: ev.regression_detected ? '#ef4444' : '#10b981'
                    }}>
                      {ev.regression_detected ? 'REGRESSED' : 'PASSED'}
                    </span>
                  </td>
                  <td style={{ padding: 12, color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {ev.created_at ? new Date(ev.created_at).toLocaleString() : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
