import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple

from main import chat, reset_context, detect_faq
from utils import preprocess_user_input, init


@dataclass
class IntentCase:
    text: str
    expected_intent: str


@dataclass
class FlowStep:
    user_id: str
    message: str
    must_contain: List[str]


@dataclass
class FlowCase:
    name: str
    steps: List[FlowStep]


def contains_all(text: str, needles: List[str]) -> bool:
    lower = text.lower()
    return all(n.lower() in lower for n in needles)


def run_intent_suite(name: str, cases: List[IntentCase]) -> Dict:
    passed = 0
    details = []
    for case in cases:
        normalized = preprocess_user_input(case.text)
        pred, _, score = detect_faq(normalized)
        ok = pred == case.expected_intent
        if ok:
            passed += 1
        details.append(
            {
                "text": case.text,
                "normalized": normalized,
                "expected": case.expected_intent,
                "predicted": pred,
                "score": float(score),
                "pass": ok,
            }
        )
    total = len(cases)
    return {
        "suite": name,
        "passed": passed,
        "total": total,
        "accuracy": (passed / total * 100.0) if total else 0.0,
        "details": details,
    }


def run_flow_suite(cases: List[FlowCase]) -> Dict:
    passed_steps = 0
    total_steps = 0
    scenario_passed = 0
    details = []

    used_users = sorted({step.user_id for c in cases for step in c.steps})
    for uid in used_users:
        reset_context(uid)

    for case in cases:
        scenario_ok = True
        scenario_steps = []
        for step in case.steps:
            total_steps += 1
            reply = chat(step.user_id, step.message)
            ok = contains_all(reply, step.must_contain)
            if ok:
                passed_steps += 1
            else:
                scenario_ok = False
            scenario_steps.append(
                {
                    "user_id": step.user_id,
                    "message": step.message,
                    "must_contain": step.must_contain,
                    "reply": reply,
                    "pass": ok,
                }
            )
        if scenario_ok:
            scenario_passed += 1
        details.append(
            {
                "scenario": case.name,
                "pass": scenario_ok,
                "steps": scenario_steps,
            }
        )

    for uid in used_users:
        reset_context(uid)

    return {
        "suite": "conversation_flow",
        "scenario_passed": scenario_passed,
        "scenario_total": len(cases),
        "step_passed": passed_steps,
        "step_total": total_steps,
        "scenario_accuracy": (scenario_passed / len(cases) * 100.0) if cases else 0.0,
        "step_accuracy": (passed_steps / total_steps * 100.0) if total_steps else 0.0,
        "details": details,
    }


def build_suites() -> Tuple[List[IntentCase], List[IntentCase], List[FlowCase]]:
    faq_cases = [
        IntentCase("apa itu bapenda medan", "apa_itu_bapenda"),
        IntentCase("jam pelayanan bapenda kapan", "jam_layanan"),
        IntentCase("alamat kantor bapenda dimana", "alamat_kantor"),
        IntentCase("kontak resmi bapenda medan", "kontak_resmi"),
        IntentCase("jenis pajak daerah apa saja", "jenis_pajak"),
        IntentCase("siapa wajib pajak", "wajib_pajak"),
        IntentCase("kapan jatuh tempo pajak daerah", "jatuh_tempo_umum"),
        IntentCase("cek tagihan pbb dimana", "pbb_cek_tagihan"),
        IntentCase("denda pbb berapa", "pbb_denda"),
        IntentCase("cara mutasi pbb", "pbb_mutasi"),
        IntentCase("cara bayar pajak daerah", "cara_bayar_umum"),
        IntentCase("cara bayar pbb", "cara_bayar_pbb"),
        IntentCase("bayar pajak online lewat apa", "bayar_online"),
        IntentCase("apa itu pajak restoran", "pajak_restoran"),
        IntentCase("apa itu pajak hotel", "pajak_hotel"),
        IntentCase("apa itu pajak hiburan", "pajak_hiburan"),
        IntentCase("mau bayar pajak", "bayar_pajak"),
        IntentCase("call center pbb berapa", "call_center_pbb"),
        IntentCase("call center bphtb berapa", "call_center_bphtb"),
        IntentCase("syarat permohonan bphtb apa", "syarat_permohonan_bphtb"),
        IntentCase("gimana cara daftar pajak restoran", "syarat_permohonan_hrh"),
    ]

    typo_cases = [
        IntentCase("jem berpaa bapenda buka", "jam_layanan"),
        IntentCase("gmn cekk pbb onlen", "pbb_cek_tagihan"),
        IntentCase("brp dnda pbb klu telatt", "pbb_denda"),
        IntentCase("mau byr pjk restoran", "bayar_pajak"),
        IntentCase("nomer cs bphtb berpa", "call_center_bphtb"),
        IntentCase("jam puasa bapenda buka kapan", "jam_layanan"),
    ]

    flow_cases = [
        FlowCase(
            name="pbb_happy_path",
            steps=[
                FlowStep("u_pbb", "mau bayar pbb", ["nomor objek pajak", "nop"]),
                FlowStep("u_pbb", "123456789012345678", ["nop anda", "masukkan nik"]),
                FlowStep("u_pbb", "1234567890123456", ["masukkan tahun pajak"]),
                FlowStep("u_pbb", "2024", ["apakah data sudah benar"]),
                FlowStep("u_pbb", "ya", ["https://pajak.medan.go.id/bayar/pbb"]),
            ],
        ),
        FlowCase(
            name="nonpbb_happy_path_restoran",
            steps=[
                FlowStep("u_nonpbb", "aku mau bayar pajak restoran", ["nomor pokok wajib pajak daerah", "npwpd"]),
                FlowStep("u_nonpbb", "1234567890123456", ["npwpd anda", "masukkan nik/nib"]),
                FlowStep("u_nonpbb", "1234567890123456", ["masa pajak", "bulan-tahun"]),
                FlowStep("u_nonpbb", "04-2025", ["apakah data sudah benar"]),
                FlowStep("u_nonpbb", "ya", ["https://pajak.medan.go.id/bayar/nonpbb"]),
            ],
        ),
        FlowCase(
            name="cancel_mid_flow",
            steps=[
                FlowStep("u_cancel", "bayar pbb", ["nomor objek pajak"]),
                FlowStep("u_cancel", "batal", ["transaksi dibatalkan"]),
            ],
        ),
        FlowCase(
            name="ambiguous_tax_selection",
            steps=[
                FlowStep("u_amb", "saya mau bayar pajak", ["mau bayar pajak apa"]),
                FlowStep("u_amb", "restoran dan hotel", ["satu pajak", "pilih salah satu"]),
            ],
        ),
        FlowCase(
            name="interleaved_context_two_users",
            steps=[
                FlowStep("u_a", "bayar pbb", ["nomor objek pajak"]),
                FlowStep("u_b", "bayar pajak restoran", ["npwpd"]),
                FlowStep("u_a", "123456789012345678", ["nop anda"]),
                FlowStep("u_b", "1234567890123456", ["npwpd anda"]),
            ],
        ),
    ]
    return faq_cases, typo_cases, flow_cases


