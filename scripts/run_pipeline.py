from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

PIPELINE_STEPS = [
    ("merge NHANES tables", ROOT / "scripts" / "merge_nhanes.py"),
    ("standardize selected fields", ROOT / "scripts" / "standardize_nhanes.py"),
    ("analyze data quality", ROOT / "scripts" / "analyze_data_quality.py"),
    ("create analysis subsets", ROOT / "scripts" / "create_analysis_subsets.py"),
    ("validate generated outputs", ROOT / "scripts" / "validate_outputs.py"),
]


def run_pipeline(runner=subprocess.run) -> None:
    for index, (step_name, script_path) in enumerate(PIPELINE_STEPS, start=1):
        print(f"[{index}/{len(PIPELINE_STEPS)}] {step_name}")
        runner([sys.executable, str(script_path)], cwd=ROOT, check=True)


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
