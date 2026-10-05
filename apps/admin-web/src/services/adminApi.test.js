import { beforeEach, describe, expect, it, vi } from 'vitest';
import { adminApi } from './adminApi';

describe('admin change-request API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    adminApi._token = null;
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  it('posts bulk approval to the backend change-requests endpoint', async () => {
    const response = { total_pending: 0, processed: 0, failed: 0, results: [] };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => response });
    vi.stubGlobal('fetch', fetchMock);

    await expect(adminApi.approveAllChangeRequests(null)).resolves.toEqual(response);

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/admin/change-requests/approve-all', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ notes: null }),
    }));
  });

  it('requests the supported maximum page size for the admin college list', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ colleges: [] }) });
    vi.stubGlobal('fetch', fetchMock);

    await expect(adminApi.listColleges()).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/admin/colleges/?per_page=100', expect.anything());
  });
});
