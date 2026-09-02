import { api } from "./api";
import type {
  AdapterInfo,
  DetectionResult,
  LogSource,
  PipelineTestResult,
  ProcessingJob,
  RawLogRecord,
  SampleFile,
  User,
} from "@/types";

// --- users ---
export const listUsers = () => api.get<User[]>("/users").then((r) => r.data);
export const createUser = (body: {
  email: string;
  password: string;
  role: string;
  full_name?: string;
}) => api.post<User>("/users", body).then((r) => r.data);

export const listAuditLogs = (params?: { action?: string; limit?: number }) =>
  api.get("/users/audit-logs", { params }).then((r) => r.data);

// --- sources ---
export const listSources = () => api.get<LogSource[]>("/sources").then((r) => r.data);
export const listAdapters = () =>
  api.get<{ adapters: AdapterInfo[] }>("/sources/adapters").then((r) => r.data.adapters);
export const createSource = (body: Partial<LogSource>) =>
  api.post<LogSource>("/sources", body).then((r) => r.data);
export const updateSource = (id: string, body: Partial<LogSource>) =>
  api.put<LogSource>(`/sources/${id}`, body).then((r) => r.data);
export const deleteSource = (id: string) => api.delete(`/sources/${id}`);

// --- ingestion ---
export const listJobs = (params?: { limit?: number; offset?: number }) =>
  api
    .get<{ total: number; items: ProcessingJob[] }>("/ingestion/jobs", { params })
    .then((r) => r.data);
export const getJob = (id: string) =>
  api.get<ProcessingJob>(`/ingestion/jobs/${id}`).then((r) => r.data);
export const getJobRecords = (id: string, params?: { status?: string; limit?: number }) =>
  api.get<RawLogRecord[]>(`/ingestion/jobs/${id}/records`, { params }).then((r) => r.data);

