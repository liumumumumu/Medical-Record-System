package com.medicalrecord.backend.ai;

import com.medicalrecord.backend.cases.CaseInput;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class MockAiClient implements AiClient {

    @Override
    public AiAnalysisResult analyze(CaseInput input) {
        String text = String.join(" ", safe(input.chiefComplaint()), safe(input.presentIllness()),
                safe(input.physicalExam()), safe(input.auxiliaryExam()));

        AnalysisPreset preset = selectPreset(text);
        String record = "基本信息：" + input.patientName() + "，" + genderText(input) + "，" + input.age() + "岁\n"
                + "主诉：" + input.chiefComplaint() + "\n"
                + "现病史：" + input.presentIllness() + "\n"
                + "既往史：" + input.pastHistory() + "\n"
                + "过敏史：" + defaultNone(input.allergyHistory()) + "\n"
                + "体格检查：" + defaultNone(input.physicalExam()) + "\n"
                + "辅助检查：" + defaultNone(input.auxiliaryExam()) + "\n"
                + "辅助分析：" + preset.diagnosis() + "\n"
                + "处理建议：" + preset.advice();

        return new AiAnalysisResult(
                record,
                preset.symptoms(),
                preset.medicalTerms(),
                preset.diagnosis(),
                preset.candidates(),
                preset.reason(),
                preset.advice(),
                "基于主诉、现病史、体格检查和辅助检查进行了规则化综合分析。",
                "mock-rules-1.0",
                0.75,
                false,
                null,
                new RecordGenerationInfo(
                        "template",
                        "mock-fact-template",
                        "record-gen-template-mock-1.0",
                        false,
                        List.of("当前后端使用课程演示 Mock，不代表真实 Transformer 推理")
                )
        );
    }

    private AnalysisPreset selectPreset(String text) {
        if (containsAny(text, "腹痛", "腹泻", "呕吐")) {
            return new AnalysisPreset(
                    "急性胃肠炎",
                    matching(text, List.of("腹痛", "腹泻", "呕吐")),
                    List.of("胃肠道症状", "脱水风险"),
                    List.of("急性胃肠炎", "消化不良"),
                    "存在胃肠道症状表现，需结合饮食史和相关检查进一步判断。",
                    "建议注意补液与饮食调整，必要时完善相关检查并由医生评估。"
            );
        }
        if (containsAny(text, "头痛", "头晕")) {
            return new AnalysisPreset(
                    "头痛待查",
                    matching(text, List.of("头痛", "头晕", "乏力")),
                    List.of("神经系统症状"),
                    List.of("紧张性头痛", "偏头痛"),
                    "存在头痛或头晕表现，当前信息不足以确定具体病因。",
                    "建议记录症状持续时间和诱因，出现加重或异常体征时及时就医。"
            );
        }
        return new AnalysisPreset(
                "上呼吸道感染",
                matching(text, List.of("发热", "咳嗽", "咽痛", "乏力")),
                List.of("上呼吸道感染", "体温"),
                List.of("上呼吸道感染", "流感"),
                "主诉和现病史包含常见呼吸道感染相关表现，需结合检查结果进一步判断。",
                "建议休息、多饮水并观察症状，必要时完善血常规等检查。"
        );
    }

    private List<String> matching(String text, List<String> candidates) {
        List<String> found = new ArrayList<>();
        candidates.stream().filter(text::contains).forEach(found::add);
        return found.isEmpty() ? List.of("症状待进一步确认") : List.copyOf(found);
    }

    private boolean containsAny(String text, String... values) {
        for (String value : values) {
            if (text.contains(value)) {
                return true;
            }
        }
        return false;
    }

    private String genderText(CaseInput input) {
        return input.gender().value().equals("male") ? "男" : "女";
    }

    private String safe(String value) {
        return value == null ? "" : value;
    }

    private String defaultNone(String value) {
        return value == null || value.isBlank() ? "未提供" : value;
    }

    private record AnalysisPreset(
            String diagnosis,
            List<String> symptoms,
            List<String> medicalTerms,
            List<String> candidates,
            String reason,
            String advice
    ) {
    }
}
