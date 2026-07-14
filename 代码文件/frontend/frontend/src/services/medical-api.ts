import axios, { AxiosError } from "axios";
import {
  mockCreateCase,
  mockCurrentUser,
  mockDownloadReport,
  mockGetCase,
  mockListCases,
  mockLogin,
  mockRegister,
  mockUpdateCase,
} from "./mock-medical-api";
import type {
  AiResult,
  ApiErrorPayload,
  AttachmentView,
  AuthSession,
  AuthUser,
  CaseCreateRequest,
  CaseRecordView,
  DepartmentCode,
  GenderCode,
  GenerationNeed,
  MedicalFormValues,
  PageResult,
  RegisterRequest,
} from "../types/medical-record";

const TOKEN_KEY = "medical-auth-token";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8080";
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === "true";
const JOB_TIMEOUT_MS = 60_000;

type BackendUser = {
  id: string;
  username: string;
  displayName?: string;
  role: string;
};

type BackendSession = {
  token: string;
  tokenType: "Bearer";
  expiresIn: number;
  user: BackendUser;
};

type BackendJobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled";

type BackendCreateCaseResponse = {
  caseId: string;
  jobId: string;
  status: BackendJobStatus;
  createdAt: string;
};

type BackendJob = {
  jobId: string;
  caseId: string;
  status: BackendJobStatus;
  progress?: number;
  message?: string;
  errorCode?: string;
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
};

type BackendAttachment = {
  id: string;
  fileName: string;
  mimeType: string;
  size: number;
  url: string;
  parseStatus: string;
  extractedText?: string;
  failureReason?: string;
};

type BackendResult = {
  caseId: string;
  generatedAt: string;
  summary: {
    patientName: string;
    gender: GenderCode;
    age: number;
    department?: DepartmentCode;
    visitDate?: string;
    chiefComplaint: string;
  };
  structuredRecord: {
    generatedContent: string;
    presentIllness: string;
    pastHistory: string;
    allergyHistory?: string;
    vitalSigns?: string;
    physicalExam?: string;
    auxiliaryExam?: string;
  };
  analysis: {
    preliminaryDiagnosis?: string;
    treatmentTaken?: string;
    medicationUsage?: string;
    generationNeeds: GenerationNeed[];
    content?: string;
    symptoms: string[];
    medicalTerms: string[];
    diagnosisTop1: string;
    diagnosisCandidates: string[];
    diagnosisReason: string;
    treatmentAdvice: string;
    modelVersion: string;
    confidence: number;
    lowConfidence: boolean;
    lowConfidenceReason?: string | null;
    disclaimer: string;
  };
  attachments: BackendAttachment[];
};

type BackendCaseDetail = {
  caseId: string;
  input: CaseCreateRequest;
  status: BackendJobStatus;
  currentJobId: string;
  result: BackendResult | null;
  editedRecord?: string;
  attachments: BackendAttachment[];
  createdAt: string;
  updatedAt: string;
};

type BackendHistoryPage = {
  content: Array<{
    caseId: string;
    patientName: string;
    gender: GenderCode;
    age: number;
    department?: DepartmentCode;
    chiefComplaint: string;
    status: BackendJobStatus;
    createdAt: string;
    updatedAt: string;
  }>;
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
};

export class MedicalApiError extends Error {
  status?: number;
  fieldErrors: Record<string, string>;
  requestId?: string;

  constructor(message: string, options: { status?: number; fieldErrors?: Record<string, string>; requestId?: string } = {}) {
    super(message);
    this.name = "MedicalApiError";
    this.status = options.status;
    this.fieldErrors = options.fieldErrors ?? {};
    this.requestId = options.requestId;
  }
}

const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 12_000,
});

http.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

