#!/usr/bin/env python3
"""Python Automation Starter - Production-ready CLI boilerplate."""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

try:
      from dotenv import load_dotenv
      load_dotenv()
except ImportError:
      pass


class JsonFormatter(logging.Formatter):
      """Structured JSON log formatter for production use."""
      def format(self, record):
                return json.dumps({
                              "ts": datetime.utcnow().isoformat() + "Z",
                              "level": record.levelname,
                              "msg": record.getMessage(),
                              "module": record.module,
                })


def setup_logging(level="INFO", json_out=False):
      logger = logging.getLogger("automation")
      logger.setLevel(getattr(logging, level.upper(), logging.INFO))
      h = logging.StreamHandler(sys.stdout)
      if json_out:
                h.setFormatter(JsonFormatter())
else:
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
      logger.addHandler(h)
    return logger


class Config:
      """Load config from environment variables."""
      def __init__(self):
                self.app_name = os.getenv("APP_NAME", "automation-starter")
                self.log_level = os.getenv("LOG_LEVEL", "INFO")
                self.json_logs = os.getenv("JSON_LOGS", "false").lower() == "true"
                self.data_dir = Path(os.getenv("DATA_DIR", "./data"))
                self.output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))

      def ensure_dirs(self):
                self.data_dir.mkdir(parents=True, exist_ok=True)
                self.output_dir.mkdir(parents=True, exist_ok=True)


def cmd_greet(args, config, logger):
      name = args.name or "World"
      logger.info(f"Greeting: {name}")
      print(f"Hello, {name}! Automation starter is working.")


def cmd_process(args, config, logger):
      input_path = Path(args.input)
      if not input_path.exists():
                logger.error(f"Not found: {input_path}")
                sys.exit(1)
            if args.dry_run:
                      logger.info(f"[DRY RUN] Would process: {input_path}")
                      return
                  config.ensure_dirs()
    lines = input_path.read_text().splitlines()
    out = config.output_dir / f"result_{datetime.now():%Y%m%d_%H%M%S}.txt"
    out.write_text(f"Processed {len(lines)} lines from {input_path.name}\n")
    logger.info(f"Done: {out}")


def main():
      parser = argparse.ArgumentParser(prog="automation-starter")
    parser.add_argument("--log-level", default=None)
    parser.add_argument("--json-logs", action="store_true")
    subs = parser.add_subparsers(dest="command")

    g = subs.add_parser("greet", help="Test greeting")
    g.add_argument("--name", default=None)

    p = subs.add_parser("process", help="Process a file")
    p.add_argument("--input", required=True)
    p.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    config = Config()
    if args.log_level:
              config.log_level = args.log_level
          logger = setup_logging(config.log_level, args.json_logs)

    cmds = {"greet": cmd_greet, "process": cmd_process}
    if args.command in cmds:
              cmds[args.command](args, config, logger)
else:
        parser.print_help()


if __name__ == "__main__":
      main()
