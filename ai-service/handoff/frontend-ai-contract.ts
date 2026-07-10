export type GenderCode = "male" | "female";
export type DepartmentCode = "internal" | "surgery" | "pediatrics" | "emergency" | "other";
export type GenerationNeed = "record" | "symptom" | "diagnosis" | "treatment" | "full-report";

export type FrontendCaseRequest = {
  patientName: string;
  gender: GenderCode;
  age: number;
  department?: DepartmentCode | "";
  visitDate?: string;
  chiefComplaint: string;
  presentIllness: string;
  pastHistory: string;
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

export type FrontendAnalysisResult = {
  status: "completed";
  generatedAt: string;
  processingTimeMs: number;
  model: {
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
    content: string;
    lowConfidence: boolean;
    lowConfidenceReason: string | null;
    disclaimer: string;
  };
  attachments: Array<{
    id: string;
    fileName: string;
    mimeType: string;
    url: string;
    processingStatus: "metadata_only" | "pending" | "parsed" | "failed";
    extractedText: string;
    failureReason: string;
    confidence: number | null;
  }>;
  failureReason: null;
};

export type AiApiError = {
  code: "VALIDATION_ERROR" | "FILE_TOO_LARGE" | "AI_PROCESSING_FAILED" | "AI_TIMEOUT";
  message: string;
  fieldErrors: Record<string, string>;
  requestId: string;
};

