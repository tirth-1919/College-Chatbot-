import { useEffect, useState } from 'react';
import { AdminAuthProvider, useAdminAuth } from './context/AdminAuthContext';
import { adminApi } from './services/adminApi';
import LoginPage from './pages/LoginPage';
import CollegeRegisterPage from './pages/CollegeRegisterPage';
import FirstPasswordChangePage from './pages/FirstPasswordChangePage';
import AdminLayout from './components/AdminLayout';
import DashboardView from './views/DashboardView';
import KnowledgeView from './views/KnowledgeView';
import CategoriesView from './views/CategoriesView';
import CategoryDetailView from './views/CategoryDetailView';
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
import ApprovalCenterView from './views/ApprovalCenterView';
import CollegesView from './views/CollegesView';
import CollegeDetailsView from './views/CollegeDetailsView';
import SmartUploadView from './views/SmartUploadView';
import ChangeRequestsView from './views/ChangeRequestsView';

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
  approval_center: ApprovalCenterView,
  colleges: CollegesView,
  smart_upload: SmartUploadView,
  change_requests: ChangeRequestsView,
};

function AdminApp() {
  const { user, loading } = useAdminAuth();
  const [activeView, setActiveView] = useState('dashboard');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [currentPath, setCurrentPath] = useState(window.location.pathname);

  useEffect(() => {
    const handlePopState = () => setCurrentPath(window.location.pathname);
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    if (user) {
      adminApi.getMetrics().then(setMetrics).catch(() => {});
    }
  }, [user]);

  // Public College Registration route - accessible without admin session and
  // never redirects to dashboard even if a token exists in local storage.
  if (currentPath === '/register-college') {
    return (
      <CollegeRegisterPage
        onBackToLogin={() => {
          window.history.pushState({}, '', '/');
          setCurrentPath('/');
        }}
      />
    );
  }

  // Dedicated College Details route (§25/§27): /super-admin/colleges/{college_id}
  // The database ID is the authoritative identifier; direct links work on refresh
  // because the view always re-fetches the college from the backend.
  const collegeDetailsMatch = currentPath.match(/^\/super-admin\/colleges\/([0-9a-fA-F-]{8,})\/?$/);
  if (collegeDetailsMatch) {
    return (
      <AdminLayout activeView="colleges" onNavChange={(key) => {
        window.history.pushState({}, '', '/');
        setCurrentPath('/');
        setActiveView(key === 'colleges' ? 'colleges' : key);
      }}>
        <CollegeDetailsView
          collegeId={collegeDetailsMatch[1]}
          onNavChange={(key) => {
            window.history.pushState({}, '', '/');
            setCurrentPath('/');
            setActiveView(key === 'colleges' ? 'colleges' : key);
          }}
        />
      </AdminLayout>
    );
  }

  // Colleges list route (§2): /super-admin/colleges — also handled when the
  // sidebar's `colleges` view is activated so the URL matches the navigation.
  const collegesListActive = currentPath === '/super-admin/colleges' || activeView === 'colleges';

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
        <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Loading Admin Platform...</div>
      </div>
    );
  }

  if (!user) return <LoginPage />;

  // Enforce first-time password change for provisioned college admins
  if (user.must_change_password) {
    return <FirstPasswordChangePage />;
  }

  // When a token exists but we are on a colleges route, show the right page.
  useEffect(() => {
    if (currentPath === '/super-admin/colleges') setActiveView('colleges');
  }, [currentPath]);

  const ActiveView = VIEW_MAP[activeView] || DashboardView;

  const layoutChildren = collegesListActive
    ? <CollegesView />
    : activeView === 'kdb_categories'
    ? (selectedCategory
      ? <CategoryDetailView category={selectedCategory} onBack={() => setSelectedCategory(null)} />
      : <CategoriesView onOpenCategory={setSelectedCategory} />)
    : <ActiveView onNavChange={(key) => {
        window.history.pushState({}, '', '/');
        setCurrentPath('/');
        setActiveView(key);
      }} />;

  return (
    <AdminLayout activeView={activeView} onNavChange={setActiveView} metrics={metrics}>
      {layoutChildren}
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
