export interface Secret {
  id: string;
  name: string;
  description: string;
  type: string;
  version: number;
  created_at: string;
  updated_at: string;
  expires_at?: string;
  is_rotated: boolean;
  labels: Record<string, string>;
}

export interface SecretWithValue extends Secret {
  value: string;
}

export interface AuditLog {
  id: string;
  secret_id: string;
  action: string;
  user: string;
  ip_address: string;
  user_agent: string;
  success: boolean;
  message: string;
  created_at: string;
}

export interface CreateSecretRequest {
  name: string;
  description: string;
  type: string;
  value: string;
  labels: Record<string, string>;
  expires_at?: string;
}

export interface UpdateSecretRequest {
  description?: string;
  value?: string;
  labels?: Record<string, string>;
  expires_at?: string;
}
