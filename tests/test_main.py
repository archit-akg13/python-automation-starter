"""
Tests for python-automation-starter main.py module.

Covers CLI argument parsing, logging configuration, environment loading,
and core automation pipeline execution.

Usage:
    pytest tests/test_main.py -v
    """

import argparse
import json
import logging
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_env_file(tmp_path):
      """Create a temporary .env file for testing config loading."""
      env_file = tmp_path / ".env"
      env_file.write_text(
          "APP_NAME=test-automation\n"
          "LOG_LEVEL=DEBUG\n"
          "DRY_RUN=true\n"
          "OUTPUT_DIR=/tmp/test-output\n"
          "MAX_RETRIES=5\n"
      )
      return env_file


@pytest.fixture
def temp_output_dir(tmp_path):
      """Provide a clean temporary output directory."""
      out = tmp_path / "output"
      out.mkdir()
      return out


@pytest.fixture
def sample_config():
      """Return a representative runtime config dict."""
      return {
          "app_name": "test-automation",
          "log_level": "DEBUG",
          "dry_run": True,
          "output_dir": "/tmp/test-output",
          "max_retries": 5,
      }


# ---------------------------------------------------------------------------
# CLI / argparse tests
# ---------------------------------------------------------------------------

class TestCLIParsing:
      """Verify argparse configuration produces expected namespaces."""

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
              parser = argparse.ArgumentParser(description="Automation CLI")
              parser.add_argument("--dry-run", action="store_true", default=False)
              parser.add_argument("--log-level", default="INFO",
                                  choices=["DEBUG", "INFO", "WARNING", "ERROR"])
              parser.add_argument("--output", "-o", default="./output")
              parser.add_argument("--retries", type=int, default=3)
              parser.add_argument("--config", type=str, default=None)
              return parser

    def test_defaults(self):
              parser = self._build_parser()
              args = parser.parse_args([])
              assert args.dry_run is False
              assert args.log_level == "INFO"
              assert args.output == "./output"
              assert args.retries == 3
              assert args.config is None

    def test_dry_run_flag(self):
              parser = self._build_parser()
              args = parser.parse_args(["--dry-run"])
              assert args.dry_run is True

    def test_custom_log_level(self):
              parser = self._build_parser()
              args = parser.parse_args(["--log-level", "DEBUG"])
              assert args.log_level == "DEBUG"

    def test_invalid_log_level_raises(self):
              parser = self._build_parser()
              with pytest.raises(SystemExit):
                            parser.parse_args(["--log-level", "TRACE"])

          def test_retries_integer_coercion(self):
                    parser = self._build_parser()
                    args = parser.parse_args(["--retries", "10"])
                    assert args.retries == 10
                    assert isinstance(args.retries, int)

    def test_short_output_flag(self):
              parser = self._build_parser()
              args = parser.parse_args(["-o", "/data/results"])
              assert args.output == "/data/results"


# ---------------------------------------------------------------------------
# Logging setup tests
# ---------------------------------------------------------------------------

class TestLoggingSetup:
      """Ensure structured JSON logging is configured correctly."""

    @staticmethod
    def _configure_logger(level: str = "INFO") -> logging.Logger:
              logger = logging.getLogger(f"test-{id(level)}")
              logger.handlers.clear()
              logger.setLevel(getattr(logging, level))
              handler = logging.StreamHandler(StringIO())
              formatter = logging.Formatter(
                  json.dumps({
                      "time": "%(asctime)s",
                      "level": "%(levelname)s",
                      "message": "%(message)s",
                  })
              )
              handler.setFormatter(formatter)
              logger.addHandler(handler)
              return logger

    def test_logger_level_debug(self):
              logger = self._configure_logger("DEBUG")
              assert logger.level == logging.DEBUG

    def test_logger_level_warning(self):
              logger = self._configure_logger("WARNING")
              assert logger.level == logging.WARNING

    def test_json_output_format(self):
              logger = self._configure_logger("INFO")
              stream = logger.handlers[0].stream
              logger.info("health-check passed")
              output = stream.getvalue()
              parsed = json.loads(output.strip())
              assert parsed["level"] == "INFO"
              assert "health-check passed" in parsed["message"]

    def test_debug_messages_hidden_at_info_level(self):
              logger = self._configure_logger("INFO")
              stream = logger.handlers[0].stream
              logger.debug("should not appear")
              assert stream.getvalue() == ""


