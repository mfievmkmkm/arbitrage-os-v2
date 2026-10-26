"""Scan reachable Git history, or the index, without printing matched credential values.
High-confidence pattern check plus filename checks; not a claim to detect every possible secret.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path

PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "telegram_bot_token": re.compile(r"\b[0-9]{7,12}:[A-Za-z0-9_-]{30,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "credential_url": re.compile(r"(?:postgres(?:ql)?|https?)://[^\s:/]+:[^\s@]+@"),
}


def scan(text, path):
    findings = []
    if (Path(path).name.startswith(".env") and Path(path).name != ".env.example") or path.endswith(
        (".pem", ".key")
    ):
        findings.append("sensitive_filename")
    for rule, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group()
            # Exactly documented non-production fixtures; no broad directory exemption.
            if rule == "credential_url" and (
                value == "postgresql://scanner:${POSTGRES_PASSWORD}@"
                or (path == ".github/workflows/ci.yml" and value == "postgresql://scanner:" + "ci-only@")
            ):
                continue
            findings.append(rule)
    return sorted(set(findings))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    def git(*cmd):
        return subprocess.check_output(["git", *cmd], cwd=root)

    refs = git("rev-list", "--all").decode().splitlines() if args.history else [None]
    checked, paths, findings = set(), set(), []
    for ref in refs:
        listing = git("ls-tree", "-rz", ref) if ref else git("ls-files", "--stage", "-z")
        for entry in listing.decode().strip("\0").split("\0"):
            if not entry:
                continue
            metadata, path = entry.split("\t", 1)
            sha = metadata.split()[2] if ref else metadata.split()[1]
            paths.add(path)
            key = sha, path
            if key in checked:
                continue
            checked.add(key)
            content = git("cat-file", "blob", sha).decode(errors="replace")
            findings.extend({"path": path, "rule": rule} for rule in scan(content, path))
    print(
        json.dumps(
            {
                "refs_scanned": len(refs),
                "paths": len(paths),
                "blobs_checked": len(checked),
                "findings": findings,
                "limitation": "HIGH_CONFIDENCE_PATTERNS_NOT_EXHAUSTIVE",
            },
            indent=2,
        )
    )
    raise SystemExit(bool(findings))


if __name__ == "__main__":
    main()
