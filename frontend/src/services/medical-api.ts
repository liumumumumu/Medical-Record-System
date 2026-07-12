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
  ApiErrorPayload,
  AuthSession,
  AuthUser,
  CaseCreateRequest,
  CaseRecordView,
  MedicalFormValues,
  PageResult,
  RegisterRequest,
} from "../types/medical-record";

const TOKEN_KEY = "medical-auth-token";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8080";
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === "true";

type ApiResponse<T> = {
  code: number;
  message: string;
  data: T;
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
  headers: { "Content-Type": "application/json" },
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
    const fieldErrors = payload?.fieldErrors ?? (payload?.data as { fieldErrors?: Record<string, string> } | undefined)?.fieldErrors;
    return new MedicalApiError(payload?.message ?? error.message ?? "网络连接失败，请稍后重试。", {
      status: error.response?.status,
      fieldErrors,
      requestId: payload?.requestId,
    });
  }
  return new MedicalApiError(error instanceof Error ? error.message : "请求失败，请稍后重试。");
}

async function unwrap<T>(request: Promise<{ data: ApiResponse<T> }>) {
  try {
    const response = await request;
    if (response.data.code !== 200) throw new MedicalApiError(response.data.message);
    return response.data.data;
  } catch (error) {
    throw toApiError(error);
  }
}

export function isMockApi() {
  return USE_MOCK_API;
}

export function getStoredToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export function isUnauthorized(error: unknown) {
  return error instanceof MedicalApiError && error.status === 401;
}

export async function login(username: string, password: string): Promise<AuthSession> {
  if (USE_MOCK_API) {
    try {
      const session = await mockLogin(username, password);
      storeToken(session.token);
      return session;
    } catch (error) {
      throw toApiError(error);
    }
  }
  const session = await unwrap(http.post<ApiResponse<AuthSession>>("/api/v1/auth/login", { username, password }));
  storeToken(session.token);
  return session;
}

export async function register(request: RegisterRequest): Promise<AuthSession> {
  if (USE_MOCK_API) {
    try {
      const session = await mockRegister(request);
      storeToken(session.token);
      return session;
    } catch (error) {
      throw toApiError(error);
    }
  }
  const session = await unwrap(http.post<ApiResponse<AuthSession>>("/api/v1/auth/register", request));
  storeToken(session.token);
  return session;
}

export async function getCurrentUser(): Promise<AuthUser> {
  const token = getStoredToken();
  if (!token) throw new MedicalApiError("尚未登录", { status: 401 });
  if (USE_MOCK_API) {
    try {
      return await mockCurrentUser(token);
    } catch (error) {
      throw new MedicalApiError(error instanceof Error ? error.message : "登录状态已失效", { status: 401 });
    }
  }
  return unwrap(http.get<ApiResponse<AuthUser>>("/api/v1/auth/me"));
}

export async function logout() {
  try {
    if (!USE_MOCK_API) await unwrap(http.post<ApiResponse<null>>("/api/v1/auth/logout"));
  } finally {
    clearStoredToken();
    if (USE_MOCK_API) window.localStorage.removeItem("medical-mock-session");
  }
}

function textValue(values: MedicalFormValues, key: string) {
  const value = values[key];
  return typeof value === "string" ? value.trim() : "";
}

export function buildCaseRequest(values: MedicalFormValues): CaseCreateRequest {
  const needs = values.generationNeeds;
  return {
    patientName: textValue(values, "patientName"),
    gender: textValue(values, "gender") as CaseCreateRequest["gender"],
    age: Number(textValue(values, "age")),
    department: textValue(values, "department") as CaseCreateRequest["department"],
    visitDate: textValue(values, "visitDate"),
    chiefComplaint: textValue(values, "chiefComplaint"),
    presentIllness: textValue(values, "presentIllness"),
    // The data contract makes this optional; the temporary backend still requires a nonblank value.
    pastHistory: textValue(values, "pastHistory") || "未提供",
    allergyHistory: textValue(values, "allergyHistory"),
    vitalSigns: textValue(values, "vitalSigns"),
    physicalExam: textValue(values, "physicalExam"),
    auxiliaryExam: textValue(values, "auxiliaryExam"),
    attachments: textValue(values, "attachments"),
    preliminaryDiagnosis: textValue(values, "preliminaryDiagnosis"),
    treatmentTaken: textValue(values, "treatmentTaken"),
    medicationUsage: textValue(values, "medicationUsage"),
    generationNeeds: Array.isArray(needs) ? needs as CaseCreateRequest["generationNeeds"] : [],
  };
}

export async function createAndAnalyze(values: MedicalFormValues): Promise<CaseRecordView> {
  const payload = buildCaseRequest(values);
  if (USE_MOCK_API) return mockCreateCase(payload);
  return unwrap(http.post<ApiResponse<CaseRecordView>>("/api/v1/cases", payload));
}

export async function listCases(keyword = "", page = 0, size = 20): Promise<PageResult<CaseRecordView>> {
  if (USE_MOCK_API) return mockListCases(keyword, page, size);
  return unwrap(http.get<ApiResponse<PageResult<CaseRecordView>>>("/api/records", { params: { keyword, page, size } }));
}

export async function getCase(id: string): Promise<CaseRecordView> {
  if (USE_MOCK_API) return mockGetCase(id);
  return unwrap(http.get<ApiResponse<CaseRecordView>>(`/api/records/${id}`));
}

export async function updateCase(id: string, editedRecord: string): Promise<CaseRecordView> {
  if (USE_MOCK_API) return mockUpdateCase(id, editedRecord);
  return unwrap(http.put<ApiResponse<CaseRecordView>>(`/api/records/${id}`, { editedRecord }));
}

export async function downloadReport(id: string): Promise<Blob> {
  if (USE_MOCK_API) return mockDownloadReport(id);
  try {
    const response = await http.get(`/api/reports/${id}/download`, { responseType: "blob" });
    return response.data as Blob;
  } catch (error) {
    throw toApiError(error);
  }
}
