"""Select an image-capable model for diagram visual review."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import struct
import subprocess
import uuid
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


Runner = Callable[[list[str], int], "CommandResult"]
Probe = Callable[[str, int], "ProbeResult | bool"]


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass
class ProbeResult:
    supported: bool
    error: str | None = None

    def __bool__(self) -> bool:
        return self.supported


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=["codex", "claude"], required=True)
    parser.add_argument("--current-model", help="Current model slug/name. If omitted, read runtime config.")
    parser.add_argument("--probe-timeout", type=int, default=60, help="Seconds for each Claude image probe")
    return parser.parse_args()


def run_command(command: list[str], timeout: int) -> CommandResult:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=timeout,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def unique_nonempty(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def read_codex_current_model(config_path: Path | None = None) -> str | None:
    env_model = os.environ.get("CODEX_MODEL") or os.environ.get("MODEL")
    if env_model:
        return env_model

    config = config_path or Path.home() / ".codex" / "config.toml"
    if not config.exists():
        return None
    match = re.search(r'(?m)^\s*model\s*=\s*"([^"]+)"', config.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def load_codex_vision_models(runner: Runner = run_command) -> list[dict[str, str]]:
    result = runner(["codex", "debug", "models"], 60)
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    vision_models: list[dict[str, str]] = []
    for model in payload.get("models", []):
        if "image" not in (model.get("input_modalities") or []):
            continue
        slug = model.get("slug")
        if not slug:
            continue
        vision_models.append(
            {
                "slug": slug,
                "display_name": model.get("display_name") or slug,
            }
        )
    return vision_models


def selection_result(
    runtime: str,
    current_model: str | None,
    selected_model: str | None,
    selection_reason: str,
    vision_models: list[str],
    probe_errors: list[dict[str, str]] | None = None,
) -> dict:
    result = {
        "runtime": runtime,
        "current_model": current_model,
        "selected_model": selected_model,
        "selection_reason": selection_reason,
        "can_run_visual_review": selected_model is not None,
        "vision_models": vision_models,
    }
    if probe_errors:
        result["probe_errors"] = probe_errors
    return result


def select_codex_model(current_model: str | None = None, runner: Runner = run_command) -> dict:
    current = current_model or read_codex_current_model()
    models = load_codex_vision_models(runner)
    slugs = [model["slug"] for model in models]
    if current and current in slugs:
        return selection_result("codex", current, current, "current_model_supports_image", slugs)
    if slugs:
        return selection_result("codex", current, slugs[0], "first_available_vision_model", slugs)
    return selection_result("codex", current, None, "no_vision_model_available", [])


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def merge_claude_config(settings_paths: Iterable[Path], env: dict[str, str]) -> tuple[dict, dict[str, str]]:
    config: dict = {}
    merged_env: dict[str, str] = {}
    for path in settings_paths:
        if not path.exists():
            continue
        payload = read_json(path)
        if not config:
            config = payload
        merged_env.update({key: str(value) for key, value in (payload.get("env") or {}).items() if value})
    merged_env.update({key: value for key, value in env.items() if value})
    return config, merged_env


def resolve_claude_alias(model: str | None, config_env: dict[str, str]) -> str | None:
    if not model:
        return None
    aliases = {
        "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    }
    key = aliases.get(model.strip().lower())
    if key and config_env.get(key):
        return config_env[key]
    return model


def claude_candidate_models(
    current_model: str | None,
    settings_paths: Iterable[Path] | None = None,
    env: dict[str, str] | None = None,
) -> tuple[str | None, list[str]]:
    paths = list(settings_paths or [Path.home() / ".claude" / "settings.json"])
    config, config_env = merge_claude_config(paths, dict(os.environ if env is None else env))
    configured_model = config.get("model")
    current = resolve_claude_alias(
        current_model or config_env.get("ANTHROPIC_MODEL") or configured_model,
        config_env,
    )
    candidates = unique_nonempty(
        [
            current,
            config_env.get("ANTHROPIC_MODEL"),
            config_env.get("ANTHROPIC_DEFAULT_HAIKU_MODEL"),
            config_env.get("ANTHROPIC_DEFAULT_SONNET_MODEL"),
            config_env.get("ANTHROPIC_DEFAULT_OPUS_MODEL"),
            resolve_claude_alias(configured_model, config_env),
            configured_model,
        ]
    )
    return current, candidates


def make_probe_png() -> tuple[Path, int, int]:
    """Generate a probe PNG with random dimensions so the model must actually see the image to report them."""
    width = random.randint(32, 60)
    height = random.randint(24, 48)
    png = make_png_bytes(width=width, height=height)
    path = Path.cwd() / f".diagram-vision-probe-{uuid.uuid4().hex}.png"
    path.write_bytes(png)
    return path, width, height


def make_png_bytes(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw_rows = b"".join(b"\x00" + (b"\xff\x00\x00" * width) for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw_rows)) + chunk(b"IEND", b"")


def probe_claude_image_support(model: str, timeout: int = 60) -> ProbeResult:
    png_path, expected_width, expected_height = make_probe_png()
    image_ref = png_path.name if png_path.parent == Path.cwd() else str(png_path)
    prompt = (
        f"Inspect this local PNG image: @{image_ref}. "
        "Look at the actual image pixels and report its dimensions. "
        "Reply with exactly one line in this format: PROBE_W_<number>_H_<number> "
        "where the numbers are the image width and height in pixels you see. "
        "If you cannot inspect the image at all, reply exactly VISION_UNSUPPORTED. "
        "Do not guess."
    )
    command = [
        "claude",
        "-p",
        "--model",
        model,
        "--output-format",
        "json",
        "--permission-mode",
        "bypassPermissions",
        "--no-session-persistence",
        prompt,
    ]
    try:
        result = run_command(command, timeout)
    except subprocess.TimeoutExpired:
        return ProbeResult(False, "probe_timeout")
    except OSError as exc:
        return ProbeResult(False, f"probe_cli_error: {exc}")
    finally:
        try:
            png_path.unlink()
        except OSError:
            pass
    output = f"{result.stdout}\n{result.stderr}"
    # Detect API errors — covers both Anthropic and DashScope-compatible proxy errors
    if "API Error" in output or "InvalidParameter" in output or "Unexpected item type" in output:
        return ProbeResult(False, "api_error")
    if result.returncode != 0:
        return ProbeResult(False, f"probe_exit_{result.returncode}")
    # Content-based verification: the model must report the correct dimensions
    match = re.search(r"PROBE_W_(\d+)_H_(\d+)", output)
    if match:
        reported_w, reported_h = int(match.group(1)), int(match.group(2))
        if reported_w == expected_width and reported_h == expected_height:
            return ProbeResult(True)
        return ProbeResult(False, f"dimension_mismatch: expected {expected_width}x{expected_height}, got {reported_w}x{reported_h}")
    if "VISION_UNSUPPORTED" in output:
        return ProbeResult(False, "vision_unsupported")
    return ProbeResult(False, "unparseable_response")


def normalize_probe_result(model: str, raw_result: ProbeResult | bool) -> ProbeResult:
    if isinstance(raw_result, ProbeResult):
        return raw_result
    return ProbeResult(bool(raw_result), None if raw_result else "probe_failed")


def select_claude_model(
    current_model: str | None = None,
    settings_paths: Iterable[Path] | None = None,
    env: dict[str, str] | None = None,
    probe: Probe = probe_claude_image_support,
    probe_timeout: int = 60,
) -> dict:
    current, candidates = claude_candidate_models(current_model, settings_paths, env)
    vision_models: list[str] = []
    probe_errors: list[dict[str, str]] = []
    for candidate in candidates:
        try:
            probe_result = normalize_probe_result(candidate, probe(candidate, probe_timeout))
        except subprocess.TimeoutExpired:
            probe_result = ProbeResult(False, "probe_timeout")
        except OSError as exc:
            probe_result = ProbeResult(False, f"probe_cli_error: {exc}")
        except Exception as exc:
            probe_result = ProbeResult(False, f"probe_error: {exc}")

        if not probe_result.supported:
            if probe_result.error:
                probe_errors.append({"model": candidate, "error": probe_result.error})
            continue
        vision_models.append(candidate)
        if current and candidate == current:
            return selection_result("claude", current, current, "current_model_supports_image", vision_models, probe_errors)

    if vision_models:
        return selection_result("claude", current, vision_models[0], "first_available_vision_model", vision_models, probe_errors)
    return selection_result("claude", current, None, "no_vision_model_available", [], probe_errors)


def main() -> int:
    args = parse_args()

    if args.runtime == "codex":
        result = select_codex_model(args.current_model)
    else:
        result = select_claude_model(args.current_model, probe_timeout=args.probe_timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
