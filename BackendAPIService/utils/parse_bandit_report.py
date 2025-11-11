#!/usr/bin/env python3
"""
Utility: Parse Bandit JSON report and print:
- Counts per severity and per confidence
- Top rules triggering (by test_id) with counts
- Remaining issues: file path, line, severity, confidence, test_id, message, link

Usage:
  python utils/parse_bandit_report.py reports/bandit_report.json
  python utils/parse_bandit_report.py security-reports/bandit-report.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_report(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        print("Usage: python utils/parse_bandit_report.py <path-to-bandit-json>", file=sys.stderr)
        sys.exit(2)

    report_path = Path(sys.argv[1])
    if not report_path.exists():
        print(f"Error: report not found at {report_path}", file=sys.stderr)
        sys.exit(1)

    data = load_report(report_path)

    results = data.get("results", [])
    metrics = data.get("metrics", {})
    errors = data.get("errors", [])

    # Aggregate by severity and confidence
    sev_counter = Counter()
    conf_counter = Counter()
    rule_counter = Counter()
    per_rule_sev = defaultdict(Counter)

    for r in results:
        sev = r.get("issue_severity", "UNDEFINED")
        conf = r.get("issue_confidence", "UNDEFINED")
        test_id = r.get("test_id", "UNKNOWN")
        sev_counter[sev] += 1
        conf_counter[conf] += 1
        rule_counter[test_id] += 1
        per_rule_sev[test_id][sev] += 1

    # Output summary
    print("Bandit report summary")
    print(f"Report file: {report_path}")
    print(f"Generated at: {data.get('generated_at','<unknown>')}")
    print("")

    print("Counts by severity:")
    for sev in ["HIGH", "MEDIUM", "LOW", "UNDEFINED"]:
        print(f"  {sev}: {sev_counter.get(sev, 0)}")
    print("")

    print("Counts by confidence:")
    for conf in ["HIGH", "MEDIUM", "LOW", "UNDEFINED"]:
        print(f"  {conf}: {conf_counter.get(conf, 0)}")
    print("")

    # Top rules
    print("Top rules triggering:")
    for test_id, cnt in rule_counter.most_common():
        sev_breakdown = ", ".join(f"{k}:{v}" for k, v in per_rule_sev[test_id].items())
        print(f"  {test_id}: {cnt} ({sev_breakdown})")
    if not rule_counter:
        print("  <no issues>")
    print("")

    # Detailed issues
    print("Remaining issues:")
    if not results:
        print("  <no issues>")
    else:
        for r in results:
            filename = r.get("filename")
            line = r.get("line_number")
            sev = r.get("issue_severity")
            conf = r.get("issue_confidence")
            test_id = r.get("test_id")
            name = r.get("test_name")
            msg = r.get("issue_text")
            more = r.get("more_info")
            print(f"- {filename}:{line} [{sev}/{conf}] {test_id} ({name}) - {msg}")
            if more:
                print(f"  More info: {more}")

    # Errors section if any
    if errors:
        print("")
        print("Bandit scanner errors:")
        for e in errors:
            print(f"  - {e}")

    # Metrics note
    if metrics:
        app_files = [k for k in metrics.keys() if k.startswith("./app/")]
        if app_files:
            print("")
            print("Note: Metrics indicate which files were scanned in ./app/*")

if __name__ == "__main__":
    main()