export const uploadLog = (file: File, sourceName: string, declaredFormat?: string) => {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("source_name", sourceName);
  if (declaredFormat) fd.append("declared_format", declaredFormat);
  return api
    .post<ProcessingJob>("/ingestion/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const listSamples = () =>
  api.get<{ root: string; samples: SampleFile[] }>("/ingestion/samples").then((r) => r.data);
export const importSample = (path: string, sourceName?: string) =>
  api
    .post<ProcessingJob>("/ingestion/import-sample", { path, source_name: sourceName })
    .then((r) => r.data);
export const simulateStream = (body: { source_id?: string; count?: number }) =>
  api.post<ProcessingJob>("/ingestion/simulate", body).then((r) => r.data);

// --- privacy ---
export interface PiiSettings {
  mode: "OFF" | "MASK" | "DETERMINISTIC_HASH";
  protect_ip: boolean;
  protect_email: boolean;
  protect_username: boolean;
  protect_host: boolean;
  scope: string;
  token_length: number;
  store_reverse_map: boolean;
}
export const getPrivacySettings = () =>
  api.get<PiiSettings>("/privacy/settings").then((r) => r.data);
export const updatePrivacySettings = (body: Partial<PiiSettings>) =>
  api.put<PiiSettings>("/privacy/settings", body).then((r) => r.data);
export const previewPseudonym = (value: string, kind: string) =>
  api
    .post<{ input: string; kind: string; mode: string; output: string; note: string }>(
      "/privacy/preview",
      { value, kind },
    )
    .then((r) => r.data);

// --- security ---
export const listSecurityEvents = (params?: { verdict?: string; job_id?: string; limit?: number }) =>
  api.get<{ total: number; items: SecurityEventRow[] }>("/security/events", { params }).then((r) => r.data);
export interface SecurityEventRow {
  id: string;
  ts: string;
  detection_type: string;
  source: string;
  severity: string;
  verdict: string;
  raw_reference: string | null;
  job_id: string | null;
  reason: string;
  indicators: { type: string; severity: string; category?: string; detail: string }[];
}

// --- pipeline ---
export const detectFormat = (sample: string, hint?: string) =>
  api.post<DetectionResult>("/pipeline/detect", { sample, hint }).then((r) => r.data);
export const pipelineTest = (body: {
  raw: string;
  declared_format?: string;
  pii_mode?: string;
}) => api.post<PipelineTestResult>("/pipeline/test", body).then((r) => r.data);

// --- logs / explorer ---
export interface UniversalEvent {
  id: string;
  schema_version: string;
  timestamp: string | null;
  ingested_at: string | null;
  source: string;
  host: string | null;
  event_type: string | null;
  severity: string | null;
  username: string | null;
  email: string | null;
  source_ip: string | null;
  destination_ip: string | null;
  source_port: number | null;
  destination_port: number | null;
  protocol: string | null;
  action: string | null;
  status: string | null;
  process: string | null;
  service: string | null;
  url: string | null;
  http_method: string | null;
  response_code: number | null;
  message: string;
  extra: Record<string, unknown>;
  field_confidence: Record<string, number>;
  raw_log: string;
  parser: string;
  parser_version: string;
  pii_protected: boolean;
  pii_mode: string;
  processing_status: string;
  confidence: number;
  template_id: string | null;
  job_id?: string | null;
}

export type LogFilters = Partial<
  Record<
    | "text" | "source" | "host" | "source_ip" | "destination_ip" | "username"
    | "event_type" | "severity" | "action" | "status" | "parser" | "processing_status"
    | "time_from" | "time_to",
    string
  >
> & { limit?: number; offset?: number };

export const searchLogs = (filters: LogFilters) =>
  api
    .get<{ total: number; items: UniversalEvent[]; limit: number; offset: number; note: string | null }>(
      "/logs",
      { params: filters },
    )
    .then((r) => r.data);

export const logStats = () =>
  api
    .get<{ total_events: number; facets: Record<string, { value: string; count: number }[]>; timeseries: { bucket: string; count: number }[] }>(
      "/logs/stats",
    )
    .then((r) => r.data);

export interface LogDetail {
  event: UniversalEvent;
  raw_log: { id: string; line_number: number; content: string; status: string; security_verdict: string; processing_errors: unknown[] } | null;
  job: { id: string; filename: string; detected_format: string; source_name: string } | null;
  pipeline: {
    stage: string;
    status: string;
    summary: string;
    fields: Record<string, unknown>;
    transformations: Record<string, unknown>[];
    warnings: string[];
    errors: string[];
  }[];
  pii_transformations: { field: string; kind: string; pseudonym: string }[];
  related_events: UniversalEvent[];
  security_events: { id: string; detection_type: string; verdict: string; severity: string; reason: string }[];
}
export const getLogDetail = (id: string) =>
  api.get<LogDetail>(`/logs/${id}`).then((r) => r.data);

// --- alerts / detection ---
export interface RiskFactor {
  factor: string;
  points: number;
  detail: string;
}
export interface Alert {
  id: string;
  ts: string;
  title: string;
  severity: string;
  risk_score: number;
  source: string;
  rule_key: string | null;
  description: string;
  reason: string;
  risk_breakdown: { score: number; band: string; summary: string; factors: RiskFactor[] };
  entity: Record<string, unknown>;
  related_event_ids: string[];
  affected_hosts: string[];
  recommended_response: {
    action: string;
    label: string;
    target: Record<string, string>;
    auto_execute: boolean;
    note: string;
    urgency: string;
  };
  status: string;
  resolution_note: string;
  updated_at: string;
}
export interface TimelineEntry {
  ts: string | null;
  event_id: string;
  source: string;
  host: string | null;
  event_type: string | null;
  action: string | null;
  status: string | null;
  severity: string | null;
  summary: string;
}

export const listAlerts = (params?: { status?: string; severity?: string }) =>
  api.get<{ total: number; items: Alert[] }>("/alerts", { params }).then((r) => r.data);
export const getAlert = (id: string) =>
  api
    .get<{ alert: Alert; timeline: TimelineEntry[]; related_events: UniversalEvent[]; correlation: Record<string, unknown> }>(
      `/alerts/${id}`,
    )
    .then((r) => r.data);
export const updateAlert = (id: string, body: { status?: string; resolution_note?: string }) =>
  api.put<Alert>(`/alerts/${id}`, body).then((r) => r.data);
export const runDetection = (since_hours = 24) =>
  api.post<{ alerts_created_or_updated: number }>("/detection/run", { since_hours }).then((r) => r.data);

export interface SecurityRule {
  rule_key: string;
  name: string;
  description: string;
  severity: string;
  threshold: number;
  window_seconds: number;
  enabled: boolean;
  params: Record<string, unknown>;
}
export const listRules = () => api.get<SecurityRule[]>("/detection/rules").then((r) => r.data);
export const updateRule = (key: string, body: Partial<SecurityRule>) =>
  api.put<SecurityRule>(`/detection/rules/${key}`, body).then((r) => r.data);

// --- analytics / dashboard ---
export interface Series {
  label: string;
  value: number;
}
export interface AnalyticsOverview {
  cards: {
    total_logs: number;
    processed: number;
    invalid: number;
    duplicates: number;
    quarantined: number;
    normalized_events: number;
    alerts: number;
    avg_processing_rate: number;
    peak_processing_rate: number;
  };
  charts: {
    logs_by_source: Series[];
    logs_by_format: Series[];
    events_by_severity: Series[];
    events_by_type: Series[];
    events_over_time: { bucket: string; count: number }[];
    processing_outcomes: Series[];
    pii_transformations: Series[];
    alerts_by_severity: Series[];
    risk_distribution: Series[];
  };
  processing_success_rate: number;
  shield_events: number;
  source_status: {
    name: string;
    category: string;
    adapter: string;
    status: string;
    events_processed: number;
    last_received: string | null;
    configured: boolean;
  }[];
  generated_at: string;
}
export const analyticsOverview = () =>
  api.get<AnalyticsOverview>("/analytics/overview").then((r) => r.data);

// --- parsers ---
export interface ParserInfo {
  name: string;
  version: string;
  format: string;
  description: string;
  kind: string;
  schema_version: string;
  specificity: number;
  pattern_count?: number;
  field_mappings?: Record<string, string>;
  limits?: { fuel: number; timeout_ms: number; max_memory_bytes: number };
}
export interface ParserTestReport {
  total: number;
  passed: number;
  results: { index: number; input: string; ok: boolean; mismatches: Record<string, unknown>; fields: Record<string, unknown> }[];
}
export const listParsers = () =>
  api.get<{ parsers: ParserInfo[] }>("/parsers").then((r) => r.data.parsers);
export const getParser = (name: string) =>
  api
    .get<ParserInfo & { definition?: Record<string, unknown>; tests?: ParserTestReport }>(
      `/parsers/${name}`,
    )
    .then((r) => r.data);
export const parserVersions = (name: string) =>
  api
    .get<{ name: string; latest_version: string; versions: { version: string; is_active: boolean; created_at: string; tests_passed: number | null }[] }>(
      `/parsers/${name}/versions`,
    )
    .then((r) => r.data);
export const testParser = (name: string, sample: string) =>
  api
    .post<{ parser: string; can_parse: number; fields: Record<string, unknown>; confidence: number; event_type: string | null; match_spans: { field: string; start: number; end: number; text: string }[]; errors: string[]; partial: boolean; tests?: ParserTestReport }>(
      `/parsers/${name}/test`,
      { sample },
    )
    .then((r) => r.data);
export const validateParserPack = (yaml_text: string) =>
  api
    .post<{ valid: boolean; problems: string[]; tests: ParserTestReport; metadata: ParserInfo }>(
      "/parsers/validate",
      { yaml_text },
    )
    .then((r) => r.data);
export const createParserPack = (yaml_text: string, author?: string) =>
  api
    .post<{ name: string; version: string; tests: ParserTestReport; registered: boolean }>(
      "/parsers",
      { yaml_text, author },
    )
    .then((r) => r.data);

// --- wasm ---
export interface WasmStatus {
  available: boolean;
  runtime: string | null;
  defaults: Record<string, number>;
  isolation: string[];
}
export const wasmStatus = () => api.get<WasmStatus>("/wasm/status").then((r) => r.data);
export const wasmRun = (wat: string, input: string) =>
  api
    .post<{ output: unknown; fuel_consumed: number; duration_ms: number; memory_bytes: number }>(
      "/wasm/run",
      { wat, input },
    )
    .then((r) => r.data);
