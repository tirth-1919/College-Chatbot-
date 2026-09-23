import { useState } from 'react';
import { adminApi } from '../services/adminApi';
import {
  Building2, CheckCircle2, AlertCircle, ArrowLeft, Search,
  Globe, Mail, User, Phone, MapPin, FileText, Shield, Copy, Check
} from 'lucide-react';

export default function CollegeRegisterPage({ onBackToLogin }) {
  const [activeTab, setActiveTab] = useState('register'); // 'register' | 'status'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [submittedApp, setSubmittedApp] = useState(null);
  const [copied, setCopied] = useState(false);

  // Status check states
  const [queryAppId, setQueryAppId] = useState('');
  const [statusResult, setStatusResult] = useState(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState('');

  // Form fields
  const [formData, setFormData] = useState({
    college_name: '',
    college_code: '',
    official_website: '',
    official_email: '',
    contact_person: '',
    contact_email: '',
    contact_phone: '',
    address: '',
    city: '',
    state: '',
    country: 'India',
    university_affiliation: '',
    logo_url: '',
    description: '',
    auth_document_path: '',
    additional_info: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await adminApi.registerCollege(formData);
      setSubmittedApp(res);
    } catch (err) {
      setError(err.message || 'Failed to submit college registration');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckStatus = async (e) => {
    if (e) e.preventDefault();
    if (!queryAppId.trim()) {
      setStatusError('Please enter an Application ID (e.g. COL-2026-00001)');
      return;
    }
    setStatusError('');
    setStatusResult(null);
    setStatusLoading(true);

    try {
      const res = await adminApi.getRegistrationStatus(queryAppId.trim());
      setStatusResult(res);
    } catch (err) {
      setStatusError(err.message || 'Application not found. Please verify your Application ID.');
    } finally {
      setStatusLoading(false);
    }
  };

  const handleCopyId = (id) => {
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'radial-gradient(ellipse 80% 60% at 50% -20%, rgba(11,10,62,0.8) 0%, transparent 70%), var(--bg-primary)',
      padding: '40px 20px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      color: '#fff'
    }}>
      {/* Top Header */}
      <div style={{ width: '100%', maxWidth: 840, marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button
          onClick={onBackToLogin}
          className="btn-secondary"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 16px', fontSize: '0.85rem' }}
        >
          <ArrowLeft size={16} />
          <span>Back to Sign In</span>
        </button>

        <div style={{ display: 'flex', background: 'rgba(255,255,255,0.06)', borderRadius: 10, padding: 4 }}>
          <button
            onClick={() => setActiveTab('register')}
            style={{
              background: activeTab === 'register' ? 'var(--primary)' : 'transparent',
              border: 'none', color: '#fff', padding: '8px 16px', borderRadius: 8,
              fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s'
            }}
          >
            Register College
          </button>
          <button
            onClick={() => setActiveTab('status')}
            style={{
              background: activeTab === 'status' ? 'var(--primary)' : 'transparent',
              border: 'none', color: '#fff', padding: '8px 16px', borderRadius: 8,
              fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s'
            }}
          >
            Check Status
          </button>
        </div>
      </div>

      {/* Main Container */}
      <div style={{ width: '100%', maxWidth: 840 }}>
        {activeTab === 'register' && !submittedApp && (
          <div className="glass-card" style={{ padding: '36px 40px' }}>
            <div style={{ textAlign: 'center', marginBottom: 30 }}>
              <div style={{
                width: 56, height: 56, borderRadius: 14,
                background: 'linear-gradient(135deg, #0b0a3e, #1a2345)',
                border: '1px solid rgba(240,133,24,0.4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 16px', boxShadow: '0 0 25px rgba(240,133,24,0.15)'
              }}>
                <Building2 size={26} color="#f08518" />
              </div>
              <h1 style={{ fontSize: '1.6rem', fontWeight: 800, marginBottom: 8, letterSpacing: '-0.02em' }}>
                Register Your College
              </h1>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Join the Multi-College AI Assistant platform. Submit your institution details for Super Admin review.
              </p>
            </div>

            {error && (
              <div style={{
                background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: 8, padding: '12px 16px', marginBottom: 24,
                display: 'flex', alignItems: 'center', gap: 10, color: '#fca5a5', fontSize: '0.875rem'
              }}>
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              {/* Institution Details */}
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f08518', marginBottom: 14, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                  1. Institution Details
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div style={{ gridColumn: 'span 2' }}>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      College / Institution Name *
                    </label>
                    <input
                      name="college_name"
                      value={formData.college_name}
                      onChange={handleChange}
                      placeholder="e.g. Ahmedabad Institute of Technology"
                      className="input-field"
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      College Code (optional)
                    </label>
                    <input
                      name="college_code"
                      value={formData.college_code}
                      onChange={handleChange}
                      placeholder="e.g. AIT"
                      className="input-field"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Official Website URL *
                    </label>
                    <input
                      name="official_website"
                      value={formData.official_website}
                      onChange={handleChange}
                      placeholder="https://www.aitindia.in"
                      className="input-field"
                      type="url"
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Official College Email *
                    </label>
                    <input
                      name="official_email"
                      value={formData.official_email}
                      onChange={handleChange}
                      placeholder="admin@aitindia.in"
                      className="input-field"
                      type="email"
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      University / Board Affiliation
                    </label>
                    <input
                      name="university_affiliation"
                      value={formData.university_affiliation}
                      onChange={handleChange}
                      placeholder="e.g. Gujarat Technological University"
                      className="input-field"
                    />
                  </div>
                </div>
              </div>

              {/* Primary Contact Person */}
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f08518', marginBottom: 14, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                  2. Primary Contact Person
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Contact Person Name *
                    </label>
                    <input
                      name="contact_person"
                      value={formData.contact_person}
                      onChange={handleChange}
                      placeholder="e.g. Dr. Rajesh Patel"
                      className="input-field"
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Contact Email * (Admin Credentials sent here)
                    </label>
                    <input
                      name="contact_email"
                      value={formData.contact_email}
                      onChange={handleChange}
                      placeholder="rajesh.patel@aitindia.in"
                      className="input-field"
                      type="email"
                      required
                    />
                  </div>

                  <div style={{ gridColumn: 'span 2' }}>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Contact Phone *
                    </label>
                    <input
                      name="contact_phone"
                      value={formData.contact_phone}
                      onChange={handleChange}
                      placeholder="e.g. 9876543210"
                      className="input-field"
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Campus Address */}
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f08518', marginBottom: 14, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                  3. Campus Address
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 16 }}>
                  <div style={{ gridColumn: 'span 3' }}>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Address *
                    </label>
                    <input
                      name="address"
                      value={formData.address}
                      onChange={handleChange}
                      placeholder="Near Vasantnagar Township, Gota-Ognaj Road"
                      className="input-field"
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      City *
                    </label>
                    <input
                      name="city"
                      value={formData.city}
                      onChange={handleChange}
                      placeholder="Ahmedabad"
                      className="input-field"
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      State *
                    </label>
                    <input
                      name="state"
                      value={formData.state}
                      onChange={handleChange}
                      placeholder="Gujarat"
                      className="input-field"
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Country
                    </label>
                    <input
                      name="country"
                      value={formData.country}
                      onChange={handleChange}
                      placeholder="India"
                      className="input-field"
                    />
                  </div>
                </div>
              </div>

              {/* Additional Metadata */}
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f08518', marginBottom: 14, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                  4. Additional Information
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      College Logo URL (optional)
                    </label>
                    <input
                      name="logo_url"
                      value={formData.logo_url}
                      onChange={handleChange}
                      placeholder="https://www.aitindia.in/logo.png"
                      className="input-field"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Authorization / Verification Document Link
                    </label>
                    <input
                      name="auth_document_path"
                      value={formData.auth_document_path}
                      onChange={handleChange}
                      placeholder="Link to accreditation certificate or GTU letter"
                      className="input-field"
                    />
                  </div>

                  <div style={{ gridColumn: 'span 2' }}>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                      College Description & Highlights
                    </label>
                    <textarea
                      name="description"
                      value={formData.description}
                      onChange={handleChange}
                      rows={3}
                      placeholder="Brief overview of programs, campus, accreditation..."
                      className="input-field"
                      style={{ resize: 'vertical' }}
                    />
                  </div>
                </div>
              </div>

              {/* Submit button */}
              <button
                type="submit"
                disabled={loading}
                className="btn-primary"
                style={{
                  width: '100%', justifyContent: 'center', padding: '14px 24px',
                  fontSize: '1rem', fontWeight: 700, marginTop: 10
                }}
              >
                {loading ? 'Submitting Registration...' : 'Submit Registration'}
              </button>
            </form>
          </div>
        )}

        {/* Submission Confirmation Screen (Section 4) */}
        {submittedApp && (
          <div className="glass-card" style={{ padding: '48px 40px', textAlign: 'center', maxWidth: 600, margin: '0 auto' }}>
            <div style={{
              width: 72, height: 72, borderRadius: '50%',
              background: 'rgba(34,197,94,0.15)', border: '2px solid rgba(34,197,94,0.4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px'
            }}>
              <CheckCircle2 size={40} color="#22c55e" />
            </div>

            <h2 style={{ fontSize: '1.75rem', fontWeight: 800, marginBottom: 12 }}>
              Registration Submitted ✓
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: 28 }}>
              Your college registration request for <strong>{submittedApp.college_name}</strong> has been submitted successfully.
            </p>

            <div style={{
              background: 'rgba(11,10,62,0.8)', border: '1px solid rgba(240,133,24,0.3)',
              borderRadius: 12, padding: '24px', marginBottom: 28, textAlign: 'left'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Application ID
                  </div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f08518', letterSpacing: '0.05em' }}>
                    {submittedApp.application_id}
                  </div>
                </div>
                <button
                  onClick={() => handleCopyId(submittedApp.application_id)}
                  className="btn-secondary"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', padding: '6px 12px' }}
                >
                  {copied ? <Check size={14} color="#22c55e" /> : <Copy size={14} />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: 14 }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Status:</span>
                <span style={{
                  background: 'rgba(234,179,8,0.15)', color: '#facc15',
                  padding: '4px 10px', borderRadius: 9999, fontSize: '0.8rem', fontWeight: 700
                }}>
                  {submittedApp.status || 'PENDING APPROVAL'}
                </span>
              </div>
            </div>

            <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', marginBottom: 28 }}>
              {submittedApp.note || 'The request will be reviewed by the Platform Super Admin. You will be notified at your contact email once approved.'}
            </p>

            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button
                onClick={() => {
                  setQueryAppId(submittedApp.application_id);
                  setActiveTab('status');
                  setSubmittedApp(null);
                  handleCheckStatus();
                }}
                className="btn-secondary"
                style={{ padding: '10px 20px' }}
              >
                Track Status Now
              </button>
              <button
                onClick={onBackToLogin}
                className="btn-primary"
                style={{ padding: '10px 24px' }}
              >
                Return to Login
              </button>
            </div>
          </div>
        )}

        {/* Application Status Checker Tab (Section 5) */}
        {activeTab === 'status' && (
          <div className="glass-card" style={{ padding: '36px 40px', maxWidth: 640, margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
              <div style={{
                width: 52, height: 52, borderRadius: 14,
                background: 'rgba(240,133,24,0.15)', border: '1px solid rgba(240,133,24,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px'
              }}>
                <Search size={24} color="#f08518" />
              </div>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 6 }}>
                Check Registration Status
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Enter your unique Application ID (e.g. COL-2026-00001) to view the review status.
              </p>
            </div>

            <form onSubmit={handleCheckStatus} style={{ display: 'flex', gap: 10, marginBottom: 24 }}>
              <input
                value={queryAppId}
                onChange={e => setQueryAppId(e.target.value.toUpperCase())}
                placeholder="COL-2026-00001"
                className="input-field"
                style={{ flex: 1, letterSpacing: '0.05em', fontWeight: 600 }}
              />
              <button type="submit" disabled={statusLoading} className="btn-primary" style={{ padding: '10px 20px', flexShrink: 0 }}>
                {statusLoading ? 'Checking...' : 'Check Status'}
              </button>
            </form>

            {statusError && (
              <div style={{
                background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: 8, padding: '12px 16px', marginBottom: 20,
                display: 'flex', alignItems: 'center', gap: 10, color: '#fca5a5', fontSize: '0.875rem'
              }}>
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>{statusError}</span>
              </div>
            )}

            {statusResult && (
              <div style={{
                background: 'rgba(11,10,62,0.8)', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 12, padding: 24
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                  <div>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff', marginBottom: 4 }}>
                      {statusResult.college_name}
                    </h3>
                    <span style={{ fontSize: '0.8rem', color: '#f08518', fontWeight: 600 }}>
                      Code: {statusResult.college_code}
                    </span>
                  </div>
                  <span style={{
                    padding: '6px 14px', borderRadius: 9999, fontSize: '0.8rem', fontWeight: 700,
                    background:
                      statusResult.status === 'ACTIVE' ? 'rgba(34,197,94,0.15)' :
                      statusResult.status === 'REJECTED' ? 'rgba(239,68,68,0.15)' :
                      statusResult.status === 'NEED_MORE_INFORMATION' ? 'rgba(249,115,22,0.15)' :
                      'rgba(234,179,8,0.15)',
                    color:
                      statusResult.status === 'ACTIVE' ? '#4ade80' :
                      statusResult.status === 'REJECTED' ? '#f87171' :
                      statusResult.status === 'NEED_MORE_INFORMATION' ? '#fb923c' :
                      '#facc15'
                  }}>
                    {statusResult.status_label || statusResult.status}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '0.85rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: 14 }}>
                  <div>
                    <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.75rem' }}>Application ID</span>
                    <strong style={{ color: '#fff' }}>{statusResult.application_id}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.75rem' }}>Website</span>
                    <a href={statusResult.official_website} target="_blank" rel="noreferrer" style={{ color: '#f08518', textDecoration: 'none' }}>
                      {statusResult.official_website}
                    </a>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.75rem' }}>Contact Person</span>
                    <span style={{ color: '#fff' }}>{statusResult.contact_person}</span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.75rem' }}>Contact Email</span>
                    <span style={{ color: '#fff' }}>{statusResult.contact_email}</span>
                  </div>
                </div>

                {/* Rejection Reason display */}
                {statusResult.status === 'REJECTED' && statusResult.rejection_reason && (
                  <div style={{
                    marginTop: 16, padding: '12px 16px', background: 'rgba(239,68,68,0.12)',
                    border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, color: '#fca5a5', fontSize: '0.85rem'
                  }}>
                    <div style={{ fontWeight: 700, marginBottom: 4 }}>Rejection Reason:</div>
                    <div>{statusResult.rejection_reason}</div>
                  </div>
                )}

                {/* Need more information message */}
                {statusResult.status === 'NEED_MORE_INFORMATION' && statusResult.review_notes && (
                  <div style={{
                    marginTop: 16, padding: '12px 16px', background: 'rgba(249,115,22,0.12)',
                    border: '1px solid rgba(249,115,22,0.3)', borderRadius: 8, color: '#fed7aa', fontSize: '0.85rem'
                  }}>
                    <div style={{ fontWeight: 700, marginBottom: 4 }}>Information Requested by Super Admin:</div>
                    <div>{statusResult.review_notes}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
