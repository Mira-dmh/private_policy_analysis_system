#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
仅针对 files/index_table_from_excel.json 中的 (id, url) 进行可访问性检测并输出报告。
输出: reports/index_table_links_report.{json,csv}

使用:
    python check_index_table_links.py \
        --file files/index_table_from_excel.json \
        --concurrency 20 --timeout 12 --retries 1

可选:
    --limit N   仅检测前 N 条 (调试用)
"""
from __future__ import annotations
import argparse
import asyncio
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List
import sys

try:
    import httpx  # type: ignore
except ImportError:
    print("请先安装 httpx: pip install httpx", file=sys.stderr)
    sys.exit(1)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

@dataclass
class RowResult:
    id: int
    url: str
    final_url: Optional[str]
    status_code: Optional[int]
    ok: bool
    error: Optional[str]
    elapsed_ms: Optional[float]


def parse_args():
    p = argparse.ArgumentParser(description="检测 index_table_from_excel.json 中的链接")
    p.add_argument('--file', default='files/index_table_from_excel.json', help='JSON 文件路径')
    p.add_argument('--concurrency', type=int, default=20, help='并发数')
    p.add_argument('--timeout', type=float, default=12.0, help='超时秒')
    p.add_argument('--retries', type=int, default=1, help='重试次数 (不含首次)')
    p.add_argument('--limit', type=int, default=None, help='仅检测前 N 条')
    p.add_argument('--output-prefix', default='reports/index_table_links_report', help='输出前缀')
    p.add_argument('--http2', action='store_true', help='启用 HTTP/2')
    return p.parse_args()


async def fetch_one(client: httpx.AsyncClient, _id: int, url: str, timeout: float, retries: int) -> RowResult:
    attempts = 0
    last_exc = None
    start = time.perf_counter()
    while attempts <= retries:
        try:
            resp = await client.get(url, timeout=timeout, follow_redirects=True)
            elapsed = (time.perf_counter() - start) * 1000
            return RowResult(
                id=_id,
                url=url,
                final_url=str(resp.url),
                status_code=resp.status_code,
                ok=200 <= resp.status_code < 400,
                error=None,
                elapsed_ms=elapsed,
            )
        except Exception as e:  # noqa
            last_exc = e
            attempts += 1
    elapsed = (time.perf_counter() - start) * 1000
    return RowResult(
        id=_id,
        url=url,
        final_url=None,
        status_code=None,
        ok=False,
        error=f"{last_exc.__class__.__name__}: {last_exc}",
        elapsed_ms=elapsed,
    )


async def run(url_rows: List[tuple[int, str]], concurrency: int, timeout: float, retries: int, http2: bool) -> List[RowResult]:
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    # 兼容 httpx 旧版本 http2 参数可能报错
    client = None
    try:
        client = httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=timeout, limits=limits, http2=http2)
    except TypeError:
        client = httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=timeout, limits=limits)

    sem = asyncio.Semaphore(concurrency)
    results: List[RowResult] = []

    async def wrapped(rid: int, u: str):
        async with sem:
            return await fetch_one(client, rid, u, timeout, retries)

    tasks = [asyncio.create_task(wrapped(rid, u)) for rid, u in url_rows]
    done = 0
    total = len(tasks)
    for coro in asyncio.as_completed(tasks):
        res = await coro
        results.append(res)
        done += 1
        if done % max(1, total // 20 or 1) == 0:
            print(f"Progress: {done}/{total} ({done/total:.0%})")
    await client.aclose()
    return results


def write_reports(results: List[RowResult], prefix: str):
    Path(prefix).parent.mkdir(parents=True, exist_ok=True)
    import csv as _csv
    json_path = f"{prefix}.json"
    csv_path = f"{prefix}.csv"
    # JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)
    # CSV
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = _csv.writer(f)
        writer.writerow(["id", "url", "final_url", "status_code", "ok", "error", "elapsed_ms"])
        for r in results:
            writer.writerow([r.id, r.url, r.final_url, r.status_code, r.ok, r.error, f"{r.elapsed_ms:.1f}" if r.elapsed_ms else None])
    print(f"已生成报告:\n  JSON: {json_path}\n  CSV : {csv_path}")


def summary(results: List[RowResult]):
    total = len(results)
    ok_cnt = sum(1 for r in results if r.ok)
    print('\n===== 汇总 =====')
    print(f"总数: {total}")
    print(f"成功: {ok_cnt} ({ok_cnt/total:.1%})")
    fail = [r for r in results if not r.ok][:15]
    if fail:
        print("前 15 个失败:")
        for r in fail:
            print(f" - id={r.id} url={r.url} err={r.error} status={r.status_code}")


def main():
    args = parse_args()
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return 2
    try:
        data = json.loads(file_path.read_text(encoding='utf-8', errors='ignore'))
        if not isinstance(data, list):
            print('JSON 顶层不是数组')
            return 1
        rows: List[tuple[int, str]] = []
        for obj in data:
            if isinstance(obj, dict) and 'id' in obj and 'url' in obj:
                rid = obj['id']
                url = obj['url']
                if isinstance(rid, int) and isinstance(url, str) and url.startswith(('http://', 'https://')):
                    rows.append((rid, url))
        if args.limit:
            rows = rows[:args.limit]
        print(f"收集到 {len(rows)} 条 (id,url)")
    except Exception as e:
        print(f"解析 JSON 失败: {e}")
        return 1

    if not rows:
        print('没有可检测的 (id,url)')
        return 0

    results = asyncio.run(run(rows, args.concurrency, args.timeout, args.retries, args.http2))
    # 按 id 排序
    results.sort(key=lambda r: r.id)
    write_reports(results, args.output_prefix)
    summary(results)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
