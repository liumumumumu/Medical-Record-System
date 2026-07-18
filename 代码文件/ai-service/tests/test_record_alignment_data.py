from scripts.prepare_record_alignment_data import (
    align_row,
    exact_copy_row,
    select_formal_target,
    structured_oral_augmentation,
)


def oral_dialogue_row():
    formal = (
        "<主诉>腹痛、腹泻2天。"
        "<现病史>患者2天前进食烧烤后出现阵发性腹痛、腹泻，排稀便4-5次，"
        "伴恶心，无呕吐、发热，自行饮用热水后症状无明显缓解。"
        "<既往史>既往体健。<辅助检查>未提供"
    )
    oral = (
        "<主诉>肚子疼还拉肚子两天"
        "<现病史>我前天晚上吃了烧烤，第二天肚子一阵一阵疼，拉了四五次，怎么办？"
        "<既往史>平时身体正常<辅助检查>未提供"
    )
    return {
        "id": "oral-001",
        "originalId": "oral-001",
        "sourceDataset": "IMCS-21",
        "department": "内科",
        "source": (
            "[患者自述]肚子疼还拉肚子两天，前天晚上吃了烧烤，"
            "第二天肚子一阵一阵疼，拉了四五次，怎么办？\n"
            "[问诊与治疗记录]\n患者：都是稀的，有点恶心，但是没吐，也没发烧。\n"
            "患者：自己喝了点热水，感觉没什么用。"
        ),
        "target": oral,
        "targets": [oral, formal],
    }


def test_formal_reference_is_selected_over_colloquial_reference():
    selected = select_formal_target(oral_dialogue_row())
    assert "腹痛、腹泻2天" in selected
    assert "患者2天前" in selected
    assert "怎么办" not in selected


def test_alignment_source_comes_from_original_dialogue_not_reference_report():
    aligned = align_row(oral_dialogue_row(), 1, "train")
    assert "[主诉原文]肚子疼还拉肚子两天" in aligned["source"]
    assert "[现病史原文]肚子疼还拉肚子两天" in aligned["source"]
    assert "[现病史原文]患者2天前进食烧烤后" not in aligned["source"]
    assert "<主诉>腹痛、腹泻2天" in aligned["target"]
    assert exact_copy_row(aligned) is False


def test_training_only_structured_augmentation_teaches_oral_to_clinical_style():
    augmented = structured_oral_augmentation(oral_dialogue_row(), 1)
    assert augmented is not None
    assert "[主诉原文]肚子疼、拉肚子2天" in augmented["source"]
    assert "肚子一阵一阵疼" in augmented["source"]
    assert "[体格检查]" in augmented["source"]
    assert "<主诉>腹痛、腹泻2天" in augmented["target"]
    assert augmented["split"] == "train"
    assert exact_copy_row(augmented) is False