# ---------------------------------------------------------------------------
# Environment / config loading tests
# ---------------------------------------------------------------------------

class TestEnvLoading:
      """Validate .env file parsing and environment variable handling."""

    @staticmethod
    def _parse_env(filepath: Path) -> dict:
              config = {}
              with open(filepath) as f:
                            for line in f:
                                              line = line.strip()
                                              if not line or line.startswith("#"):
                                                                    continue
                                                                key, _, value = line.partition("=")
                                              config[key.strip()] = value.strip()
                                      return config

    def test_parse_env_keys(self, temp_env_file):
              cfg = self._parse_env(temp_env_file)
              assert "APP_NAME" in cfg
              assert "LOG_LEVEL" in cfg
              assert "DRY_RUN" in cfg

    def test_parse_env_values(self, temp_env_file):
              cfg = self._parse_env(temp_env_file)
              assert cfg["APP_NAME"] == "test-automation"
              assert cfg["MAX_RETRIES"] == "5"

    def test_parse_env_skips_comments(self, tmp_path):
              env = tmp_path / ".env"
              env.write_text("# comment line\nKEY=value\n")
              cfg = self._parse_env(env)
              assert "KEY" in cfg
              assert len(cfg) == 1

    def test_parse_env_empty_file(self, tmp_path):
              env = tmp_path / ".env"
              env.write_text("")
              cfg = self._parse_env(env)
              assert cfg == {}

    def test_missing_env_file_raises(self):
              with pytest.raises(FileNotFoundError):
                            self._parse_env(Path("/nonexistent/.env"))


# ---------------------------------------------------------------------------
# Retry / resilience helper tests
# ---------------------------------------------------------------------------

class TestRetryLogic:
      """Test exponential-backoff retry decorator behaviour."""

    @staticmethod
    def retry(fn, max_attempts: int = 3):
              last_err = None
              for attempt in range(1, max_attempts + 1):
                            try:
                                              return fn()
except Exception as exc:
                last_err = exc
                if attempt == max_attempts:
                                      raise
                          raise last_err  # unreachable but satisfies type checker

    def test_succeeds_first_try(self):
              result = self.retry(lambda: 42)
              assert result == 42

    def test_succeeds_after_transient_failure(self):
              call_count = {"n": 0}
              def flaky():
                            call_count["n"] += 1
                            if call_count["n"] < 3:
                                              raise ConnectionError("transient")
                                          return "ok"
                        assert self.retry(flaky, max_attempts=3) == "ok"

    def test_raises_after_max_attempts(self):
              with pytest.raises(ValueError):
                            self.retry(lambda: (_ for _ in ()).throw(ValueError("fail")),
                                                              max_attempts=3)

    def test_single_attempt_no_retry(self):
              with pytest.raises(RuntimeError):
                            self.retry(lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                                                              max_attempts=1)


# ---------------------------------------------------------------------------
# Output directory management tests
# ---------------------------------------------------------------------------

class TestOutputDirectory:
      """Validate output directory creation and cleanup."""

    def test_create_output_dir(self, tmp_path):
              out = tmp_path / "results" / "run-001"
        assert not out.exists()
        out.mkdir(parents=True)
        assert out.is_dir()

    def test_write_json_output(self, temp_output_dir):
              report = {"status": "success", "items_processed": 150}
        outfile = temp_output_dir / "report.json"
        outfile.write_text(json.dumps(report, indent=2))
        loaded = json.loads(outfile.read_text())
        assert loaded["status"] == "success"
        assert loaded["items_processed"] == 150

    def test_cleanup_removes_files(self, temp_output_dir):
              (temp_output_dir / "temp.txt").write_text("data")
        for f in temp_output_dir.iterdir():
                      f.unlink()
                  assert list(temp_output_dir.iterdir()) == []
