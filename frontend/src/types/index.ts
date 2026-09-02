export type Role = "ADMIN" | "ANALYST" | "VIEWER";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export type Severity = "info" | "low" | "medium" | "high" | "critical";
