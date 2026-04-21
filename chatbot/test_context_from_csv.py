import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from main import detect_faq
from utils import init, preprocess_user_input


CSV_PATH = Path("data/faq_fixed.csv")
REPORT_PATH = Path("logs/context_from_csv_report.json")

# Group intents that are semantically close for lenient evaluation.
INTENT_GROUPS = {
    "kontak_layanan": {"kontak_resmi", "pengaduan_layanan"},
    "jatuh_tempo": {"jatuh_tempo_umum", "jatuh_tempo_restoran"},
    "sanksi_denda": {"sanksi", "denda", "pbb_denda"},
    "bayar_info": {"bayar_pajak", "cara_bayar_umum"},
    "pbb_permohonan": {"syarat_permohonan_pbb", "standar_pelayanan_pbb"},
    "syarat_umum_hrh": {"syarat_permohonan_umum", "syarat_permohonan_hrh"},
}

INTENT_TO_GROUP = {}
for group_name, intents in INTENT_GROUPS.items():
    for intent_name in intents:
        INTENT_TO_GROUP[intent_name] = group_name


def canonical_intent(intent: str) -> str:
    return INTENT_TO_GROUP.get(intent, intent)


@dataclass
class RowResult:
    intent: str
    question: str
    normalized: str
    predicted: str
    score: float
    passed: bool


def load_dataset(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            intent = (row.get("intent") or "").strip()
            question = (row.get("question") or "").strip()
            if not intent or not question:
                continue
            rows.append({"intent": intent, "question": question})
    return rows


def evaluate_rows(rows: List[Dict[str, str]]) -> List[RowResult]:
    results: List[RowResult] = []
    for row in rows:
        normalized = preprocess_user_input(row["question"])
        predicted, _, score = detect_faq(normalized)
        expected = row["intent"]
        canonical_expected = canonical_intent(expected)
        canonical_predicted = canonical_intent(predicted or "NONE")
        results.append(
            RowResult(
                intent=expected,
                question=row["question"],
                normalized=normalized,
                predicted=predicted or "NONE",
                score=float(score),
                passed=(canonical_expected == canonical_predicted),
            )
        )
    return results


def summarize(results: List[RowResult]) -> Dict:
    by_intent: Dict[str, List[RowResult]] = defaultdict(list)
    for item in results:
        by_intent[item.intent].append(item)

    intent_summary = {}
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    for intent, rows in sorted(by_intent.items(), key=lambda x: x[0]):
        i_total = len(rows)
        i_passed = sum(1 for r in rows if r.passed)
        i_failed = i_total - i_passed
        intent_summary[intent] = {
            "total": i_total,
            "passed": i_passed,
            "failed": i_failed,
            "accuracy": (i_passed / i_total * 100.0) if i_total else 0.0,
        }

    mismatches = [
        {
            "intent": r.intent,
            "question": r.question,
            "normalized": r.normalized,
            "predicted": r.predicted,
            "score": r.score,
        }
        for r in results
        if not r.passed
    ]

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "accuracy": (passed / total * 100.0) if total else 0.0,
        "by_intent": intent_summary,
        "mismatches": mismatches,
    }


def print_console_report(summary: Dict, top_fail: int) -> None:
    print("=== CSV Context Test (User Questions) ===")
    print(
        f"Overall: {summary['passed']}/{summary['total']} "
        f"({summary['accuracy']:.2f}%)"
    )
    print("\nPer intent:")
    for intent, stats in summary["by_intent"].items():
        print(
            f"- {intent:<28} "
            f"{stats['passed']}/{stats['total']} ({stats['accuracy']:.2f}%)"
        )

    if summary["mismatches"]:
        print(f"\nTop {min(top_fail, len(summary['mismatches']))} mismatches:")
        for row in summary["mismatches"][:top_fail]:
            print(
                f"- q='{row['question']}' | expected={row['intent']} "
                f"| got={row['predicted']} | score={row['score']:.3f}"
            )
    else:
        print("\nNo mismatches.")


def main():
    parser = argparse.ArgumentParser(
        description="Test all contexts/intents from data/faq_fixed.csv using user questions."
    )
    parser.add_argument(
        "--csv",
        default=str(CSV_PATH),
        help="Path to FAQ CSV file (default: data/faq_fixed.csv)",
    )
    parser.add_argument(
        "--report",
        default=str(REPORT_PATH),
        help="Output JSON report path (default: logs/context_from_csv_report.json)",
    )
    parser.add_argument(
        "--top-fail",
        type=int,
        default=30,
        help="How many mismatch rows to print in console (default: 30)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    init()
    rows = load_dataset(csv_path)
    results = evaluate_rows(rows)
    summary = summarize(results)

    report_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print_console_report(summary, top_fail=args.top_fail)
    print(f"\nJSON report saved to: {report_path}")


if __name__ == "__main__":
    main()
