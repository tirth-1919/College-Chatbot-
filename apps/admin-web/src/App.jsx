import { useEffect, useState } from 'react';
import { AdminAuthProvider, useAdminAuth } from './context/AdminAuthContext';
import { adminApi } from './services/adminApi';
import LoginPage from './pages/LoginPage';
import AdminLayout from './components/AdminLayout';
import DashboardView from './views/DashboardView';
import KnowledgeView from './views/KnowledgeView';
import WebsiteView from './views/WebsiteView';
import DocumentsView from './views/DocumentsView';
import ImagesView from './views/ImagesView';
import ConflictsView from './views/ConflictsView';
import AiControlView from './views/AiControlView';
import UsersView from './views/UsersView';
import GapsView from './views/GapsView';
import AuditView from './views/AuditView';
import SettingsView from './views/SettingsView';
import AutomationView from './views/AutomationView';
import AlertsView from './views/AlertsView';
import EvaluationView from './views/EvaluationView';

const VIEW_MAP = {
  dashboard: DashboardView,
  knowledge: KnowledgeView,
  website: WebsiteView,
  documents: DocumentsView,
  images: ImagesView,
  conflicts: ConflictsView,
  ai: AiControlView,
  users: UsersView,
  gaps: GapsView,
  feedback: GapsView,
  audit: AuditView,
  settings: SettingsView,
  automation: AutomationView,
  alerts: AlertsView,
  evaluation: EvaluationView,
};

function AdminApp() {
  const { user, loading } = useAdminAuth();
  const [activeView, setActiveView] = useState('dashboard');
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    if (user) {
      adminApi.getMetrics().then(setMetrics).catch(() => {});
    }
  }, [user]);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', flexDirection: 'column', gap: 16,
        background: 'var(--bg-primary)'
      }}>
        <div style={{
          width: 52, height: 52, borderRadius: 12,
          background: 'linear-gradient(135deg, #0b0a3e, #1a2345)',
          border: '1px solid rgba(240,133,24,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          animation: 'pulse 1.5s ease-in-out infinite'
        }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L3 7v10l9 5 9-5V7L12 2z" stroke="#f08518" strokeWidth="2" fill="none" />
          </svg>
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Loading AIT Admin...</div>
      </div>
    );
  }

  if (!user) return <LoginPage />;

  const ActiveView = VIEW_MAP[activeView] || DashboardView;

  return (
    <AdminLayout activeView={activeView} onNavChange={setActiveView} metrics={metrics}>
      <ActiveView />
    </AdminLayout>
  );
}

export default function App() {
  return (
    <AdminAuthProvider>
      <AdminApp />
    </AdminAuthProvider>
  );
}
