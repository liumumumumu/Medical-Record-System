import { describe, expect, it } from "vitest";
import { buildCaseRequest, mapHistorySummary } from "./medical-api";

describe("buildCaseRequest", () => {
  it("normalizes text fields while keeping age zero and selected needs", () => {
    const request = buildCaseRequest({
      patientName: "  小王  ",
      gender: "female",
      age: "0",
      department: "pediatrics",
      visitDate: "2026-07-13",
      chiefComplaint: "  发热一天  ",
      presentIllness: "  今日出现发热  ",
      generationNeeds: ["record", "diagnosis"],
      attachments: [],
    });

    expect(request).toMatchObject({
      patientName: "小王",
      gender: "female",
      age: 0,
      department: "pediatrics",
      visitDate: "2026-07-13",
      chiefComplaint: "发热一天",
      presentIllness: "今日出现发热",
      generationNeeds: ["record", "diagnosis"],
    });
  });

  it("omits blank optional fields", () => {
    const request = buildCaseRequest({
      patientName: "测试患者",
      gender: "male",
      age: "18",
      department: "",
      visitDate: "",
      chiefComplaint: "咳嗽",
      presentIllness: "咳嗽两天",
      pastHistory: "   ",
      generationNeeds: [],
    });

    expect(request.department).toBeUndefined();
    expect(request.visitDate).toBeUndefined();
    expect(request.pastHistory).toBeUndefined();
  });
});

describe("mapHistorySummary", () => {
  it("maps a completed backend history item with its AI diagnosis", () => {
    const summary = mapHistorySummary({
      caseId: "case_1",
      patientName: "张某",
      gender: "male",
      age: 32,
      chiefComplaint: "发热咳嗽",
      diagnosisTop1: "上呼吸道感染",
      status: "completed",
      createdAt: "2026-07-15T00:00:00Z",
      updatedAt: "2026-07-15T00:05:00Z",
    });

    expect(summary).toMatchObject({
      id: "case_1",
      patientName: "张某",
      diagnosisTop1: "上呼吸道感染",
      status: "COMPLETED",
    });
  });

  it("keeps the preliminary diagnosis as fallback while analysis is pending", () => {
    const summary = mapHistorySummary({
      caseId: "case_2",
      patientName: "李某",
      gender: "female",
      age: 45,
      chiefComplaint: "头痛",
      preliminaryDiagnosis: "疑似偏头痛",
      status: "processing",
      createdAt: "2026-07-15T00:00:00Z",
      updatedAt: "2026-07-15T00:00:30Z",
    });

    expect(summary.status).toBe("DRAFT");
    expect(summary.diagnosisTop1).toBeNull();
    expect(summary.preliminaryDiagnosis).toBe("疑似偏头痛");
  });
});