function toApiError(error: unknown): MedicalApiError {
  if (error instanceof MedicalApiError) return error;
  if (error instanceof AxiosError) {
    const payload = error.response?.data as ApiErrorPayload | undefined;
    const fieldErrors = payload?.fieldErrors
      ?? (payload?.data as { fieldErrors?: Record<string, string> } | undefined)?.fieldErrors;
    return new MedicalApiError(payload?.message ?? error.message ?? "网络连接失败，请稍后重试。", {
      status: error.response?.status,
      fieldErrors,
      requestId: payload?.requestId,
    });
  }
  return new MedicalApiError(error instanceof Error ? error.message : "请求失败，请稍后重试。");
}

async function request<T>(operation: Promise<{ data: T }>): Promise<T> {
  try {
    return (await operation).data;
  } catch (error) {
    throw toApiError(error);
  }
}

function mapUser(user: BackendUser): AuthUser {
  return {
    id: user.id,
    username: user.username,
    displayName: user.displayName || user.username,
    role: user.role,
  };
}

function mapSession(session: BackendSession): AuthSession {
  return {
    token: session.token,
    tokenType: session.tokenType,
    expiresAt: new Date(Date.now() + session.expiresIn * 1000).toISOString(),
    user: mapUser(session.user),
  };
}

function attachmentView(attachment: BackendAttachment): AttachmentView {
  const knownStatuses = new Set(["metadata_only", "not_processed", "pending", "parsed", "failed"]);
  return {
    id: attachment.id,
    fileName: attachment.fileName,
    mimeType: attachment.mimeType,
    url: attachment.url,
    processingStatus: knownStatuses.has(attachment.parseStatus)
      ? attachment.parseStatus as AttachmentView["processingStatus"]
      : "not_processed",
    extractedText: attachment.extractedText,
    failureReason: attachment.failureReason,
  };
}

function aiResult(result: BackendResult): AiResult {
  return {
    status: "completed",
    generatedAt: result.generatedAt,
    model: {
      name: "medical-record-ai",
      version: result.analysis.modelVersion || "unknown",
      confidence: result.analysis.confidence ?? 0,
      lowConfidence: result.analysis.lowConfidence ?? false,
    },
    summary: {
      ...result.summary,
      department: result.summary.department ?? "",
      visitDate: result.summary.visitDate ?? "",
    },
    structuredRecord: {
      presentIllness: result.structuredRecord.presentIllness,
      pastHistory: result.structuredRecord.pastHistory,
      allergyHistory: result.structuredRecord.allergyHistory ?? "",
      vitalSigns: result.structuredRecord.vitalSigns ?? "",
      physicalExam: result.structuredRecord.physicalExam ?? "",
      auxiliaryExam: result.structuredRecord.auxiliaryExam ?? "",
      generatedRecord: result.structuredRecord.generatedContent,
    },
    analysis: {
      preliminaryDiagnosis: result.analysis.preliminaryDiagnosis ?? "",
      treatmentTaken: result.analysis.treatmentTaken ?? "",
      medicationUsage: result.analysis.medicationUsage ?? "",
      generationNeeds: result.analysis.generationNeeds ?? [],
      symptoms: result.analysis.symptoms ?? [],
      medicalTerms: result.analysis.medicalTerms ?? [],
      diagnosisTop1: result.analysis.diagnosisTop1,
      diagnosisCandidates: result.analysis.diagnosisCandidates ?? [],
      diagnosisReason: result.analysis.diagnosisReason,
      treatmentAdvice: result.analysis.treatmentAdvice,
      content: result.analysis.content,
      lowConfidence: result.analysis.lowConfidence ?? false,
      lowConfidenceReason: result.analysis.lowConfidenceReason ?? null,
      disclaimer: result.analysis.disclaimer,
    },
    attachments: result.attachments.map(attachmentView),
    failureReason: null,
  };
}

function recordStatus(status: BackendJobStatus): CaseRecordView["status"] {
  if (status === "completed") return "COMPLETED";
  if (status === "failed" || status === "cancelled") return "ANALYSIS_FAILED";
  return "DRAFT";
}

