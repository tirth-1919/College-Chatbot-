import { useState } from 'react';
import { useAdminAuth } from '../context/AdminAuthContext';
import {
  LayoutDashboard, BookOpen, Globe, FileText, Image, AlertTriangle,
  Cpu, Users, MessageSquare, TrendingUp, Shield, Settings,
  ChevronLeft, ChevronRight, LogOut, Activity, Bell, RefreshCw,
  Zap, Database, Lock, GitMerge
} from 'lucide-react';

const NAV_SECTIONS = [
  {
    label: 'Overview',
    items: [
      { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    ]
  },
  {
    label: 'Knowledge',
    items: [
      { key: 'knowledge', label: 'AIT Facts & Entities', icon: BookOpen },
      { key: 'website', label: 'Website Sync', icon: Globe },
      { key: 'documents', label: 'Documents', icon: FileText },
      { key: 'images', label: 'Image Library', icon: Image },
      { key: 'conflicts', label: 'Conflicts', icon: AlertTriangle, badge: 'conflicts' },
      { key: 'gaps', label: 'Knowledge Gaps', icon: GitMerge, badge: 'gaps' },
      { key: 'evaluation', label: 'Evaluation & Rollback', icon: Zap },
    ]
  },
  {
    label: 'AI System',
    items: [
      { key: 'ai', label: 'Providers & Models', icon: Cpu },
    ]
  },
  {
    label: 'Users & Feedback',
    items: [
      { key: 'users', label: 'Users', icon: Users },
      { key: 'feedback', label: 'Feedback', icon: MessageSquare },
    ]
  },
  {
    label: 'Operations & Engine',
    items: [
      { key: 'automation', label: 'Automation & Jobs', icon: RefreshCw },
      { key: 'alerts', label: 'Alerts & Incidents', icon: Bell },
      { key: 'audit', label: 'Audit & Security', icon: Lock },
      { key: 'settings', label: 'Settings & Prompts', icon: Settings },
    ]
  }
];

export default function AdminLayout({ children, activeView, onNavChange, metrics }) {
  const { user, logout } = useAdminAuth();
  const [collapsed, setCollapsed] = useState(false);

  const badgeCounts = {
    conflicts: metrics?.counts?.conflicts || 0,
    gaps: metrics?.counts?.knowledge_gaps || 0,
  };

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar */}
      <aside style={{
        width: collapsed ? 64 : 252,
        minWidth: collapsed ? 64 : 252,
        background: 'linear-gradient(180deg, #0a0f23 0%, #070913 100%)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.25s ease, min-width 0.25s ease',
        overflow: 'hidden',
        position: 'relative',
        zIndex: 10
      }}>
        {/* Sidebar header */}
        <div style={{
          padding: collapsed ? '18px 14px' : '18px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          minHeight: 68
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8, flexShrink: 0,
            background: 'linear-gradient(135deg, #0b0a3e, #1a2345)',
            border: '1px solid rgba(240,133,24,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Shield size={18} color="#f08518" />
          </div>
          {!collapsed && (
            <div>
              <div style={{ fontWeight: 800, fontSize: '0.9rem', lineHeight: 1.2, color: '#fff' }}>AIT Admin</div>
              <div style={{ fontSize: '0.7rem', color: '#f08518', fontWeight: 600 }}>Control Center</div>
            </div>
          )}
        </div>

        {/* Live indicator */}
        {!collapsed && (
          <div style={{
            margin: '12px 16px 0', padding: '8px 12px',
            borderRadius: 8, background: 'rgba(16,185,129,0.08)',
            border: '1px solid rgba(16,185,129,0.2)',
            display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.75rem'
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: '#10b981', flexShrink: 0
            }} className="pulse-live" />
            <span style={{ color: '#34d399', fontWeight: 600 }}>System LIVE</span>
            <Activity size={12} color="#34d399" style={{ marginLeft: 'auto' }} />
          </div>
        )}

        {/* Navigation */}
        <nav style={{ flex: 1, overflowY: 'auto', padding: '16px 0' }}>
          {NAV_SECTIONS.map(section => (
            <div key={section.label} style={{ marginBottom: 8 }}>
              {!collapsed && (
                <div style={{
                  padding: '4px 20px 6px',
                  fontSize: '0.65rem', fontWeight: 700,
                  color: 'var(--text-dim)',
                  textTransform: 'uppercase', letterSpacing: '0.1em'
                }}>
                  {section.label}
                </div>
              )}
              {section.items.map(item => {
                const Icon = item.icon;
                const isActive = activeView === item.key;
                const badgeCount = item.badge ? badgeCounts[item.badge] : 0;
                return (
                  <button
                    key={item.key}
                    id={`nav-${item.key}`}
                    onClick={() => onNavChange(item.key)}
                    style={{
                      width: '100%', border: 'none', cursor: 'pointer',
                      background: isActive
                        ? 'linear-gradient(90deg, rgba(240,133,24,0.18), rgba(240,133,24,0.05))'
                        : 'transparent',
                      display: 'flex', alignItems: 'center',
                      gap: 10, padding: collapsed ? '10px 18px' : '10px 20px',
                      color: isActive ? '#f08518' : 'var(--text-muted)',
                      fontSize: '0.875rem', fontWeight: isActive ? 600 : 400,
                      fontFamily: 'var(--font-sans)',
                      borderLeft: `2px solid ${isActive ? '#f08518' : 'transparent'}`,
                      transition: 'all 0.15s ease',
                      textAlign: 'left',
                      whiteSpace: 'nowrap'
                    }}
                    title={collapsed ? item.label : ''}
                  >
                    <Icon size={17} style={{ flexShrink: 0 }} />
                    {!collapsed && (
                      <>
                        <span style={{ flex: 1 }}>{item.label}</span>
                        {badgeCount > 0 && (
                          <span style={{
                            background: '#ef4444', color: '#fff',
                            borderRadius: 9999, padding: '1px 7px',
                            fontSize: '0.7rem', fontWeight: 700
                          }}>{badgeCount}</span>
                        )}
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* User footer */}
        <div style={{
          padding: collapsed ? '14px 10px' : '14px 16px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex', alignItems: 'center', gap: 10
        }}>
          <div style={{
            width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
            background: 'linear-gradient(135deg, #0b0a3e, #1a2345)',
            border: '1px solid rgba(240,133,24,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.8rem', fontWeight: 700, color: '#f08518'
          }}>
            {user?.full_name?.[0] || 'A'}
          </div>
          {!collapsed && (
            <>
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, truncate: true, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user?.full_name || 'Administrator'}
                </div>
                <div style={{ fontSize: '0.68rem', color: '#f08518', fontWeight: 600 }}>
                  {user?.role || 'ADMIN'}
                </div>
              </div>
              <button
                onClick={logout}
                style={{
                  background: 'none', border: 'none',
                  cursor: 'pointer', color: 'var(--text-dim)', padding: 4
                }}
                title="Sign out"
              >
                <LogOut size={16} />
              </button>
            </>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(v => !v)}
          style={{
            position: 'absolute', right: -12, top: 80,
            width: 24, height: 24, borderRadius: '50%',
            background: '#0e1428', border: '1px solid var(--border-subtle)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: 'var(--text-muted)', zIndex: 20
          }}
        >
          {collapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
        </button>
      </aside>

      {/* Main content */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        {/* Top bar */}
        <header style={{
          height: 56, padding: '0 24px',
          background: 'rgba(10,15,35,0.95)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          position: 'sticky', top: 0, zIndex: 5
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>AIT</span>
            <span style={{ color: 'var(--text-dim)' }}>/</span>
            <span style={{ color: '#f08518', fontSize: '0.8rem', fontWeight: 600, textTransform: 'capitalize' }}>
              {activeView}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
              {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
            <div style={{
              padding: '4px 10px', borderRadius: 6,
              background: 'rgba(16,185,129,0.1)',
              border: '1px solid rgba(16,185,129,0.2)',
              fontSize: '0.75rem', color: '#34d399', fontWeight: 600
            }}>
              {metrics?.system_health || 'OPTIMAL'}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{ flex: 1, padding: 24 }}>
          {children}
        </main>
      </div>
    </div>
  );
}
