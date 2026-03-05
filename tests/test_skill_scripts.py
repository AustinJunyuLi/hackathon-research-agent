"""Tests for OpenClaw skill helper scripts."""

from __future__ import annotations

import json
from importlib import util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skill"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"


def _load_module(path: Path, name: str) -> object:
    assert path.exists(), f"Missing script: {path}"
    spec = util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openclaw_cron_task_mentions_paper_id_drill_down() -> None:
    config = json.loads((SKILL_ROOT / "openclaw.json").read_text())
    cron_task = config["cron"][0]["task"]
    assert "paper ID" in cron_task


def test_setup_daily_cron_supports_whatsapp(monkeypatch, capsys) -> None:
    module = _load_module(SCRIPTS_ROOT / "setup_daily_cron.py", "setup_daily_cron")
    captured: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], check: bool, capture_output: bool, text: bool):
        captured["cmd"] = cmd
        return module.subprocess.CompletedProcess(cmd, 0, stdout='{"ok": true}')

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "setup_daily_cron.py",
            "--project-root",
            str(REPO_ROOT),
            "--whatsapp",
            "+447700900123",
        ],
    )

    module.main()

    cmd = captured["cmd"]
    assert "--channel" in cmd
    assert cmd[cmd.index("--channel") + 1] == "whatsapp"
    assert "--to" in cmd
    assert cmd[cmd.index("--to") + 1] == "+447700900123"
    message = cmd[cmd.index("--message") + 1]
    assert "Format the results for WhatsApp" in message
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_format_whatsapp_digest_groups_papers(tmp_path: Path) -> None:
    module = _load_module(SCRIPTS_ROOT / "format_whatsapp.py", "format_whatsapp")
    summary_path = tmp_path / "batch_summary.json"
    summary_path.write_text(
        json.dumps(
            [
                {
                    "arxiv_id": "2106.09685",
                    "title": "LoRA",
                    "summary": "Directly relevant to parameter-efficient fine-tuning work.",
                    "read_decision": "read in full",
                    "novelty_score": 0.91,
                    "local_relevance": 0.96,
                },
                {
                    "arxiv_id": "1706.03762",
                    "title": "Attention Is All You Need",
                    "summary": "Foundational transformer paper.",
                    "read_decision": "skim",
                    "novelty_score": 0.0,
                    "local_relevance": 0.86,
                },
                {
                    "arxiv_id": "1512.03385",
                    "title": "ResNet",
                    "summary": "Computer vision paper with low relevance here.",
                    "read_decision": "skip",
                    "relevance": "low",
                },
            ]
        )
    )

    digest = module.format_whatsapp_digest(summary_path)

    assert "READ IN FULL" in digest
    assert "SKIM" in digest
    assert "SKIP" in digest
    assert "LoRA (2106.09685)" in digest
    assert "Attention Is All You Need (1706.03762)" in digest
    assert "ResNet -- low" in digest
    assert "Reply with a paper ID for the full memo." in digest
