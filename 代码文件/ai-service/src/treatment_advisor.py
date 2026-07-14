from dataclasses import dataclass

from src.config import CONFIG_DIR, load_json
from src.text_utils import has_positive_occurrence, normalize_text


DISCLAIMER = "本结果仅用于课程演示和辅助分析，不替代医生诊断。"


@dataclass(frozen=True)
class TreatmentResult:
    advice: str
    red_flags: list[str]


class TreatmentAdvisor:
    def __init__(self) -> None:
        self.rules = load_json(CONFIG_DIR / "treatment_rules.json")
        self.red_flag_rules = load_json(CONFIG_DIR / "red_flags.json")

    def generate(self, diagnosis: str, text: str) -> TreatmentResult:
        normalized = normalize_text(text)
        messages: list[str] = []
        flags: list[str] = []
        for rule in self.red_flag_rules:
            if any(
                pattern in normalized and has_positive_occurrence(normalized, pattern)
                for pattern in rule["patterns"]
            ):
                flags.append(rule["name"])
                messages.append(rule["message"])
        if not messages:
            messages.append(self.rules.get(diagnosis, self.rules["暂无法确定"]))
        return TreatmentResult(advice="".join(dict.fromkeys(messages)), red_flags=flags)
