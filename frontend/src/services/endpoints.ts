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