function mapDetail(detail: BackendCaseDetail, lastError: string | null = null): CaseRecordView {
  const result = detail.result ? aiResult(detail.result) : null;
  return {
    id: detail.caseId,
    status: recordStatus(detail.status),
    patientInput: detail.input,
    aiResult: result,
    generatedRecord: result?.structuredRecord.generatedRecord ?? null,
    editedRecord: detail.editedRecord ?? null,
    lastError,
    version: detail.editedRecord ? 2 : detail.result ? 1 : 0,
    createdAt: detail.createdAt,
    updatedAt: detail.updatedAt,
  };
}

function textValue(values: MedicalFormValues, key: string) {
  const value = values[key];
  return typeof value === "string" ? value.trim() : "";
}

function selectedNeeds(values: MedicalFormValues): GenerationNeed[] {
  const value = values.generationNeeds;
  return Array.isArray(value)
    ? value.filter((item): item is GenerationNeed => typeof item === "string")
    : [];
}

function selectedFiles(values: MedicalFormValues): File[] {
  const value = values.attachments;
  return Array.isArray(value)
    ? value.filter((item): item is File => typeof item !== "string")
    : [];
}

function delay(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function waitForJob(jobId: string): Promise<BackendJob> {
  const deadline = Date.now() + JOB_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const job = await request(http.get<BackendJob>(`/api/v1/jobs/${jobId}`));
    if (job.status === "completed") return job;
    if (job.status === "failed" || job.status === "cancelled") {
      throw new MedicalApiError(job.errorMessage || "病例分析失败，请稍后重试。");
    }
    await delay(750);
  }
  throw new MedicalApiError("病例分析等待超时，请稍后从历史记录查看结果。");
}

async function backendDetail(caseId: string): Promise<BackendCaseDetail> {
  return request(http.get<BackendCaseDetail>(`/api/v1/cases/${caseId}`));
}

export function isMockApi() {
  return USE_MOCK_API;
}

export function getStoredToken() {
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string) {
  window.sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  window.sessionStorage.removeItem(TOKEN_KEY);
}

export function isUnauthorized(error: unknown) {
  return error instanceof MedicalApiError && error.status === 401;
}

export async function login(username: string, password: string): Promise<AuthSession> {
  if (USE_MOCK_API) {
    const session = await mockLogin(username, password).catch((error) => { throw toApiError(error); });
    storeToken(session.token);
    return session;
  }
  const session = mapSession(await request(
    http.post<BackendSession>("/api/v1/auth/login", { username, password }),
  ));
  storeToken(session.token);
  return session;
}

export async function register(payload: RegisterRequest): Promise<AuthSession> {
  if (USE_MOCK_API) {
    const session = await mockRegister(payload).catch((error) => { throw toApiError(error); });
    storeToken(session.token);
    return session;
  }
  const session = mapSession(await request(
    http.post<BackendSession>("/api/v1/auth/register", payload),
  ));
  storeToken(session.token);
  return session;
}

export async function getCurrentUser(): Promise<AuthUser> {
  const token = getStoredToken();
  if (!token) throw new MedicalApiError("尚未登录", { status: 401 });
  if (USE_MOCK_API) {
    return mockCurrentUser(token).catch((error) => {
      throw new MedicalApiError(error instanceof Error ? error.message : "登录状态已失效", { status: 401 });
    });
  }
  return mapUser(await request(http.get<BackendUser>("/api/v1/auth/me")));
}

export async function logout() {
  try {
    if (!USE_MOCK_API) await request(http.post<void>("/api/v1/auth/logout"));
  } finally {
    clearStoredToken();
    if (USE_MOCK_API) window.localStorage.removeItem("medical-mock-session");
  }
}

