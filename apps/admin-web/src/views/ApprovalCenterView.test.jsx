import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ApprovalCenterView from './ApprovalCenterView';
import { adminApi } from '../services/adminApi';
import { useAdminAuth } from '../context/AdminAuthContext';

vi.mock('../services/adminApi', () => ({
  adminApi: {
    listColleges: vi.fn(),
    getStagedUploads: vi.fn(),
    approveStagedUpload: vi.fn(),
    rejectStagedUpload: vi.fn(),
    approveCollege: vi.fn(),
    rejectCollege: vi.fn(),
    requestInfoCollege: vi.fn(),
    sendCredentialsCollege: vi.fn(),
  },
}));

vi.mock('../context/AdminAuthContext', () => ({
  useAdminAuth: vi.fn(),
}));

const createMockPendingRecords = (count) =>
  Array.from({ length: count }, (_, index) => ({
    id: `smart-${index + 1}`,
    filename: `doc-${index + 1}.pdf`,
    detected_category: 'academic_calendar',
    course_department: 'Computer Science',
    academic_year: '2026-27',
    confidence_score: 0.95,
    status: 'PENDING_REVIEW',
  }));

describe('ApprovalCenterView - Smart Upload Bulk Approval', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAdminAuth.mockReturnValue({
      user: { role: 'SUPER_ADMIN', full_name: 'Super Admin' },
    });
    adminApi.listColleges.mockResolvedValue([]);
    adminApi.getStagedUploads.mockResolvedValue([]);
    adminApi.approveStagedUpload.mockResolvedValue({});
    adminApi.rejectStagedUpload.mockResolvedValue({});
  });

  it('renders one "Approve All & Ingest (7)" button at the top of the Smart Upload section when 7 records are pending', async () => {
    const records = createMockPendingRecords(7);
    adminApi.getStagedUploads.mockResolvedValue(records);

    render(<ApprovalCenterView />);

    // Switch to Smart Upload tab
    const smartUploadTab = await screen.findByRole('button', { name: 'Smart Upload (7)' });
    expect(smartUploadTab).toBeInTheDocument();
    fireEvent.click(smartUploadTab);

    // Verify exactly ONE bulk button at the top of the Smart Upload section
    const bulkButtons = screen.getAllByRole('button', { name: /Approve All & Ingest \(7\)/i });
    expect(bulkButtons).toHaveLength(1);
    expect(bulkButtons[0]).toBeEnabled();

    // Verify all 7 documents are listed in the table
    for (let i = 1; i <= 7; i++) {
      expect(screen.getByText(`doc-${i}.pdf`)).toBeInTheDocument();
    }
  });

  it('executes bulk approval for all 7 pending records, disables button while processing, refreshes list, and shows success feedback', async () => {
    const records = createMockPendingRecords(7);
    adminApi.getStagedUploads.mockResolvedValue(records);

    // Provide a controlled promise so we can verify the disabled state while in flight
    let resolveFirst;
    let firstCall = true;
    adminApi.approveStagedUpload.mockImplementation(() => {
      if (firstCall) {
        firstCall = false;
        return new Promise((resolve) => {
          resolveFirst = resolve;
        });
      }
      return Promise.resolve({});
    });

    render(<ApprovalCenterView />);

    fireEvent.click(await screen.findByRole('button', { name: 'Smart Upload (7)' }));

    const bulkButton = screen.getByRole('button', { name: /Approve All & Ingest \(7\)/i });
    expect(bulkButton).toBeEnabled();

    fireEvent.click(bulkButton);

    // Verify button is disabled during processing
    expect(bulkButton).toBeDisabled();

    // Resolve the in-flight approval so subsequent approvals continue
    resolveFirst({});

    await waitFor(() => {
      expect(adminApi.approveStagedUpload).toHaveBeenCalledTimes(7);
    });

    for (let i = 1; i <= 7; i++) {
      expect(adminApi.approveStagedUpload).toHaveBeenCalledWith(`smart-${i}`);
    }

    // Verify list was refreshed after completion
    expect(adminApi.getStagedUploads).toHaveBeenCalledTimes(2);

    // Verify success feedback
    expect(await screen.findByText('7 documents approved and ingested successfully.')).toBeInTheDocument();
  });

  it('only SUPER_ADMIN can see/use the bulk approval button; hides it for COLLEGE-ADMIN and COLLEGE_ADMIN', async () => {
    const records = createMockPendingRecords(7);
    adminApi.getStagedUploads.mockResolvedValue(records);

    // Test with hyphenated role COLLEGE-ADMIN
    useAdminAuth.mockReturnValue({
      user: { role: 'COLLEGE-ADMIN', full_name: 'College Admin' },
    });

    const { unmount } = render(<ApprovalCenterView />);
    fireEvent.click(await screen.findByRole('button', { name: 'Smart Upload (7)' }));

    expect(screen.queryByRole('button', { name: /Approve All & Ingest/i })).not.toBeInTheDocument();
    unmount();

    // Test with underscored role COLLEGE_ADMIN
    useAdminAuth.mockReturnValue({
      user: { role: 'COLLEGE_ADMIN', full_name: 'College Admin' },
    });

    render(<ApprovalCenterView />);
    fireEvent.click(await screen.findByRole('button', { name: 'Smart Upload (7)' }));

    expect(screen.queryByRole('button', { name: /Approve All & Ingest/i })).not.toBeInTheDocument();
  });

  it('does not include already APPROVED, REJECTED, or non-pending records in the count or approval calls', async () => {
    const mixedRecords = [
      ...createMockPendingRecords(7),
      { id: 'smart-approved-1', filename: 'approved-1.pdf', status: 'APPROVED' },
      { id: 'smart-rejected-1', filename: 'rejected-1.pdf', status: 'REJECTED' },
      { id: 'smart-failed-1', filename: 'failed-1.pdf', status: 'FAILED' },
    ];
    adminApi.getStagedUploads.mockResolvedValue(mixedRecords);

    render(<ApprovalCenterView />);
    fireEvent.click(await screen.findByRole('button', { name: 'Smart Upload (7)' }));

    // Count is strictly 7, not 10
    const bulkButton = screen.getByRole('button', { name: 'Approve All & Ingest (7)' });
    expect(bulkButton).toBeInTheDocument();

    fireEvent.click(bulkButton);

    await waitFor(() => {
      expect(adminApi.approveStagedUpload).toHaveBeenCalledTimes(7);
    });

    // None of the non-pending records were approved
    expect(adminApi.approveStagedUpload).not.toHaveBeenCalledWith('smart-approved-1');
    expect(adminApi.approveStagedUpload).not.toHaveBeenCalledWith('smart-rejected-1');
    expect(adminApi.approveStagedUpload).not.toHaveBeenCalledWith('smart-failed-1');
  });

  it('handles partial failures gracefully without pretending all succeeded, reporting successes and failures', async () => {
    const records = createMockPendingRecords(7);
    adminApi.getStagedUploads.mockResolvedValue(records);

    // Fail 2 out of 7 approvals
    adminApi.approveStagedUpload.mockImplementation((id) => {
      if (id === 'smart-2' || id === 'smart-6') {
        return Promise.reject(new Error(`Failed to ingest ${id}`));
      }
      return Promise.resolve({});
    });

    render(<ApprovalCenterView />);
    fireEvent.click(await screen.findByRole('button', { name: 'Smart Upload (7)' }));

    const bulkButton = screen.getByRole('button', { name: 'Approve All & Ingest (7)' });
    fireEvent.click(bulkButton);

    await waitFor(() => {
      expect(adminApi.approveStagedUpload).toHaveBeenCalledTimes(7);
    });

    // Refreshes the list
    expect(adminApi.getStagedUploads).toHaveBeenCalledTimes(2);

    // Shows partial feedback with count of succeeded and failed
    expect(await screen.findByText(/5 documents approved and ingested successfully\. 2 failed\./i)).toBeInTheDocument();
    expect(await screen.findByText(/2 documents failed to approve\./i)).toBeInTheDocument();
  });

  it('maintains individual Reject and Approve & Ingest buttons for each document', async () => {
    const records = createMockPendingRecords(2);
    adminApi.getStagedUploads.mockResolvedValue(records);

    render(<ApprovalCenterView />);
    fireEvent.click(await screen.findByRole('button', { name: 'Smart Upload (2)' }));

    const individualApproveButtons = screen.getAllByRole('button', { name: 'Approve & Ingest' });
    const individualRejectButtons = screen.getAllByRole('button', { name: 'Reject' });

    expect(individualApproveButtons).toHaveLength(2);
    expect(individualRejectButtons).toHaveLength(2);

    // Click individual Approve for doc-1
    fireEvent.click(individualApproveButtons[0]);
    await waitFor(() => {
      expect(adminApi.approveStagedUpload).toHaveBeenCalledWith('smart-1');
    });

    // Wait for async update to complete and re-query buttons
    const updatedRejectButtons = await screen.findAllByRole('button', { name: 'Reject' });
    fireEvent.click(updatedRejectButtons[1]);
    await waitFor(() => {
      expect(adminApi.rejectStagedUpload).toHaveBeenCalledWith('smart-2');
    });
  });

  it('preserves the College Applications tab and displays its filters', async () => {
    render(<ApprovalCenterView />);

    expect(screen.getByRole('button', { name: 'College Applications' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'All Applications' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Pending Approval' })).toBeInTheDocument();
  });
});
