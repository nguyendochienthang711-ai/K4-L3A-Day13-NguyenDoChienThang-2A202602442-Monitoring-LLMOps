import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

LOG_PATH = Path("data/logs.jsonl")
OUT_PATH = Path("submission/evidence/11-dashboard-overview.png")

def main():
    if not LOG_PATH.exists():
        print(f"Error: {LOG_PATH} not found.")
        return

    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    req_events = [r for r in records if r.get("event") == "request_received"]
    resp_events = [r for r in records if r.get("event") == "response_sent"]
    failed_events = [r for r in records if r.get("event") == "request_failed"]

    latencies = [r["latency_ms"] for r in resp_events if "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in resp_events if "ttft_ms" in r]
    tokens_in = sum(r.get("tokens_in", 0) for r in resp_events)
    tokens_out = sum(r.get("tokens_out", 0) for r in resp_events)
    costs = [r.get("cost_usd", 0.0) for r in resp_events]
    total_cost = sum(costs)
    qualities = [r.get("quality_score", 0.0) for r in resp_events]
    mean_quality = np.mean(qualities) if qualities else 0.0

    p50 = np.percentile(latencies, 50) if latencies else 0
    p95 = np.percentile(latencies, 95) if latencies else 0
    p99 = np.percentile(latencies, 99) if latencies else 0
    ttft_p95 = np.percentile(ttfts, 95) if ttfts else 0

    total_req = len(req_events)
    total_fail = len(failed_events)
    error_rate = (total_fail / total_req * 100) if total_req else 0.0
    retrieval_success = sum(1 for r in resp_events if r.get("tool_success") is True)
    retrieval_rate = (retrieval_success / len(resp_events) * 100) if resp_events else 100.0

    fig, axes = plt.subplots(2, 3, figsize=(16, 9), facecolor="#0f172a")
    plt.subplots_adjust(hspace=0.35, wspace=0.25)
    
    title_font = {"fontsize": 13, "fontweight": "bold", "color": "#38bdf8"}
    label_font = {"fontsize": 10, "color": "#94a3b8"}
    
    for ax in axes.flat:
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="#cbd5e1", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#334155")
        ax.grid(color="#334155", linestyle="--", linewidth=0.5, alpha=0.7)

    # Panel 1: Latency & TTFT
    ax1 = axes[0, 0]
    metrics = ["P50", "P95", "P99", "TTFT P95"]
    vals = [p50, p95, p99, ttft_p95]
    bars = ax1.bar(metrics, vals, color=["#38bdf8", "#818cf8", "#f43f5e", "#fbbf24"], width=0.55)
    ax1.axhline(3000, color="#ef4444", linestyle="--", linewidth=1.5, label="SLO Threshold: 3000ms")
    ax1.set_title("1. Latency Percentiles & TTFT (ms)", **title_font)
    ax1.set_ylabel("Milliseconds", **label_font)
    ax1.legend(loc="upper left", facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1", fontsize=8)
    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, yval + 15, f"{yval:.1f}ms", ha="center", va="bottom", color="#f8fafc", fontsize=9, fontweight="bold")
    ax1.set_ylim(0, max(3500, max(vals)*1.2 if vals else 3500))

    # Panel 2: Traffic
    ax2 = axes[0, 1]
    req_counts = [len(resp_events)]
    ax2.bar(["Current Window"], req_counts, color="#34d399", width=0.4)
    ax2.axhline(1, color="#f59e0b", linestyle="--", linewidth=1.5, label="Threshold: >=1 req/min")
    ax2.set_title("2. Request Traffic (req/window)", **title_font)
    ax2.set_ylabel("Requests", **label_font)
    ax2.legend(loc="upper left", facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1", fontsize=8)
    ax2.text(0, req_counts[0] + 0.3, f"{req_counts[0]} reqs", ha="center", va="bottom", color="#f8fafc", fontsize=10, fontweight="bold")
    ax2.set_ylim(0, max(15, req_counts[0]*1.4))

    # Panel 3: Errors & Retrieval Success
    ax3 = axes[0, 2]
    cat = ["Error Rate %", "Retrieval Success %"]
    rates = [error_rate, retrieval_rate]
    bars3 = ax3.bar(cat, rates, color=["#f43f5e", "#10b981"], width=0.45)
    ax3.axhline(2, color="#ef4444", linestyle="--", linewidth=1.2, label="Error Max: 2%")
    ax3.axhline(90, color="#10b981", linestyle=":", linewidth=1.2, label="Retrieval Min: 90%")
    ax3.set_title("3. Error Rate & Retrieval Success (%)", **title_font)
    ax3.set_ylabel("Percent (%)", **label_font)
    ax3.legend(loc="center right", facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1", fontsize=8)
    for bar in bars3:
        y = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2, y + 2, f"{y:.1f}%", ha="center", va="bottom", color="#f8fafc", fontsize=9, fontweight="bold")
    ax3.set_ylim(0, 115)

    # Panel 4: Cost
    ax4 = axes[1, 0]
    ax4.bar(["Total Cost"], [total_cost], color="#a78bfa", width=0.4)
    ax4.axhline(2.5, color="#f43f5e", linestyle="--", linewidth=1.5, label="Threshold: <=$2.50")
    ax4.set_title("4. Cost (USD)", **title_font)
    ax4.set_ylabel("USD ($)", **label_font)
    ax4.legend(loc="upper right", facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1", fontsize=8)
    ax4.text(0, total_cost + 0.05, f"${total_cost:.5f}", ha="center", va="bottom", color="#f8fafc", fontsize=10, fontweight="bold")
    ax4.set_ylim(0, 3.0)

    # Panel 5: Tokens
    ax5 = axes[1, 1]
    tok_types = ["Tokens In", "Tokens Out", "Total Tokens"]
    tok_vals = [tokens_in, tokens_out, tokens_in + tokens_out]
    bars5 = ax5.bar(tok_types, tok_vals, color=["#38bdf8", "#818cf8", "#c084fc"], width=0.5)
    ax5.axhline(50000, color="#ef4444", linestyle="--", linewidth=1.5, label="Threshold: <=50,000")
    ax5.set_title("5. Input & Output Tokens", **title_font)
    ax5.set_ylabel("Tokens Count", **label_font)
    ax5.legend(loc="upper right", facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1", fontsize=8)
    for bar in bars5:
        y = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2, y + 100, f"{int(y)}", ha="center", va="bottom", color="#f8fafc", fontsize=9, fontweight="bold")
    ax5.set_ylim(0, max(55000, max(tok_vals)*1.3 if tok_vals else 55000))

    # Panel 6: Quality
    ax6 = axes[1, 2]
    ax6.bar(["Quality Proxy"], [mean_quality], color="#fbbf24", width=0.4)
    ax6.axhline(0.75, color="#10b981", linestyle="--", linewidth=1.5, label="Threshold: >=0.75")
    ax6.set_title("6. Quality Score (0 to 1)", **title_font)
    ax6.set_ylabel("Score (0.0 - 1.0)", **label_font)
    ax6.legend(loc="upper right", facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1", fontsize=8)
    ax6.text(0, mean_quality + 0.03, f"{mean_quality:.2f}", ha="center", va="bottom", color="#f8fafc", fontsize=10, fontweight="bold")
    ax6.set_ylim(0, 1.15)

    plt.suptitle("K4-L3A Day 13 Monitoring & LLMOps — Runtime Dashboard Overview\nProject: day13-k4-l3a-2A202602442 | Window: 60m", fontsize=16, fontweight="bold", color="#f8fafc", y=0.98)
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PATH, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Successfully generated dashboard image: {OUT_PATH}")

if __name__ == "__main__":
    main()
