"""Post the public sample inputs concurrently and report latency."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import time
from pathlib import Path

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def post_one(url: str, payload: dict) -> tuple[float, str | None]:
    start = time.perf_counter()
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            elapsed = time.perf_counter() - start
            return elapsed, None if response.status == 200 else f"HTTP {response.status}"
    except HTTPError as exc:
        return time.perf_counter() - start, f"HTTP {exc.code}"
    except (URLError, TimeoutError, OSError) as exc:
        return time.perf_counter() - start, type(exc).__name__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("-n", "--rounds", type=int, default=3)
    parser.add_argument("-c", "--concurrency", type=int, default=5)
    args = parser.parse_args()
    if args.rounds < 1 or args.concurrency < 1:
        parser.error("rounds and concurrency must be positive")
    cases = json.loads((ROOT / "data" / "public_samples.json").read_text(encoding="utf-8"))["cases"]
    if len(cases) != 10:
        parser.error("expected exactly 10 public sample cases")
    jobs = [(case["id"], case["input"]) for _ in range(args.rounds) for case in cases]
    url = args.base_url.rstrip("/") + "/optimize-energy"
    latencies: list[float] = []
    failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(post_one, url, payload): case_id for case_id, payload in jobs}
        for future in concurrent.futures.as_completed(futures):
            elapsed, error = future.result()
            latencies.append(elapsed)
            if error:
                failures.append(f"{futures[future]}: {error}")
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    print(f"total requests: {len(jobs)} | errors: {len(failures)} | p50: {p50:.3f}s | p95: {p95:.3f}s | max: {max(latencies):.3f}s")
    for line in failures[:30]:
        print(line)
    return 1 if failures or p95 > 5 else 0


if __name__ == "__main__":
    raise SystemExit(main())
