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
  raw_log_id?: string | null;
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

export interface PipelineNode {
  key: string;
  label: string;
  count: number;
  status: "idle" | "ok" | "warn" | "critical" | "running";
  detail: Record<string, unknown>;
}
export const analyticsPipeline = () =>
  api
    .get<{ nodes: PipelineNode[]; generated_at: string }>("/analytics/pipeline")
    .then((r) => r.data);

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

// --- templates (Module 23) ---
export interface TemplateSummary {
  id: string;
  template_key: string;
  pattern: string;
  token_count: number;
  variable_count: number;
  variable_types: (string | null)[];
  occurrences: number;
  source_distribution: Record<string, number>;
  example: string;
  first_seen: string;
  last_seen: string;
  created_at: string;
  updated_at: string;
}
export interface TemplateDetail extends TemplateSummary {
  literal_tokens: (string | null)[];
  separators: string[];
  trailing: string;
  token_signature: string;
  examples: { raw_log_id: string; source: string; ts: string | null; raw: string }[];
}
export interface TemplateList {
  total: number;
  items: TemplateSummary[];
  covered_events: number;
  unique_sources: number;
  avg_variables: number;
}
export interface MineResult {
  records_scanned: number;
  records_matched: number;
  templates_total: number;
  templates_created: number;
  templates_updated: number;
  duration_seconds: number;
  scan_limit_hit: boolean;
  template_keys: string[];
}

export const listTemplates = (params?: {
  source?: string;
  min_frequency?: number;
  time_from?: string;
  time_to?: string;
  limit?: number;
  offset?: number;
}) => api.get<TemplateList>("/templates", { params }).then((r) => r.data);

export const getTemplate = (key: string) =>
  api.get<TemplateDetail>(`/templates/${key}`).then((r) => r.data);

export const getTemplateExamples = (key: string, limit = 20) =>
  api
    .get<{ raw_log_id: string; source: string; ts: string | null; raw: string; variables: string[] }[]>(
      `/templates/${key}/examples`,
      { params: { limit } },
    )
    .then((r) => r.data);

export const mineTemplates = (body: {
  source?: string;
  time_from?: string;
  time_to?: string;
  limit?: number;
}) => api.post<MineResult>("/templates/mine", body).then((r) => r.data);

// --- compression (Module 24) ---
export interface BenchmarkResult {
  scope: string;
  record_count: number;
  reconstructable_count: number;
  template_count: number;
  original_bytes: number;
  compressed_bytes: number;
  metadata_bytes: number;
  total_compressed_bytes: number;
  savings_bytes: number;
  reduction_pct: number;
  processing_seconds: number;
  events_per_sec: number;
  mismatches: { raw_log_id: string; original_preview: string; reconstructed_preview: string }[];
}
export interface CompressionRecordRow {
  id: string;
  ts: string;
  job_id: string | null;
  scope: string;
  original_bytes: number;
  compressed_bytes: number;
  metadata_bytes: number;
  total_compressed_bytes: number;
  reduction_pct: number;
  record_count: number;
  reconstructable_count: number;
  template_count: number;
  processing_seconds: number;
  events_per_sec: number;
  method: string;
}
export interface DecompressResult {
  raw_log_id: string;
  template_key: string | null;
  original: string;
  reconstructed: string | null;
  exact_match: boolean;
  variables: string[];
}

export const runBenchmark = (body: { job_id?: string; source?: string; limit?: number }) =>
  api.post<BenchmarkResult>("/compression/benchmark", body).then((r) => r.data);
export const compressScope = (body: { job_id?: string; source?: string; limit?: number }) =>
  api
    .post<{ records_in_scope: number; records_compressed: number; templates_used: number }>(
      "/compression/compress",
      body,
    )
    .then((r) => r.data);
export const decompressRecord = (raw_log_id: string) =>
  api.post<DecompressResult>("/compression/decompress", { raw_log_id }).then((r) => r.data);
export const listCompressionRecords = () =>
  api.get<CompressionRecordRow[]>("/compression/records").then((r) => r.data);

// --- AI explainer (Module 22) ---
export interface AIStatus {
  provider: string;
  offline: boolean;
  model: string | null;
  available: boolean;
  fallback_active: boolean;
  note: string;
}
export interface AIExplanation {
  provider: string;
  offline: boolean;
  model: string | null;
  summary: string;
  important_fields: { field: string; value: string; note: string }[];
  why_it_matters: string;
  detection_context: string;
  related_activity: string;
  suggested_steps: string[];
  disclaimer: string;
  fallback_from: string | null;
}
export interface AIExplainResponse {
  kind: "event" | "alert" | "raw";
  generated_at: string;
  provider: string;
  offline: boolean;
  model: string | null;
  evidence: Record<string, unknown>;
  explanation: AIExplanation;
}
export const aiStatus = () => api.get<AIStatus>("/ai/status").then((r) => r.data);
export const aiExplain = (body:
  | { kind: "event"; event_id: string }
  | { kind: "alert"; alert_id: string }
  | { kind: "raw"; text: string }
) => api.post<AIExplainResponse>("/ai/explain", body).then((r) => r.data);

// --- response simulator (Module 28) ---
export interface SimAction {
  action: string;
  target: string | null;
  port: number | null;
  protocol: string | null;
  detail: string;
  mode: string; // always "SIMULATION_ONLY"
}
export interface Recommendation {
  category: string;
  available: boolean;
  label: string;
  rationale: string;
  actions: SimAction[];
  evidence: Record<string, unknown>;
}
export interface RecommendResponse {
  alert: Record<string, any>;
  recommendation: Recommendation;
  evidence: Record<string, any>;
}
export interface SimulateResponse {
  simulation: boolean;
  disclaimer: string;
  audit_id: string;
  alert: Record<string, any>;
  recommendation: Recommendation;
  actions: SimAction[];
  result: {
    simulation: boolean;
    disclaimer: string;
    no_real_change: boolean;
    primary: {
      kind: string;
      target: string | null;
      before: any[];
      after: any[];
      expected_result: string;
      state_change: { before: string; after: string };
      disclaimer: string;
    } | null;
    all: any[];
  };
  evidence: Record<string, unknown>;
}
export interface SimulationRecord {
  id: string;
  ts: string;
  actor_email: string | null;
  alert_id: string;
  alert_title: string;
  alert_rule_key: string | null;
  alert_severity: string;
  alert_risk_score: number;
  recommendation: Recommendation;
  actions: SimAction[];
  result: SimulateResponse["result"];
  simulation_only: boolean;
}

export const getRecommendation = (alertId: string) =>
  api.get<RecommendResponse>(`/response/recommend/${alertId}`).then((r) => r.data);
export const runResponseSimulation = (alertId: string) =>
  api.post<SimulateResponse>("/response/simulate", { alert_id: alertId }).then((r) => r.data);
export const listSimulations = (params?: { alert_id?: string }) =>
  api.get<SimulationRecord[]>("/response/simulations", { params }).then((r) => r.data);
