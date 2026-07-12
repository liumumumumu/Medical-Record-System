import type {
  AiResult,
  AuthSession,
  AuthUser,
  CaseCreateRequest,
  CaseRecordView,
  PageResult,
  RegisterRequest,
} from "../types/medical-record";

const MOCK_TOKEN = "medical-demo-token";
const RECORDS_KEY = "medical-mock-records";
const USERS_KEY = "medical-mock-users";
const SESSION_KEY = "medical-mock-session";

type MockUser = AuthUser & { password: string };

function delay(ms = 280) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function readRecords(): CaseRecordView[] {
  try {
    return JSON.parse(window.localStorage.getItem(RECORDS_KEY) ?? "[]") as CaseRecordView[];
  } catch {
    return [];
  }
}

function writeRecords(records: CaseRecordView[]) {
  window.localStorage.setItem(RECORDS_KEY, JSON.stringify(records));
}

const demoUser: MockUser = {
  id: "user_demo_doctor",
  username: "doctor",
  displayName: "演示医生",
  password: "demo123",
};

function readUsers(): MockUser[] {
  try {
    const stored = JSON.parse(window.localStorage.getItem(USERS_KEY) ?? "[]") as MockUser[];
    return stored.some((user) => user.username === demoUser.username) ? stored : [demoUser, ...stored];
  } catch {
    return [demoUser];
  }
}

