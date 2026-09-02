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

export interface LogSource {
  id: string;
  name: string;
  category: string;
  adapter: string;
  description: string;
  config: Record<string, unknown>;
  enabled: boolean;
  connection_status: string;
  last_received_at: string | null;
  events_processed: number;
  created_at: string;
}

export interface AdapterInfo {
  kind: string;
  mvp_supported: boolean;
  requires: string;
  status: string;
  detail: string;
}

export type JobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface ProcessingJob {
  id: string;
  source_id: string | null;
  source_name: string;
  filename: string;
  declared_format: string | null;
  detected_format: string | null;
  status: JobStatus;
  started_at: string | null;
  finished_at: string | null;
  total_records: number;
  processed_records: number;
  invalid_records: number;
  duplicate_records: number;
  quarantined_records: number;
  processing_rate: number;
  error: string;
  stats: Record<string, unknown>;
  created_at: string;
}

export interface RawLogRecord {
  id: string;
  line_number: number;
  content: string;
  content_hash: string;
  status: string;
  security_verdict: string;
  processing_errors: unknown[];
}

export interface DetectionResult {
  format: string;
  confidence: number;
  candidates: { format: string; parser: string; confidence: number }[];
  signals: string[];
}

export interface SampleFile {
  path: string;
  category: string;
  bytes: number;
}

export interface PipelineStageResult {
  stage: string;
  status: "ok" | "warn" | "error" | "skipped";
  summary: string;
  input: unknown;
  output: unknown;
  fields: Record<string, unknown>;
  transformations: { type: string; [k: string]: unknown }[];
  warnings: string[];
  errors: string[];
  meta: Record<string, unknown>;
  duration_ms: number;
}

export interface PipelineTestResult {
  raw: string;
  stage_order: string[];
  stages: PipelineStageResult[];
  security_verdict: string;
  detected_format: string;
  format_confidence: number;
  parser: { name: string; version: string };
  match_spans: { field: string; start: number; end: number; text: string }[];
  pii_transformations: { field: string; kind: string; pseudonym: string }[];
  disposition: string;
  event: Record<string, unknown> | null;
  errors: string[];
  warnings: string[];
}
