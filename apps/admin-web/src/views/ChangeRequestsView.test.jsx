import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import ChangeRequestsView from './ChangeRequestsView';
import { adminApi } from '../services/adminApi';
import { useAdminAuth } from '../context/AdminAuthContext';

vi.mock('../services/adminApi', () => ({
  adminApi: {
    listChangeRequests: vi.fn(),
    approveChangeRequest: vi.fn(),
    approveAllChangeRequests: vi.fn(),
    rejectChangeRequest: vi.fn(),
  },
}));

vi.mock('../context/AdminAuthContext', () => ({
  useAdminAuth: vi.fn(),
}));

const pending = { id: 'cr-pending-42', status: 'PENDING', action: 'UPDATE', entity_type: 'FEES' };

beforeEach(() => {
  vi.clearAllMocks();
  useAdminAuth.mockReturnValue({ user: { role: 'SUPER_ADMIN' } });
  adminApi.listChangeRequests.mockResolvedValue([pending]);
  adminApi.approveChangeRequest.mockResolvedValue({ ...pending, status: 'APPLIED' });
  adminApi.rejectChangeRequest.mockResolvedValue({ ...pending, status: 'REJECTED' });
});

describe('ChangeRequestsView review controls', () => {
  it('renders an enabled bulk action for 34 pending requests', async () => {
    const requests = Array.from({ length: 34 }, (_, index) => ({
      id: `cr-pending-${index}`,
      status: 'PENDING',
      action: 'UPDATE',
      entity_type: 'FEES',
    }));
    adminApi.listChangeRequests.mockResolvedValue(requests);

    render(<ChangeRequestsView />);

    const bulk = await screen.findByRole('button', { name: 'Approve All & Apply (34)' });
    expect(bulk).toBeEnabled();
  });

  it('counts only pending requests when statuses are mixed', async () => {
    const requests = [
      ...Array.from({ length: 3 }, (_, index) => ({ ...pending, id: `pending-${index}` })),
      ...Array.from({ length: 2 }, (_, index) => ({ ...pending, id: `approved-${index}`, status: 'APPROVED' })),
      ...Array.from({ length: 4 }, (_, index) => ({ ...pending, id: `failed-${index}`, status: 'FAILED' })),
      { ...pending, id: 'rejected-1', status: 'REJECTED' },
    ];
    adminApi.listChangeRequests.mockResolvedValue(requests);

    render(<ChangeRequestsView />);

    expect(await screen.findByRole('button', { name: 'Approve All & Apply (3)' })).toBeEnabled();
  });

  it('shows the pending count, confirms, calls bulk approval, updates results, and awaits refresh', async () => {
    const failed = { id: 'cr-failed', status: 'PENDING', action: 'UPDATE', entity_type: 'FEES' };
    adminApi.listChangeRequests
      .mockResolvedValueOnce([pending, failed])
      .mockResolvedValueOnce([
        { ...pending, status: 'APPLIED' },
        { ...failed, status: 'FAILED', review_notes: 'Target is stale' },
      ]);
    adminApi.approveAllChangeRequests.mockResolvedValue({
      total_pending: 2, processed: 1, failed: 1,
      results: [
        { request_id: pending.id, status: 'APPLIED' },
        { request_id: failed.id, status: 'FAILED', message: 'Target is stale' },
      ],
    });
    render(<ChangeRequestsView />);
    const bulk = await screen.findByRole('button', { name: /Approve All & Apply \(2\)/i });
    fireEvent.click(bulk);
    expect(screen.getByRole('dialog')).toHaveTextContent('Approve and apply all 2 pending change requests?');
    fireEvent.click(screen.getByRole('dialog').querySelector('button.btn-primary'));
    await waitFor(() => {
      expect(adminApi.approveAllChangeRequests).toHaveBeenCalledWith(null);
      expect(adminApi.listChangeRequests).toHaveBeenCalledTimes(2);
      expect(screen.getByText(/Approved & Applied: 1.*Failed: 1/)).toBeInTheDocument();
    });
  });

  it('disables the bulk action when there are no pending requests', async () => {
    adminApi.listChangeRequests.mockResolvedValue([{ ...pending, status: 'FAILED' }]);
    render(<ChangeRequestsView />);
    const bulk = await screen.findByRole('button', { name: 'Approve All & Apply' });
    expect(bulk).toBeDisabled();
  });

  it('surfaces bulk API errors and prevents duplicate calls', async () => {
    let rejectBulk;
    adminApi.approveAllChangeRequests.mockReturnValue(new Promise((_, reject) => { rejectBulk = reject; }));
    render(<ChangeRequestsView />);
    fireEvent.click(await screen.findByRole('button', { name: /Approve All & Apply \(1\)/i }));
    fireEvent.click(screen.getByRole('dialog').querySelector('button.btn-primary'));
    const loadingButton = screen.getByRole('button', { name: /Approving All/i });
    expect(loadingButton).toBeDisabled();
    rejectBulk(new Error('Bulk approval unavailable'));
    await waitFor(() => expect(screen.getByText('Bulk approval unavailable')).toBeInTheDocument());
    expect(adminApi.approveAllChangeRequests).toHaveBeenCalledTimes(1);
  });

  it('submits the exact approval API with the request id and refreshes processed state', async () => {
    adminApi.listChangeRequests
      .mockResolvedValueOnce([pending])
      .mockResolvedValueOnce([{ ...pending, status: 'APPLIED' }]);
    adminApi.approveChangeRequest.mockResolvedValue({ ...pending, status: 'APPLIED' });
    render(<ChangeRequestsView />);

    const approve = await screen.findByRole('button', { name: /^Approve & Apply$/i });
    expect(approve).toBeEnabled();

    fireEvent.click(approve);

    await waitFor(() => {
      expect(adminApi.approveChangeRequest).toHaveBeenCalledTimes(1);
      expect(adminApi.approveChangeRequest).toHaveBeenCalledWith('cr-pending-42', null);
      expect(adminApi.listChangeRequests).toHaveBeenCalledTimes(2);
      expect(screen.queryByRole('button', { name: /^Approve & Apply$/i })).not.toBeInTheDocument();
    });
    expect(screen.getByText('This request has already been processed.')).toBeInTheDocument();
  });

  it('surfaces approval API errors and does not refresh as if approval succeeded', async () => {
    adminApi.approveChangeRequest.mockRejectedValueOnce(new Error('Approval failed: target is stale'));
    render(<ChangeRequestsView />);

    fireEvent.click(await screen.findByRole('button', { name: /^Approve & Apply$/i }));

    await waitFor(() => {
      expect(screen.getByText('Approval failed: target is stale')).toBeInTheDocument();
    });
    expect(adminApi.approveChangeRequest).toHaveBeenCalledWith('cr-pending-42', null);
    expect(adminApi.listChangeRequests).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: /Approve & Apply/i })).toBeEnabled();
  });

  it.each(['APPROVED', 'REJECTED', 'FAILED'])('%s requests have no approve action', async (status) => {
    adminApi.listChangeRequests.mockResolvedValue([{ ...pending, status }]);
    render(<ChangeRequestsView />);

    await waitFor(() => expect(adminApi.listChangeRequests).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: /^Approve & Apply$/i })).not.toBeInTheDocument();
    expect(screen.getByText('This request has already been processed.')).toBeInTheDocument();
  });
});