export function buildCaseRequest(values: MedicalFormValues): CaseCreateRequest {
  const department = textValue(values, "department");
  return {
    patientName: textValue(values, "patientName"),
    gender: textValue(values, "gender") as GenderCode,
    age: Number(textValue(values, "age")),
    department: department ? department as DepartmentCode : undefined,
    visitDate: textValue(values, "visitDate") || undefined,
    chiefComplaint: textValue(values, "chiefComplaint"),
    presentIllness: textValue(values, "presentIllness"),
    pastHistory: textValue(values, "pastHistory") || undefined,
    allergyHistory: textValue(values, "allergyHistory") || undefined,
    vitalSigns: textValue(values, "vitalSigns") || undefined,
    physicalExam: textValue(values, "physicalExam") || undefined,
    auxiliaryExam: textValue(values, "auxiliaryExam") || undefined,
    preliminaryDiagnosis: textValue(values, "preliminaryDiagnosis") || undefined,
    treatmentTaken: textValue(values, "treatmentTaken") || undefined,
    medicationUsage: textValue(values, "medicationUsage") || undefined,
    generationNeeds: selectedNeeds(values),
  };
}

export async function createAndAnalyze(values: MedicalFormValues): Promise<CaseRecordView> {
  const payload = buildCaseRequest(values);
  if (USE_MOCK_API) return mockCreateCase(payload);

  const files = selectedFiles(values);
  let created: BackendCreateCaseResponse;
  if (files.length > 0) {
    const form = new FormData();
    form.append("case", new Blob([JSON.stringify(payload)], { type: "application/json" }), "case.json");
    files.forEach((file) => form.append("attachments", file));
    created = await request(http.post<BackendCreateCaseResponse>("/api/v1/cases", form));
  } else {
    created = await request(http.post<BackendCreateCaseResponse>("/api/v1/cases", payload));
  }

  await waitForJob(created.jobId);
  return mapDetail(await backendDetail(created.caseId));
}

export async function listCases(keyword = "", page = 0, size = 20): Promise<PageResult<CaseRecordView>> {
  if (USE_MOCK_API) return mockListCases(keyword, page, size);
  const history = await request(http.get<BackendHistoryPage>("/api/v1/cases", {
    params: { keyword: keyword.trim(), page, size },
  }));
  const items = await Promise.all(history.content.map(async (item) => mapDetail(await backendDetail(item.caseId))));
  return { items, total: history.totalElements, page: history.page, size: history.size };
}

export async function getCase(id: string): Promise<CaseRecordView> {
  if (USE_MOCK_API) return mockGetCase(id);
  const detail = await backendDetail(id);
  let lastError: string | null = null;
  if ((detail.status === "failed" || detail.status === "cancelled") && detail.currentJobId) {
    const job = await request(http.get<BackendJob>(`/api/v1/jobs/${detail.currentJobId}`));
    lastError = job.errorMessage ?? null;
  }
  return mapDetail(detail, lastError);
}

export async function updateCase(id: string, editedRecord: string): Promise<CaseRecordView> {
  if (USE_MOCK_API) return mockUpdateCase(id, editedRecord);
  const detail = await request(http.put<BackendCaseDetail>(
    `/api/v1/cases/${id}/record`,
    { editedRecord },
  ));
  return mapDetail(detail);
}

export async function downloadReport(id: string): Promise<Blob> {
  if (USE_MOCK_API) return mockDownloadReport(id);
  try {
    const response = await http.get(`/api/v1/cases/${id}/report`, { responseType: "blob" });
    return response.data as Blob;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data instanceof Blob) {
      try {
        const payload = JSON.parse(await error.response.data.text()) as ApiErrorPayload;
        throw new MedicalApiError(payload.message || "报告下载失败，请稍后重试。", {
          status: error.response.status,
          fieldErrors: payload.fieldErrors,
          requestId: payload.requestId,
        });
      } catch (blobError) {
        if (blobError instanceof MedicalApiError) throw blobError;
      }
    }
    throw toApiError(error);
  }
}

export async function downloadAttachment(url: string): Promise<Blob> {
  try {
    const response = await http.get(url, { responseType: "blob" });
    return response.data as Blob;
  } catch (error) {
    throw toApiError(error);
  }
}
