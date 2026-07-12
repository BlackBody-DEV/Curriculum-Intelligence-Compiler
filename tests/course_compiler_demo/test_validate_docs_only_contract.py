import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "course_compiler_demo"))

from validate_docs_only_contract import ContractValidationError, validate_contract  # noqa: E402


VALID_CONTRACT = REPO_ROOT / ".axiomiq" / "task_contracts" / "docs_only_finalize_v1.json"


def load_valid_contract(tmp_path: Path) -> Path:
    data = json.loads(VALID_CONTRACT.read_text())
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(data))
    return path


def test_docs_only_finalize_contract_is_valid() -> None:
    checks = validate_contract(VALID_CONTRACT)
    assert "valid JSON" in checks
    assert "safety flags false" in checks


def test_rejects_alpha_access(tmp_path: Path) -> None:
    path = load_valid_contract(tmp_path)
    data = json.loads(path.read_text())
    data["source_snapshot"]["live_alpha_access"] = "advisory_only"
    path.write_text(json.dumps(data))

    with pytest.raises(ContractValidationError, match="live_alpha_access"):
        validate_contract(path)


def test_rejects_enabled_safety_flag(tmp_path: Path) -> None:
    path = load_valid_contract(tmp_path)
    data = json.loads(path.read_text())
    data["safety_flags"]["allow_database_contact"] = True
    path.write_text(json.dumps(data))

    with pytest.raises(ContractValidationError, match="allow_database_contact"):
        validate_contract(path)


def test_rejects_non_docs_path(tmp_path: Path) -> None:
    path = load_valid_contract(tmp_path)
    data = json.loads(path.read_text())
    data["allowed_paths"].append("tools/course_compiler_demo/runner.py")
    path.write_text(json.dumps(data))

    with pytest.raises(ContractValidationError, match="outside docs-only compiler scope"):
        validate_contract(path)


def test_rejects_unsafe_action(tmp_path: Path) -> None:
    path = load_valid_contract(tmp_path)
    data = json.loads(path.read_text())
    data["actions"].append("execute")
    path.write_text(json.dumps(data))

    with pytest.raises(ContractValidationError, match="actions are not docs-only safe"):
        validate_contract(path)
