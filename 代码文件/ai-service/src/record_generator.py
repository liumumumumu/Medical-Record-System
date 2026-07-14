from src.schema import PatientInput


class RecordGenerator:
    def generate(
        self,
        patient: PatientInput,
        diagnosis: str,
        treatment_advice: str,
    ) -> str:
        department = {
            "internal": "内科",
            "surgery": "外科",
            "pediatrics": "儿科",
            "emergency": "急诊",
            "other": "其他",
        }.get(patient.department, patient.department or "未提供")
        return "\n".join(
            (
                "一、基本信息",
                f"姓名：{patient.name}",
                f"性别：{patient.gender}",
                f"年龄：{patient.age}岁",
                f"就诊科室：{department}",
                f"就诊日期：{patient.visit_date or '未提供'}",
                "",
                "二、主诉",
                patient.chief_complaint,
                "",
                "三、现病史",
                patient.history_present_illness,
                "",
                "四、既往史",
                patient.past_history,
                "",
                "五、过敏史",
                patient.allergy_history,
                "",
                "六、生命体征与体格检查",
                f"生命体征：{patient.vital_signs}",
                f"体格检查：{patient.physical_exam}",
                "",
                "七、辅助检查",
                patient.lab_results,
                "",
                "八、初步诊断",
                diagnosis,
                "",
                "九、处理建议",
                treatment_advice,
            )
        )
