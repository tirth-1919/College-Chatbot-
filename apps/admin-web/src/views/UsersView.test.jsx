import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import UsersView from './UsersView';
import { adminApi } from '../services/adminApi';

vi.mock('../services/adminApi', () => ({
  adminApi: { getUsers: vi.fn(), changeUserRole: vi.fn(), toggleUserStatus: vi.fn() },
}));

describe('UsersView', () => {
  beforeEach(() => vi.clearAllMocks());
  it('renders loading and then users from the existing array API response', async () => {
    adminApi.getUsers.mockResolvedValue([{ id: '1', full_name: 'Ada', email: 'ada@example.com', role: 'STUDENT', is_active: true }]);
    render(<UsersView />);
    expect(screen.getByText('Loading users...')).toBeInTheDocument();
    expect(await screen.findByText('Ada')).toBeInTheDocument();
  });
  it('handles object response, empty response, and API failure with retry', async () => {
    adminApi.getUsers.mockResolvedValueOnce({ items: [] });
    render(<UsersView />);
    expect(await screen.findByText('No users found.')).toBeInTheDocument();
    adminApi.getUsers.mockRejectedValueOnce(new Error('Forbidden'));
    fireEvent.change(screen.getByPlaceholderText('Search by name or email...'), { target: { value: 'x' } });
    expect(await screen.findByText('Unable to load users.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });
});
