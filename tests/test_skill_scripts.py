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


def test_openclaw_cron_task_mentions_source_sync() -> None:
    config = json.loads((SKILL_ROOT / "openclaw.json").read_text())
    cron_task = config["cron"][0]["task"]
    assert "sync enrolled research sources" in cron_task


def test_openclaw_cron_default_schedule_is_three_times_weekly() -> None:
    config = json.loads((SKILL_ROOT / "openclaw.json").read_text())
    schedule = config["cron"][0]["schedule"]["expression"]
    assert schedule == "0 8 * * 1,3,5"


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


def test_setup_daily_cron_defaults_to_three_times_weekly(monkeypatch, capsys) -> None:
    module = _load_module(SCRIPTS_ROOT / "setup_daily_cron.py", "setup_daily_cron_default")
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
        ],
    )

    module.main()

    cmd = captured["cmd"]
    assert cmd[cmd.index("--cron") + 1] == "0 8 * * 1,3,5"
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_setup_daily_cron_message_syncs_before_batch_triage() -> None:
    module = _load_module(SCRIPTS_ROOT / "setup_daily_cron.py", "setup_daily_cron_sync")

    message = module._build_message(REPO_ROOT, "ids.txt", "out/daily_latest")

    assert "python3 skill/scripts/enroll.py sync" in message
    assert "triage --batch-file ids.txt --format json --output-dir out/daily_latest" in message
    assert "No strong papers worth pushing this cycle." in message


def test_run_triage_syncs_sources_before_triage(monkeypatch) -> None:
    module = _load_module(SCRIPTS_ROOT / "run_triage.py", "run_triage_sync")
    events: list[str] = []

    def fake_sync() -> None:
        events.append("sync")

    async def fake_run_via_python(
        arxiv_input: str,
        output_format: str,
        output_path: str | None,
    ) -> None:
        events.append(f"triage:{arxiv_input}:{output_format}:{output_path}")

    monkeypatch.setattr(module, "sync_all_sources", fake_sync, raising=False)
    monkeypatch.setattr(module, "_run_via_python", fake_run_via_python)
    monkeypatch.setattr("sys.argv", ["run_triage.py", "2106.09685"])

    import asyncio

    asyncio.run(module.main())

    assert events == ["sync", "triage:2106.09685:markdown:None"]


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
                    "why_this_matters_to_you": "Extends your current low-rank adaptation notes.",
                    "read_decision": "read in full",
                    "novelty_score": 0.91,
                    "local_relevance": 0.96,
                },
                {
                    "arxiv_id": "1706.03762",
                    "title": "Attention Is All You Need",
                    "summary": "Foundational transformer paper.",
                    "why_this_matters_to_you": (
                        "Useful background context for your current modeling stack."
                    ),
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
    assert "Extends your current low-rank adaptation notes." in digest
    assert "ResNet -- low" in digest
    assert "Reply with a paper ID for the full memo." in digest


def test_format_whatsapp_digest_is_terse_when_everything_is_skip(tmp_path: Path) -> None:
    module = _load_module(SCRIPTS_ROOT / "format_whatsapp.py", "format_whatsapp_low_signal")
    summary_path = tmp_path / "batch_summary.json"
    summary_path.write_text(
        json.dumps(
            [
                {
                    "arxiv_id": "1512.03385",
                    "title": "ResNet",
                    "summary": "Computer vision paper with low relevance here.",
                    "read_decision": "skip",
                    "relevance": "low",
                }
            ]
        )
    )

    digest = module.format_whatsapp_digest(summary_path)

    assert "No strong papers worth pushing this cycle." in digest
    assert "READ IN FULL" not in digest
