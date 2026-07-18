import os
import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

# Unit tests exercise deterministic record assembly. Transformer loading/inference
# is covered by the dedicated smoke/acceptance command after training.
os.environ.setdefault("RECORD_GENERATOR_BACKEND", "template")
os.environ.setdefault("REQUIRE_RECORD_GENERATOR", "false")
