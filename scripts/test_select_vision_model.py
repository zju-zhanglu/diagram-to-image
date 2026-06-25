"""Regression tests for select_vision_model.py."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import select_vision_model as selector


class SelectVisionModelTests(unittest.TestCase):
    def test_run_command_does_not_leak_parent_stdin_to_claude(self) -> None:
        with mock.patch("select_vision_model.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0, stdout="{}", stderr="")

            selector.run_command(["claude", "-p", "prompt"], 3)

        self.assertIs(run.call_args.kwargs["stdin"], selector.subprocess.DEVNULL)

    def test_claude_probe_passes_prompt_as_final_argument(self) -> None:
        with mock.patch("select_vision_model.make_probe_png") as make_png, mock.patch(
            "select_vision_model.run_command"
        ) as run:
            probe_path = mock.Mock()
            probe_path.name = ".probe.png"
            probe_path.parent = Path.cwd()
            probe_path.unlink = mock.Mock()
            make_png.return_value = probe_path
            run.return_value = selector.CommandResult(returncode=0, stdout="VISION_OK", stderr="")

            self.assertTrue(selector.probe_claude_image_support("vision-model", 3))

        command = run.call_args.args[0]
        self.assertIn("--model", command)
        self.assertEqual(command[command.index("--model") + 1], "vision-model")
        self.assertTrue(command[-1].startswith("Inspect this local PNG image: @.probe.png."))
        self.assertNotIn("--tools", command)

    def test_claude_probe_treats_api_error_as_failed_probe(self) -> None:
        with mock.patch("select_vision_model.make_probe_png") as make_png, mock.patch(
            "select_vision_model.run_command"
        ) as run:
            probe_path = mock.Mock()
            probe_path.name = ".probe.png"
            probe_path.parent = Path.cwd()
            probe_path.unlink = mock.Mock()
            make_png.return_value = probe_path
            run.return_value = selector.CommandResult(returncode=1, stdout="", stderr="API Error: bad request")

            result = selector.probe_claude_image_support("vision-model", 3)

        self.assertFalse(result)
        self.assertEqual(result.error, "api_error")

    def test_claude_probe_catches_timeout_and_cli_errors(self) -> None:
        with mock.patch("select_vision_model.make_probe_png") as make_png, mock.patch(
            "select_vision_model.run_command"
        ) as run:
            probe_path = mock.Mock()
            probe_path.name = ".probe.png"
            probe_path.parent = Path.cwd()
            probe_path.unlink = mock.Mock()
            make_png.return_value = probe_path
            run.side_effect = selector.subprocess.TimeoutExpired(["claude"], 3)

            timeout_result = selector.probe_claude_image_support("vision-model", 3)

            run.side_effect = OSError("missing cli")
            cli_result = selector.probe_claude_image_support("vision-model", 3)

        self.assertFalse(timeout_result)
        self.assertEqual(timeout_result.error, "probe_timeout")
        self.assertFalse(cli_result)
        self.assertTrue(cli_result.error.startswith("probe_cli_error:"))

    def test_probe_png_satisfies_common_minimum_image_dimensions(self) -> None:
        path = selector.make_probe_png()
        try:
            data = path.read_bytes()
        finally:
            path.unlink(missing_ok=True)

        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        self.assertGreater(width, 10)
        self.assertGreater(height, 10)

    def test_codex_prefers_current_model_when_it_supports_image(self) -> None:
        def runner(command: list[str], timeout: int) -> selector.CommandResult:
            self.assertEqual(command, ["codex", "debug", "models"])
            return selector.CommandResult(
                returncode=0,
                stdout=json.dumps(
                    {
                        "models": [
                            {"slug": "gpt-text", "display_name": "GPT Text", "input_modalities": ["text"]},
                            {"slug": "gpt-vision", "display_name": "GPT Vision", "input_modalities": ["text", "image"]},
                        ]
                    }
                ),
                stderr="",
            )

        result = selector.select_codex_model("gpt-vision", runner=runner)

        self.assertTrue(result["can_run_visual_review"])
        self.assertEqual(result["selected_model"], "gpt-vision")
        self.assertEqual(result["selection_reason"], "current_model_supports_image")
        self.assertEqual(result["vision_models"], ["gpt-vision"])

    def test_codex_uses_first_vision_model_when_current_is_text_only(self) -> None:
        def runner(command: list[str], timeout: int) -> selector.CommandResult:
            return selector.CommandResult(
                returncode=0,
                stdout=json.dumps(
                    {
                        "models": [
                            {"slug": "gpt-vision-a", "display_name": "GPT Vision A", "input_modalities": ["text", "image"]},
                            {"slug": "gpt-vision-b", "display_name": "GPT Vision B", "input_modalities": ["text", "image"]},
                        ]
                    }
                ),
                stderr="",
            )

        result = selector.select_codex_model("gpt-text", runner=runner)

        self.assertTrue(result["can_run_visual_review"])
        self.assertEqual(result["selected_model"], "gpt-vision-a")
        self.assertEqual(result["selection_reason"], "first_available_vision_model")

    def test_codex_skips_when_no_vision_models_exist(self) -> None:
        def runner(command: list[str], timeout: int) -> selector.CommandResult:
            return selector.CommandResult(
                returncode=0,
                stdout=json.dumps({"models": [{"slug": "gpt-text", "input_modalities": ["text"]}]}),
                stderr="",
            )

        result = selector.select_codex_model("gpt-text", runner=runner)

        self.assertFalse(result["can_run_visual_review"])
        self.assertIsNone(result["selected_model"])
        self.assertEqual(result["selection_reason"], "no_vision_model_available")

    def test_claude_parses_candidates_and_prefers_current_after_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "model": "sonnet",
                        "env": {
                            "ANTHROPIC_MODEL": "provider-current",
                            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "provider-haiku",
                            "ANTHROPIC_DEFAULT_SONNET_MODEL": "provider-sonnet",
                            "ANTHROPIC_DEFAULT_OPUS_MODEL": "provider-opus",
                        },
                    }
                ),
                encoding="utf-8",
            )
            probed: list[str] = []

            def probe(model: str, timeout: int) -> bool:
                probed.append(model)
                return model == "provider-current"

            result = selector.select_claude_model(
                None,
                settings_paths=[settings_path],
                env={},
                probe=probe,
            )

        self.assertTrue(result["can_run_visual_review"])
        self.assertEqual(result["current_model"], "provider-current")
        self.assertEqual(result["selected_model"], "provider-current")
        self.assertEqual(result["selection_reason"], "current_model_supports_image")
        self.assertEqual(probed[0], "provider-current")

    def test_claude_uses_first_successful_probe_when_current_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "env": {
                            "ANTHROPIC_MODEL": "text-only",
                            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "vision-haiku",
                            "ANTHROPIC_DEFAULT_SONNET_MODEL": "vision-sonnet",
                        }
                    }
                ),
                encoding="utf-8",
            )

            def probe(model: str, timeout: int) -> bool:
                return model == "vision-haiku"

            result = selector.select_claude_model(
                None,
                settings_paths=[settings_path],
                env={},
                probe=probe,
            )

        self.assertTrue(result["can_run_visual_review"])
        self.assertEqual(result["selected_model"], "vision-haiku")
        self.assertEqual(result["selection_reason"], "first_available_vision_model")
        self.assertEqual(result["vision_models"], ["vision-haiku"])

    def test_claude_skips_when_all_probes_fail(self) -> None:
        result = selector.select_claude_model(
            "text-only",
            settings_paths=[],
            env={"ANTHROPIC_DEFAULT_HAIKU_MODEL": "also-text"},
            probe=lambda model, timeout: False,
        )

        self.assertFalse(result["can_run_visual_review"])
        self.assertIsNone(result["selected_model"])
        self.assertEqual(result["selection_reason"], "no_vision_model_available")

    def test_base_url_environment_does_not_override_successful_probe(self) -> None:
        result = selector.select_claude_model(
            "provider-current",
            settings_paths=[],
            env={
                "ANTHROPIC_BASE_URL": "https://one-api.example.test",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "provider-haiku",
            },
            probe=lambda model, timeout: model == "provider-current",
        )

        self.assertTrue(result["can_run_visual_review"])
        self.assertEqual(result["selected_model"], "provider-current")
        self.assertEqual(result["selection_reason"], "current_model_supports_image")
        self.assertEqual(
            set(result),
            {
                "runtime",
                "current_model",
                "selected_model",
                "selection_reason",
                "can_run_visual_review",
                "vision_models",
            },
        )

    def test_claude_continues_after_probe_failures_and_records_errors(self) -> None:
        def probe(model: str, timeout: int) -> selector.ProbeResult:
            if model == "bad-current":
                raise OSError("missing cli")
            if model == "api-failure":
                return selector.ProbeResult(False, "api_error")
            return selector.ProbeResult(model == "vision-sonnet", None)

        result = selector.select_claude_model(
            "bad-current",
            settings_paths=[],
            env={
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "api-failure",
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "vision-sonnet",
            },
            probe=probe,
        )

        self.assertTrue(result["can_run_visual_review"])
        self.assertEqual(result["selected_model"], "vision-sonnet")
        self.assertEqual(result["selection_reason"], "first_available_vision_model")
        self.assertEqual(
            result["probe_errors"],
            [
                {"model": "bad-current", "error": "probe_cli_error: missing cli"},
                {"model": "api-failure", "error": "api_error"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
