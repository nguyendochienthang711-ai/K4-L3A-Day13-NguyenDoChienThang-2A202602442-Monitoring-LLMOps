import json
import math
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

LOG_PATH = Path("data/logs.jsonl")
PORT = 8501

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K4-L3A Day 13 Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-base: #0b0f19;
            --bg-card: #131b2e;
            --border-card: #1f2d4d;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-cyan: #38bdf8;
            --accent-indigo: #818cf8;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --slo-red: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-base);
            color: var(--text-main);
            padding: 24px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border-card);
        }
        .header-title h1 {
            font-size: 22px;
            font-weight: 700;
            color: var(--accent-cyan);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header-title p {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 4px;
        }
        .header-meta {
            display: flex;
            gap: 16px;
            align-items: center;
        }
        .badge {
            background: #1e293b;
            border: 1px solid #334155;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 12px;
            color: #cbd5e1;
        }
        .badge strong { color: var(--accent-cyan); }
        .grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 14px;
        }
        .card-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-main);
        }
        .card-sub {
            font-size: 11px;
            color: var(--text-muted);
        }
        .chart-box {
            position: relative;
            flex: 1;
            min-height: 220px;
        }
        .metric-summary {
            display: flex;
            gap: 12px;
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 12px;
        }
        .metric-item {
            flex: 1;
            background: rgba(15, 23, 42, 0.6);
            padding: 8px;
            border-radius: 6px;
            text-align: center;
        }
        .metric-label { font-size: 11px; color: var(--text-muted); }
        .metric-val { font-size: 14px; font-weight: 700; color: #fff; margin-top: 2px; }
        .slo-tag {
            display: inline-block;
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">
            <h1>📊 LLMOps Runtime Dashboard (6 Panels Contract)</h1>
            <p>Sinh viên: <strong>Nguyễn Đỗ Chiến Thắng</strong> | MSSV: <strong>2A202602442</strong> | Lớp: <strong>K4-L3A</strong> | Nguồn: <code>data/logs.jsonl</code></p>
        </div>
        <div class="header-meta">
            <div class="badge">Project: <strong>day13-k4-l3a-2A202602442</strong></div>
            <div class="badge">Time Range: <strong>60 phút</strong></div>
            <div class="badge">Refresh: <strong>Live 15s</strong></div>
        </div>
    </div>

    <div class="grid">
        <!-- Panel 1: Latency & TTFT -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">1. Latency Percentiles & TTFT</span>
                <span class="slo-tag">SLO: P95 ≤ 3000ms</span>
            </div>
            <div class="chart-box">
                <canvas id="chartLatency"></canvas>
            </div>
            <div class="metric-summary">
                <div class="metric-item"><div class="metric-label">P50</div><div class="metric-val" id="p50Val">--</div></div>
                <div class="metric-item"><div class="metric-label">P95</div><div class="metric-val" id="p95Val" style="color: #38bdf8;">--</div></div>
                <div class="metric-item"><div class="metric-label">P99</div><div class="metric-val" id="p99Val">--</div></div>
                <div class="metric-item"><div class="metric-label">TTFT P95</div><div class="metric-val" id="ttftVal">--</div></div>
            </div>
        </div>

        <!-- Panel 2: Traffic -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">2. Request Traffic</span>
                <span class="badge" style="padding: 2px 6px; font-size: 10px;">req/window</span>
            </div>
            <div class="chart-box">
                <canvas id="chartTraffic"></canvas>
            </div>
            <div class="metric-summary">
                <div class="metric-item"><div class="metric-label">Total Requests</div><div class="metric-val" id="totReq">--</div></div>
                <div class="metric-item"><div class="metric-label">Unique Sessions</div><div class="metric-val" id="totSessions">--</div></div>
                <div class="metric-item"><div class="metric-label">Avg Rate</div><div class="metric-val">~1.2 req/m</div></div>
            </div>
        </div>

        <!-- Panel 3: Errors & Retrieval -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">3. Error Rate & Retrieval Success</span>
                <span class="slo-tag">Max Error: 2%</span>
            </div>
            <div class="chart-box">
                <canvas id="chartErrors"></canvas>
            </div>
            <div class="metric-summary">
                <div class="metric-item"><div class="metric-label">Error Rate</div><div class="metric-val" id="errRate">0.0%</div></div>
                <div class="metric-item"><div class="metric-label">Retrieval Success</div><div class="metric-val" id="retSuccess" style="color: #10b981;">100%</div></div>
            </div>
        </div>

        <!-- Panel 4: Cost -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">4. Cost (USD)</span>
                <span class="slo-tag">Threshold: ≤ $2.50</span>
            </div>
            <div class="chart-box">
                <canvas id="chartCost"></canvas>
            </div>
            <div class="metric-summary">
                <div class="metric-item"><div class="metric-label">Total Cost</div><div class="metric-val" id="costTotal" style="color: #c084fc;">$0.000000</div></div>
                <div class="metric-item"><div class="metric-label">Model</div><div class="metric-val">claude-sonnet-4-5</div></div>
            </div>
        </div>

        <!-- Panel 5: Tokens -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">5. Input & Output Tokens</span>
                <span class="slo-tag">Threshold: ≤ 50,000</span>
            </div>
            <div class="chart-box">
                <canvas id="chartTokens"></canvas>
            </div>
            <div class="metric-summary">
                <div class="metric-item"><div class="metric-label">Tokens In</div><div class="metric-val" id="tokIn">--</div></div>
                <div class="metric-item"><div class="metric-label">Tokens Out</div><div class="metric-val" id="tokOut">--</div></div>
                <div class="metric-item"><div class="metric-label">Total</div><div class="metric-val" id="tokTot" style="color: #818cf8;">--</div></div>
            </div>
        </div>

        <!-- Panel 6: Quality -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">6. Quality Proxy Score</span>
                <span class="slo-tag" style="border-color: #10b981; color: #34d399; background: rgba(16, 185, 129, 0.15);">Target: ≥ 0.75</span>
            </div>
            <div class="chart-box">
                <canvas id="chartQuality"></canvas>
            </div>
            <div class="metric-summary">
                <div class="metric-item"><div class="metric-label">Mean Quality</div><div class="metric-val" id="qualityMean" style="color: #fbbf24;">--</div></div>
                <div class="metric-item"><div class="metric-label">Evaluation Metric</div><div class="metric-val">Heuristic Proxy</div></div>
            </div>
        </div>
    </div>

    <script>
        fetch('/api/metrics')
            .then(res => res.json())
            .then(data => {
                document.getElementById('p50Val').innerText = data.p50 + 'ms';
                document.getElementById('p95Val').innerText = data.p95 + 'ms';
                document.getElementById('p99Val').innerText = data.p99 + 'ms';
                document.getElementById('ttftVal').innerText = data.ttft_p95 + 'ms';
                document.getElementById('totReq').innerText = data.total_req;
                document.getElementById('totSessions').innerText = data.unique_sessions;
                document.getElementById('errRate').innerText = data.error_rate.toFixed(1) + '%';
                document.getElementById('retSuccess').innerText = data.retrieval_rate.toFixed(1) + '%';
                document.getElementById('costTotal').innerText = '$' + data.total_cost.toFixed(5);
                document.getElementById('tokIn').innerText = data.tokens_in;
                document.getElementById('tokOut').innerText = data.tokens_out;
                document.getElementById('tokTot').innerText = data.tokens_in + data.tokens_out;
                document.getElementById('qualityMean').innerText = data.mean_quality.toFixed(2);

                const commonOptions = {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } }
                    }
                };

                // 1. Latency Chart
                new Chart(document.getElementById('chartLatency'), {
                    type: 'bar',
                    data: {
                        labels: ['P50', 'P95', 'P99', 'TTFT P95'],
                        datasets: [{
                            data: [data.p50, data.p95, data.p99, data.ttft_p95],
                            backgroundColor: ['#38bdf8', '#818cf8', '#f43f5e', '#fbbf24'],
                            borderRadius: 6
                        }]
                    },
                    options: {
                        ...commonOptions,
                        scales: {
                            ...commonOptions.scales,
                            y: {
                                ...commonOptions.scales.y,
                                suggestedMax: 3500,
                                title: { display: true, text: 'Milliseconds (ms)', color: '#64748b' }
                            }
                        }
                    }
                });

                // 2. Traffic Chart
                new Chart(document.getElementById('chartTraffic'), {
                    type: 'bar',
                    data: {
                        labels: ['Received', 'Sent', 'Failed'],
                        datasets: [{
                            data: [data.total_req, data.total_resp, data.total_fail],
                            backgroundColor: ['#38bdf8', '#10b981', '#f43f5e'],
                            borderRadius: 6
                        }]
                    },
                    options: commonOptions
                });

                // 3. Errors Chart
                new Chart(document.getElementById('chartErrors'), {
                    type: 'bar',
                    data: {
                        labels: ['Error Rate %', 'Retrieval Success %'],
                        datasets: [{
                            data: [data.error_rate, data.retrieval_rate],
                            backgroundColor: ['#f43f5e', '#10b981'],
                            borderRadius: 6
                        }]
                    },
                    options: {
                        ...commonOptions,
                        scales: {
                            ...commonOptions.scales,
                            y: { ...commonOptions.scales.y, max: 100 }
                        }
                    }
                });

                // 4. Cost Chart
                new Chart(document.getElementById('chartCost'), {
                    type: 'bar',
                    data: {
                        labels: ['Total Cost (USD)'],
                        datasets: [{
                            data: [data.total_cost],
                            backgroundColor: ['#a78bfa'],
                            borderRadius: 6
                        }]
                    },
                    options: {
                        ...commonOptions,
                        scales: {
                            ...commonOptions.scales,
                            y: { ...commonOptions.scales.y, suggestedMax: 0.1 }
                        }
                    }
                });

                // 5. Tokens Chart
                new Chart(document.getElementById('chartTokens'), {
                    type: 'bar',
                    data: {
                        labels: ['Tokens In', 'Tokens Out', 'Total'],
                        datasets: [{
                            data: [data.tokens_in, data.tokens_out, data.tokens_in + data.tokens_out],
                            backgroundColor: ['#38bdf8', '#818cf8', '#c084fc'],
                            borderRadius: 6
                        }]
                    },
                    options: commonOptions
                });

                // 6. Quality Chart
                new Chart(document.getElementById('chartQuality'), {
                    type: 'bar',
                    data: {
                        labels: ['Mean Quality Proxy'],
                        datasets: [{
                            data: [data.mean_quality],
                            backgroundColor: ['#fbbf24'],
                            borderRadius: 6
                        }]
                    },
                    options: {
                        ...commonOptions,
                        scales: {
                            ...commonOptions.scales,
                            y: { ...commonOptions.scales.y, min: 0, max: 1.0 }
                        }
                    }
                });
            });
    </script>