function writeUsers(users: MockUser[]) {
  window.localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

function issueMockSession(user: AuthUser): AuthSession {
  const token = `${MOCK_TOKEN}-${user.id}`;
  window.localStorage.setItem(SESSION_KEY, JSON.stringify({ token, user }));
  return {
    token,
    tokenType: "Bearer",
    expiresAt: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
    user,
  };
}

export async function mockLogin(username: string, password: string): Promise<AuthSession> {
  await delay();
  const user = readUsers().find((item) => item.username === username && item.password === password);
  if (!user) throw new Error("账号或密码错误。可使用演示账号 doctor / demo123。");
  return issueMockSession(user);
}

export async function mockRegister(request: RegisterRequest): Promise<AuthSession> {
  await delay();
  const users = readUsers();
  if (users.some((user) => user.username === request.username)) throw new Error("用户名已存在，请更换后重试。");
  const user: MockUser = {
    id: `mock_user_${Date.now().toString(36)}`,
    username: request.username,
    displayName: request.displayName,
    password: request.password,
  };
  writeUsers([...users, user]);
  return issueMockSession(user);
}

export async function mockCurrentUser(token: string): Promise<AuthUser> {
  await delay(80);
  try {
    const session = JSON.parse(window.localStorage.getItem(SESSION_KEY) ?? "null") as { token: string; user: AuthUser } | null;
    if (!session || session.token !== token) throw new Error("登录状态已失效");
    return session.user;
  } catch {
    throw new Error("登录状态已失效");
  }
}

function buildAiResult(input: CaseCreateRequest): AiResult {
  const evidence = `${input.chiefComplaint} ${input.presentIllness} ${input.vitalSigns ?? ""}`;
  const influenza = /高热|发热|咳嗽|酸痛|乏力|头痛/.test(evidence);
  const diagnosisTop1 = influenza ? "流行性感冒" : "上呼吸道感染";
  const symptoms = ["发热", "咳嗽", "乏力", "肌肉酸痛", "头痛"].filter((item) => evidence.includes(item));
  const generatedAt = new Date().toISOString();

  return {
    status: "completed",
    generatedAt,
    processingTimeMs: 6.4,
    model: {
      name: "medical-record-hybrid-diagnosis",
      version: "mock-1.0.0",
      confidence: influenza ? 0.54 : 0.42,
      lowConfidence: !influenza,
    },
    summary: {
      patientName: input.patientName,
      gender: input.gender,
      age: input.age,
      department: input.department ?? "",
      visitDate: input.visitDate ?? "",
      chiefComplaint: input.chiefComplaint,
    },
    structuredRecord: {
      presentIllness: input.presentIllness,
      pastHistory: input.pastHistory || "未提供",
      allergyHistory: input.allergyHistory || "无",
      vitalSigns: input.vitalSigns || "无",
      physicalExam: input.physicalExam || "无",
      auxiliaryExam: input.auxiliaryExam || "无",
      generatedRecord: `主诉：${input.chiefComplaint}\n现病史：${input.presentIllness}\n既往史：${input.pastHistory || "未提供"}\n辅助分析：${diagnosisTop1}。`,
    },
    analysis: {
      preliminaryDiagnosis: input.preliminaryDiagnosis || "待专业人员复核",
      treatmentTaken: input.treatmentTaken || "未提供",
      medicationUsage: input.medicationUsage || "未提供",
      generationNeeds: input.generationNeeds ?? [],
      symptoms,
      medicalTerms: influenza ? ["流行性感冒", "体温"] : ["上呼吸道感染"],
      diagnosisTop1,
      diagnosisCandidates: influenza ? ["流行性感冒", "上呼吸道感染", "急性咽炎"] : ["上呼吸道感染", "急性咽炎", "普通感冒"],
      diagnosisReason: `根据主诉、现病史和体征识别到 ${symptoms.join("、") || "有限症状"}，该结果仅用于演示排序。`,
      treatmentAdvice: "建议结合临床检查、病程变化和专业医师意见进一步判断。",
      content: "前端模拟服务返回的分析结果。",
      lowConfidence: !influenza,
      lowConfidenceReason: influenza ? null : "可用症状证据较少，需要补充检查信息。",
      disclaimer: "本结果仅用于课程演示和辅助分析，不替代执业医师诊断。",
    },
    attachments: (typeof input.attachments === "string" ? input.attachments.split(" / ") : input.attachments ?? [])
      .filter(Boolean)
      .map((fileName, index) => ({
        id: `input_${index + 1}`,
        fileName,
        mimeType: "application/octet-stream",
        url: "",
        processingStatus: "metadata_only" as const,
      })),
  };
}

export async function mockCreateCase(input: CaseCreateRequest): Promise<CaseRecordView> {
  await delay(520);
  const timestamp = new Date().toISOString();
  const aiResult = buildAiResult(input);
  const record: CaseRecordView = {
    id: `mock_${Date.now().toString(36)}`,
    status: "COMPLETED",
    patientInput: input,
    aiResult,
    generatedRecord: aiResult.structuredRecord.generatedRecord,
    editedRecord: aiResult.structuredRecord.generatedRecord,
    lastError: null,
    version: 1,
    createdAt: timestamp,
    updatedAt: timestamp,
  };
  writeRecords([record, ...readRecords()]);
  return record;
}

export async function mockListCases(keyword = "", page = 0, size = 20): Promise<PageResult<CaseRecordView>> {
  await delay(180);
  const search = keyword.trim().toLowerCase();
  const matched = readRecords().filter((record) => `${record.patientInput.patientName} ${record.patientInput.chiefComplaint} ${record.aiResult?.analysis.diagnosisTop1 ?? ""}`.toLowerCase().includes(search));
  return { items: matched.slice(page * size, page * size + size), total: matched.length, page, size };
}

export async function mockGetCase(id: string) {
  await delay(140);
  const record = readRecords().find((item) => item.id === id);
  if (!record) throw new Error("病例不存在或已过期");
  return record;
}

export async function mockUpdateCase(id: string, editedRecord: string) {
  await delay(160);
  const records = readRecords();
  const index = records.findIndex((record) => record.id === id);
  if (index < 0) throw new Error("病例不存在或已过期");
  const updated = { ...records[index], editedRecord, version: records[index].version + 1, updatedAt: new Date().toISOString() };
  records[index] = updated;
  writeRecords(records);
  return updated;
}

export async function mockDownloadReport(id: string) {
  const record = await mockGetCase(id);
  return new Blob([record.editedRecord || record.generatedRecord || "暂无病历内容"], { type: "text/plain;charset=utf-8" });
}