def print_summary(intent_report: Dict, typo_report: Dict, flow_report: Dict):
    print("=== Chatbot Accuracy Report ===")
    print(f"FAQ Intent Accuracy      : {intent_report['passed']}/{intent_report['total']} ({intent_report['accuracy']:.2f}%)")
    print(f"Typo/Slang Accuracy      : {typo_report['passed']}/{typo_report['total']} ({typo_report['accuracy']:.2f}%)")
    print(
        "Flow Scenario Accuracy   : "
        f"{flow_report['scenario_passed']}/{flow_report['scenario_total']} ({flow_report['scenario_accuracy']:.2f}%)"
    )
    print(
        "Flow Step Accuracy       : "
        f"{flow_report['step_passed']}/{flow_report['step_total']} ({flow_report['step_accuracy']:.2f}%)"
    )

    overall_total = intent_report["total"] + typo_report["total"] + flow_report["step_total"]
    overall_pass = intent_report["passed"] + typo_report["passed"] + flow_report["step_passed"]
    overall_acc = (overall_pass / overall_total * 100.0) if overall_total else 0.0
    print(f"Overall Weighted Accuracy: {overall_pass}/{overall_total} ({overall_acc:.2f}%)")


def save_report(report: Dict):
    out_path = Path("logs/context_accuracy_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDetail report saved to: {out_path}")


if __name__ == "__main__":
    init()
    faq_cases, typo_cases, flow_cases = build_suites()

    intent_report = run_intent_suite("faq_intent", faq_cases)
    typo_report = run_intent_suite("typo_slang_intent", typo_cases)
    flow_report = run_flow_suite(flow_cases)

    final_report = {
        "faq_intent": intent_report,
        "typo_slang_intent": typo_report,
        "conversation_flow": flow_report,
    }

    print_summary(intent_report, typo_report, flow_report)

    # Print failed rows quickly for inspection.
    failed_intents = [d for d in intent_report["details"] if not d["pass"]]
    failed_typos = [d for d in typo_report["details"] if not d["pass"]]
    failed_flow_steps = [
        step
        for sc in flow_report["details"]
        for step in sc["steps"]
        if not step["pass"]
    ]

    if failed_intents:
        print("\nFailed FAQ Intent Cases:")
        for row in failed_intents:
            print(f"- {row['text']} -> expected={row['expected']} got={row['predicted']} score={row['score']:.3f}")
    if failed_typos:
        print("\nFailed Typo/Slang Cases:")
        for row in failed_typos:
            print(f"- {row['text']} -> expected={row['expected']} got={row['predicted']} score={row['score']:.3f}")
    if failed_flow_steps:
        print("\nFailed Flow Steps:")
        for row in failed_flow_steps:
            print(f"- user={row['user_id']} msg='{row['message']}'")
            print(f"  expected contains: {row['must_contain']}")
            print(f"  got: {row['reply']}")

    save_report(final_report)
