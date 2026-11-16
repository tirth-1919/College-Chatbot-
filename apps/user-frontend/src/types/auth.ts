export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "STUDENT" | "COLLEGE_ADMIN" | "SUPER_ADMIN";
  is_verified: boolean;
  is_active: boolean;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

