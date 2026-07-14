import { describe, expect, it } from "vitest";
import { buildCaseRequest } from "./medical-api";

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
