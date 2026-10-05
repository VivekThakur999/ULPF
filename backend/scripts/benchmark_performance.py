"""ULPF Final Performance Benchmarking Suite.

Measures and records:
1. Pipeline Ingestion & Normalization Throughput (events/sec)
2. MongoDB Bulk Write Throughput & Batch Latency
3. Log Explorer Paginated Search Latency (P50, P95, P99)
4. Multi-Field Aggregation & Facet Computation Latency
5. Alert & Security Detection Query Latency
6. Template Mining & Extraction Performance
7. Byte-Exact Micro-Compression Reconstruction Validation
"""
from __future__ import annotations

import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.core.config import settings
from app.core.mongodb import ensure_mongo_indexes, get_mongo_db
from app.models.template import Template, TemplateMatch
from app.repositories.events import EventQuery
from app.repositories.mongodb.alerts import MongoAlertRepository
from app.repositories.mongodb.events import MongoEventRepository
from app.repositories.mongodb.templates import MongoTemplateRepository
from app.services.compression.engine import reconstruct
from app.services.pipeline.service import run_record
from app.services.templates.classify import separators_for, tokenize
from app.services.templates.mining import RecordRef, mine_lines


def run_comprehensive_benchmarks():
    if "mongo" in settings.mongodb_uri and not os.environ.get("RUNNING_IN_DOCKER"):
        settings.mongodb_uri = "mongodb://127.0.0.1:27017/ulpf_telemetry"

    db = get_mongo_db()
    ensure_mongo_indexes(db)
    event_repo = MongoEventRepository(db)
    alert_repo = MongoAlertRepository(db)
    tpl_repo = MongoTemplateRepository(db)

    print("================================================================================")
    print("ULPF FINAL RELEASE — COMPREHENSIVE PERFORMANCE BENCHMARK SUITE")
    print("================================================================================")
    print(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {platform.python_version()} | Architecture: {platform.architecture()[0]}")
    print(f"MongoDB Target: {settings.mongodb_uri}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("--------------------------------------------------------------------------------")

    # 1. Raw Pipeline Normalization & Security Shield Ingestion Throughput
    sample_raw_logs = [
        "Oct  5 14:32:10 edge-fw01 %ASA-4-106023: Deny tcp src outside:192.168.1.105/49152 dst inside:10.0.0.50/443 by access-group 'outside_in'",
        "Oct  5 14:32:11 auth-srv-02 sshd[5892]: Failed password for root from 203.0.113.42 port 22 ssh2",
        "192.168.1.10 - - [05/Oct/2026:14:32:12 +0000] \"GET /api/v1/auth/login HTTP/1.1\" 200 4522 \"-\" \"Mozilla/5.0\"",
        "10.0.0.5 - admin [05/Oct/2026:14:32:13 +0000] \"POST /admin/exec HTTP/1.1\" 403 214 \"-\" \"curl/7.68.0\"",
        "{\"timestamp\": \"2026-10-05T14:32:14Z\", \"level\": \"error\", \"service\": \"payment-gw\", \"msg\": \"Payment transaction timeout for order 98124\", \"src_ip\": \"10.0.2.14\"}",
    ]

    pipeline_count = 500
    t0 = time.perf_counter()
    for i in range(pipeline_count):
        raw_line = sample_raw_logs[i % len(sample_raw_logs)]
        _ = run_record(raw_line, source_name="benchmark_stream")
    t_pipeline = time.perf_counter() - t0
    pipeline_rate = round(pipeline_count / t_pipeline, 2)
    print(f"[BENCHMARK 1] Pipeline Normalization & Shield: {pipeline_count} events in {t_pipeline:.3f}s | Throughput: {pipeline_rate:,.1f} events/sec")

    # 2. MongoDB Bulk Ingestion Throughput (Batch write plane)
    batch_sizes = [100, 500, 1000, 2500]
    for n in batch_sizes:
        now = datetime.now(timezone.utc)
        docs = [
            {
                "id": f"bench_ev_{i}_{int(time.time()*1000)}",
                "source": "syslog-firewall",
                "host": f"fw-0{i % 4}.perimeter.internal",
                "event_type": "traffic_denied" if i % 3 == 0 else "traffic_allowed",
                "severity": "high" if i % 3 == 0 else "info",
                "source_ip": f"198.51.100.{i % 254 + 1}",
                "destination_ip": "10.0.0.1",
                "destination_port": 443 if i % 2 == 0 else 80,
                "protocol": "TCP",
                "action": "DROP" if i % 3 == 0 else "PERMIT",
                "message": f"Firewall packet inspection rule matched on interface eth0 packet {i}",
                "timestamp": now,
                "ingested_at": now,
                "processing_status": "ok",
                "confidence": 0.98,
            }
            for i in range(n)
        ]

        t0 = time.perf_counter()
        _ = event_repo.insert_bulk(docs)
        t_elapsed = time.perf_counter() - t0
        rate = round(n / t_elapsed, 2)
        print(f"[BENCHMARK 2] MongoDB Bulk Write (Batch={n:4d}): {t_elapsed*1000:7.2f} ms | Rate: {rate:9,.1f} events/sec")

    # 3. Log Explorer Query Latency (P50, P95, P99)
    query_latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        page = event_repo.search(EventQuery(source="syslog-firewall", limit=50, order="desc"))
        query_latencies.append((time.perf_counter() - t0) * 1000)

    p50 = statistics.median(query_latencies)
    p95 = sorted(query_latencies)[int(len(query_latencies) * 0.95)]
    p99 = sorted(query_latencies)[int(len(query_latencies) * 0.99)]
    print(f"[BENCHMARK 3] Log Explorer Query (100 runs):   P50={p50:.2f} ms | P95={p95:.2f} ms | P99={p99:.2f} ms (Total found: {page.total})")

    # 4. Multi-Field Aggregation & Facet Computation Latency
    agg_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = event_repo.facets(EventQuery(source="syslog-firewall"), ["severity", "host", "action"])
        agg_latencies.append((time.perf_counter() - t0) * 1000)

    agg_p50 = statistics.median(agg_latencies)
    agg_p95 = sorted(agg_latencies)[int(len(agg_latencies) * 0.95)]
    print(f"[BENCHMARK 4] Aggregation & Facet Query (50 runs): P50={agg_p50:.2f} ms | P95={agg_p95:.2f} ms")

    # 5. Alert & Security Detection Query Latency
    alert_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        _, _ = alert_repo.list_alerts(limit=50)
        alert_latencies.append((time.perf_counter() - t0) * 1000)
    alert_p50 = statistics.median(alert_latencies)
    print(f"[BENCHMARK 5] Security Alert Queue Query (50 runs): P50={alert_p50:.2f} ms")

    # 6. Template Mining & Micro-Compression Efficiency
    mining_records = [
        RecordRef(
            ref_id=f"raw-{i}",
            raw=f"2026-10-05 14:00:{i%60:02d} [INFO] Authentication successful for user_{i%20} from 192.168.1.{i%50+1}",
            source="app-auth",
            ts=datetime.now(timezone.utc),
        )
        for i in range(1000)
    ]
    t0 = time.perf_counter()
    clusters = mine_lines(mining_records)
    t_mining = time.perf_counter() - t0
    print(f"[BENCHMARK 6] Template Mining: 1,000 logs clustered into {len(clusters)} template(s) in {t_mining*1000:.2f} ms ({round(1000/t_mining, 1)} logs/s)")

    # 7. Exact Micro-Compression Reconstruction Check
    if clusters:
        c = clusters[0]
        tpl_model = Template(
            template_key="TPL-BENCH-001",
            pattern=c.pattern_text(),
            token_count=c.token_count,
            literal_tokens=c.literals,
            variable_types=c.var_types,
            separators=c.separators,
            trailing=c.trailing,
        )
        sample_line = mining_records[0].raw
        spans = tokenize(sample_line)
        tokens = [s.text for s in spans]
        variables = c.extract_variables(tokens)
        seps, trailing = separators_for(sample_line, spans)
        match_model = TemplateMatch(
            template_id="TPL-BENCH-001",
            raw_log_id="raw-001",
            variables=variables,
            separators=None if seps == c.separators else seps,
            trailing="" if trailing == c.trailing else trailing,
        )
        reconstructed = reconstruct(tpl_model, match_model)
        assert reconstructed == sample_line, f"Reconstruction mismatch!\nOriginal: {sample_line}\nReconstructed: {reconstructed}"
        print(f"[BENCHMARK 7] Micro-Compression Reconstruction: Verified 100% byte-for-byte exact equality.")

    # Cleanup benchmark records
    event_repo.collection.delete_many({"source": "syslog-firewall"})
    print("--------------------------------------------------------------------------------")
    print("BENCHMARK EXECUTION COMPLETED SUCCESSFULLY WITH ZERO FAILURES.")
    print("================================================================================")


if __name__ == "__main__":
    run_comprehensive_benchmarks()
