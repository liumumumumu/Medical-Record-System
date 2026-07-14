export type GenderCode = "male" | "female";
export type DepartmentCode = "internal" | "surgery" | "pediatrics" | "emergency" | "other";
export type GenerationNeed = "record" | "symptom" | "diagnosis" | "treatment" | "full-report";
export type FieldValue = string | string[] | File[];
export type MedicalFormValues = Record<string, FieldValue>;

export type AuthUser = {
  id: string;
  username: string;
  displayName: string;
  role?: string;
};

export type AuthSession = {
  token: string;
  tokenType: "Bearer";
  expiresAt: string;
  user: AuthUser;
};

export type RegisterRequest = {
  username: string;
  password: string;
  displayName: string;
};

export type CaseCreateRequest = {
  patientName: string;
  gender: GenderCode;
  age: number;
  department?: DepartmentCode | "";
  visitDate?: string;
  chiefComplaint: string;
  presentIllness: string;
  pastHistory?: string;
  allergyHistory?: string;
  vitalSigns?: string;
  physicalExam?: string;
  auxiliaryExam?: string;
  attachments?: string | string[];
  preliminaryDiagnosis?: string;
  treatmentTaken?: string;
  medicationUsage?: string;
  generationNeeds?: GenerationNeed[];
};

export type AttachmentView = {
  id: string;
  fileName: string;
  mimeType: string;
  url: string;
  processingStatus: "metadata_only" | "not_processed" | "pending" | "parsed" | "failed";
  extractedText?: string;
  failureReason?: string;
  confidence?: number | null;
};

export type AiResult = {
  status?: "completed" | "failed";
  generatedAt?: string;
  processingTimeMs?: number;
  model?: {
    name: string;
    version: string;
    confidence: number;
    lowConfidence: boolean;
  };
  summary: {
    patientName: string;
    gender: GenderCode;
    age: number;
    department: DepartmentCode | "";
    visitDate: string;
    chiefComplaint: string;
  };
  structuredRecord: {
    presentIllness: string;
    pastHistory: string;
    allergyHistory: string;
    vitalSigns: string;
    physicalExam: string;
    auxiliaryExam: string;
    generatedRecord: string;
  };
  analysis: {
    preliminaryDiagnosis: string;
    treatmentTaken: string;
    medicationUsage: string;
    generationNeeds: GenerationNeed[];
    symptoms: string[];
    medicalTerms: string[];
    diagnosisTop1: string;
    diagnosisCandidates: string[];
    diagnosisReason: string;
    treatmentAdvice: string;
    content?: string;
    lowConfidence: boolean;
    lowConfidenceReason?: string | null;
    disclaimer: string;
  };
  attachments: AttachmentView[];
  failureReason?: string | null;
};

export type CaseRecordView = {
  id: string;
  status: "DRAFT" | "COMPLETED" | "ANALYSIS_FAILED";
  patientInput: CaseCreateRequest;
  aiResult: AiResult | null;
  generatedRecord: string | null;
  editedRecord: string | null;
  lastError: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
};

export type PageResult<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
};

export type ApiErrorPayload = {
  code: number | string;
  message: string;
  data?: {
    fieldErrors?: Record<string, string>;
  };
  fieldErrors?: Record<string, string>;
  requestId?: string;
};