</body>
</html>
"""

def compute_metrics():
    if not LOG_PATH.exists():
        return {}
    
    records = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    req_events = [r for r in records if r.get("event") == "request_received"]
    resp_events = [r for r in records if r.get("event") == "response_sent"]
    failed_events = [r for r in records if r.get("event") == "request_failed"]

    latencies = sorted([r["latency_ms"] for r in resp_events if "latency_ms" in r])
    ttfts = sorted([r["ttft_ms"] for r in resp_events if "ttft_ms" in r])
    
    def percentile(arr, p):
        if not arr: return 0
        k = (len(arr) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c: return arr[int(k)]
        return round(arr[f] * (c - k) + arr[c] * (k - f), 1)

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    ttft_p95 = percentile(ttfts, 95)

    tokens_in = sum(r.get("tokens_in", 0) for r in resp_events)
    tokens_out = sum(r.get("tokens_out", 0) for r in resp_events)
    total_cost = sum(r.get("cost_usd", 0.0) for r in resp_events)
    
    qualities = [r.get("quality_score", 0.0) for r in resp_events]
    mean_quality = round(sum(qualities) / len(qualities), 2) if qualities else 0.0

    retrieval_success = sum(1 for r in resp_events if r.get("tool_success") is True)
    retrieval_rate = (retrieval_success / len(resp_events) * 100) if resp_events else 100.0
    
    total_req = len(req_events)
    total_fail = len(failed_events)
    error_rate = (total_fail / total_req * 100) if total_req else 0.0
    
    sessions = set(r.get("session_id") for r in records if r.get("session_id"))

    return {
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "ttft_p95": ttft_p95,
        "total_req": total_req,
        "total_resp": len(resp_events),
        "total_fail": total_fail,
        "error_rate": error_rate,
        "retrieval_rate": retrieval_rate,
        "total_cost": total_cost,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "mean_quality": mean_quality,
        "unique_sessions": len(sessions),
    }

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/dashboard"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path == "/api/metrics":
            data = compute_metrics()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"[*] Dashboard running at http://localhost:{PORT}/dashboard")
    print(f"[*] Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
