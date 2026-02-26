"""Core constants for Manus."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "manus" / "config"
WORKSPACE_DIR = PROJECT_ROOT / "workspace"

DEFAULT_MODEL_YAML = CONFIG_DIR / "models.yaml"

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 120

MEMORY_DIR = PROJECT_ROOT / "memory"
TASK_PLAN_FILE = "task_plan.md"
NOTES_FILE = "notes.md"
OUTPUT_FILE = "output.md"

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
