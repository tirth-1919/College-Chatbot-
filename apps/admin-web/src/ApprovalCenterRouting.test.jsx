import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { adminApi } from './services/adminApi';
import { useAdminAuth } from './context/AdminAuthContext';

vi.mock('./services/adminApi', () => ({
  adminApi: {
    getMetrics: vi.fn(),
    listColleges: vi.fn(),
    getStagedUploads: vi.fn(),
    approveStagedUpload: vi.fn(),
    rejectStagedUpload: vi.fn(),
  },
}));

vi.mock('./context/AdminAuthContext', () => ({
  AdminAuthProvider: ({ children }) => children,
  useAdminAuth: vi.fn(),
}));

describe('Approval Center routing', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/');
    useAdminAuth.mockReturnValue({
      user: { role: 'SUPER_ADMIN', full_name: 'Platform Admin' },
      loading: false,
    });
    adminApi.getMetrics.mockResolvedValue({ counts: {} });
    adminApi.listColleges.mockResolvedValue([]);
    adminApi.getStagedUploads.mockResolvedValue([{
      id: 'smart-1', filename: 'ait-admissions.pdf', detected_category: 'admission_process',
      course_department: 'Computer Science', academic_year: '2026-27', confidence_score: 0.94,
      status: 'PENDING_REVIEW',
    }]);
    adminApi.approveStagedUpload.mockResolvedValue({});
    adminApi.rejectStagedUpload.mockResolvedValue({});
  });

  it('navigates to the Approval Center component instead of All Colleges', async () => {
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: 'Approval Center' }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Super Admin Approval Center' })).toBeInTheDocument();
    });
    expect(screen.queryByRole('heading', { name: 'All Colleges' })).not.toBeInTheDocument();
    expect(window.location.pathname).toBe('/super-admin/approval-center');
  });

  it('shows the Smart Upload queue and Super Admin actions while retaining application tabs', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: 'Approval Center' }));

    expect(await screen.findByRole('button', { name: /Smart Upload \(1\)/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'All Applications' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Smart Upload \(1\)/ }));
    expect(await screen.findByText('ait-admissions.pdf')).toBeInTheDocument();
    expect(screen.getByText('admission process')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Approve & Ingest' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument();
  });
});
