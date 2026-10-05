import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SmartUploadView from './SmartUploadView';
import { adminApi } from '../services/adminApi';
import { useAdminAuth } from '../context/AdminAuthContext';

vi.mock('../services/adminApi', () => ({
  adminApi: {
    getStagedUploads: vi.fn(),
    approveStagedUpload: vi.fn(),
    rejectStagedUpload: vi.fn(),
    smartUpload: vi.fn(),
  },
}));

vi.mock('../context/AdminAuthContext', () => ({
  useAdminAuth: vi.fn(),
}));

const pendingRecord = {
  id: 'staged-1',
  filename: 'admission.pdf',
  file_size: 1024,
  file_type: 'PDF',
  detected_category: 'admission_process',
  course_department: 'All Programs',
  academic_year: '2026-27',
  confidence_score: 0.98,
  status: 'PENDING_REVIEW',
};

beforeEach(() => {
  vi.clearAllMocks();
  adminApi.getStagedUploads.mockResolvedValue([pendingRecord]);
});

describe('SmartUploadView approval visibility', () => {
  it('shows Approve & Ingest to Super Admin users', async () => {
    useAdminAuth.mockReturnValue({ user: { role: 'SUPER_ADMIN' } });

    render(<SmartUploadView />);

    expect(await screen.findByRole('button', { name: 'Approve & Ingest' })).toBeInTheDocument();
  });

  it('hides approval actions and shows the awaiting message for the actual College Admin role', async () => {
    useAdminAuth.mockReturnValue({ user: { role: 'COLLEGE-ADMIN' } });

    render(<SmartUploadView />);

    expect(await screen.findByText('Awaiting Super Admin Approval')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Approve & Ingest' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reject' })).not.toBeInTheDocument();
    expect(screen.getByText('ADMISSION PROCESS')).toBeInTheDocument();
  });
});
