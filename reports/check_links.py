#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量链接可访问性检测脚本
================================
功能:
1. 递归扫描输入的文件/目录 (JSON, CSV, TXT, 以及 .py/.md/.ipynb 等任意文本) 中的 URL。
2. 支持直接通过 --url 指定单个或多个 URL。
3. 并发异步请求 (httpx + asyncio)，可配置并发数、超时与重试次数。
4. 自动为部分站点添加常见浏览器 User-Agent，避免 400/403。
5. HEAD 请求失败或返回 405 时自动回退 GET。
6. 输出 JSON 与 CSV 报告到 reports/link_check_report_<timestamp>.{json,csv}。
7. 展示状态分类统计汇总。
8. 去重 (默认)；可通过 --allow-duplicate 保留重复项。

使用示例:
    python check_links.py --inputs files/index_table.json README.md \
        --concurrency 30 --timeout 15 --retries 2

    python check_links.py --url https://example.com --url https://electrongoo.com/privacypolicy.html

    # 指定自定义输出前缀
    python check_links.py --inputs files/ --output-prefix reports/my_run

依赖: 仅标准库 + httpx (请确保安装)。
    pip install httpx

注意:
- 如果需要解析 .ipynb，将会尝试加载为 JSON，从其中 source 字段提取文本再匹配 URL。
- JSON 里会递归提取所有字符串值尝试匹配 URL，无需指定字段名。
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Dict, Any, Set, Optional

try:
    import httpx  # type: ignore
except ImportError:
    print("[ERROR] 未安装 httpx，请先运行: pip install httpx", file=sys.stderr)
    sys.exit(1)

URL_REGEX = re.compile(r"https?://[\w\-._~:/?#@!$&'()*+,;=%]+", re.IGNORECASE)

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
class LinkResult:
    url: str
    final_url: str | None
    status_code: int | None
    ok: bool
    category: str
    error: str | None
    elapsed_ms: float | None
    content_type: str | None
    content_length: int | None
    retries_used: int
    method: str
    timestamp: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="批量检测链接可访问性")
    p.add_argument("--inputs", nargs="*", default=[], help="输入的文件或目录，可多个。支持 json/csv/txt/ipynb 及任意文本。")
    p.add_argument("--url", dest="urls", action="append", default=[], help="直接附加检测的 URL，可多次传递。")
    p.add_argument("--concurrency", type=int, default=20, help="并发请求数")
    p.add_argument("--timeout", type=float, default=15.0, help="单个请求超时(秒)")
    p.add_argument("--retries", type=int, default=2, help="失败重试次数 (不含首次)")
    p.add_argument("--allow-duplicate", action="store_true", help="不过滤重复 URL")
    p.add_argument("--output-prefix", default=None, help="输出文件前缀 (默认: reports/link_check_report_<timestamp>)")
    p.add_argument("--no-head", action="store_true", help="直接使用 GET，不先尝试 HEAD")
    p.add_argument("--jitter", type=float, default=0.0, help="在 0~jitter 秒之间增加随机延迟，缓和请求")
    p.add_argument("--http2", action="store_true", help="启用 HTTP/2 (默认关闭，有些站点对 h2 指纹敏感)")
    p.add_argument("--proxy", default=None, help="可选 HTTP/HTTPS 代理，如 http://127.0.0.1:7890")
    p.add_argument("--extract-regex", default=None, help="自定义 URL 正则 (默认内置)")
    p.add_argument("--limit", type=int, default=None, help="测试或调试时仅检测前 N 条 URL")
    p.add_argument("--flush-every", type=int, default=50, help="每完成 N 条就增量写入一次 partial 报告 (当前实现未启用，预留)")
    return p.parse_args()


def collect_urls(paths: List[str], extra_urls: List[str], allow_duplicate: bool, custom_regex: Optional[str]) -> List[str]:
    url_pattern = re.compile(custom_regex, re.IGNORECASE) if custom_regex else URL_REGEX
    collected: List[str] = []
    seen: Set[str] = set()

    def add(u: str):
        if not allow_duplicate:
            if u in seen:
                return
            seen.add(u)
        collected.append(u)

    def extract_from_text(text: str):
        for m in url_pattern.finditer(text):
            add(m.group(0))

    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"[WARN] 输入路径不存在: {p}")
            continue
        if path.is_dir():
            for sub in path.rglob('*'):
                if sub.is_file():
                    try:
                        text = sub.read_text(encoding='utf-8', errors='ignore')
                    except Exception:
                        continue
                    extract_from_text(text)
        else:
            suffix = path.suffix.lower()
            try:
                if suffix == '.json' or suffix == '.ipynb':
                    obj = json.loads(path.read_text(encoding='utf-8', errors='ignore'))
                    def walk(o: Any):
                        if isinstance(o, str):
                            extract_from_text(o)
                        elif isinstance(o, dict):
                            for v in o.values():
                                walk(v)
                        elif isinstance(o, list):
                            for v in o:
                                walk(v)
                    walk(obj)
                elif suffix == '.csv':
                    import csv as _csv
                    with path.open('r', encoding='utf-8', errors='ignore') as f:
                        reader = _csv.reader(f)
                        for row in reader:
                            for cell in row:
                                extract_from_text(cell)
                else:
                    text = path.read_text(encoding='utf-8', errors='ignore')
                    extract_from_text(text)
            except Exception as e:
                print(f"[WARN] 解析文件失败 {path}: {e}")

    for u in extra_urls:
        add(u)

    return collected


async def fetch_url(client: httpx.AsyncClient, url: str, timeout: float, retries: int, use_head: bool, jitter: float) -> LinkResult:
    import random
    attempts = 0
    method_used = 'HEAD' if use_head else 'GET'
    last_exc: Optional[Exception] = None
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    start = time.perf_counter()

    # sequence of methods to try if head not allowed
    methods_sequence = []
    if use_head:
        methods_sequence.append('HEAD')
    methods_sequence.append('GET')

    while attempts <= retries:
        if jitter > 0:
            await asyncio.sleep(random.random() * jitter)
        for method in methods_sequence:
            try:
                resp = await client.request(method, url, timeout=timeout, follow_redirects=True)
                status_code = resp.status_code
                final_url = str(resp.url)
                content_type = resp.headers.get('Content-Type')
                cl = resp.headers.get('Content-Length')
                if cl and cl.isdigit():
                    content_length = int(cl)
                method_used = method
                # If HEAD returns something not ok (e.g. 405) -> try GET immediately
                if method == 'HEAD' and (status_code >= 400 or status_code == 405):
                    continue  # fallthrough to GET
                elapsed_ms = (time.perf_counter() - start) * 1000
                category = categorize_status(status_code)
                return LinkResult(
                    url=url,
                    final_url=final_url,
                    status_code=status_code,
                    ok=200 <= status_code < 400,
                    category=category,
                    error=None,
                    elapsed_ms=elapsed_ms,
                    content_type=content_type,
                    content_length=content_length,
                    retries_used=attempts,
                    method=method_used,
                    timestamp=datetime.utcnow().isoformat(),
                )
            except Exception as e:  # noqa
                last_exc = e
        attempts += 1

    elapsed_ms = (time.perf_counter() - start) * 1000
    return LinkResult(
        url=url,
        final_url=final_url,
        status_code=status_code,
        ok=False,
        category='exception',
        error=short_exception(last_exc),
        elapsed_ms=elapsed_ms,
        content_type=content_type,
        content_length=content_length,
        retries_used=attempts - 1,
        method=method_used,
        timestamp=datetime.utcnow().isoformat(),
    )


def short_exception(e: Optional[Exception]) -> Optional[str]:
    if not e:
        return None
    return f"{e.__class__.__name__}: {str(e)}"[:500]


def categorize_status(status: Optional[int]) -> str:
    if status is None:
        return 'no_status'
    if 200 <= status < 300:
        return '2xx'
    if 300 <= status < 400:
        return '3xx'
    if 400 <= status < 500:
        return '4xx'
    if 500 <= status < 600:
        return '5xx'
    return 'other'


async def run_checks(urls: List[str], concurrency: int, timeout: float, retries: int, use_head: bool, jitter: float, http2: bool, proxy: Optional[str]) -> List[LinkResult]:
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)

    async def _create_client() -> httpx.AsyncClient:
        base_kwargs = dict(
            headers=DEFAULT_HEADERS,
                timeout=httpx.Timeout(timeout, connect=timeout/2, read=timeout, write=timeout, pool=timeout),
            limits=limits,
            http2=http2,
            follow_redirects=True,
        )
        # 兼容不同 httpx 版本: 尝试 proxies -> proxy -> 去掉
        if proxy:
            for key in ("proxies", "proxy"):
                try:
                    kw = dict(base_kwargs)
                    kw[key] = proxy
                    return httpx.AsyncClient(**kw)
                except TypeError:
                    continue
        # 如果 http2 不被支持（极老版本），再次降级尝试
        try:
            return httpx.AsyncClient(**base_kwargs)
        except TypeError:
            base_kwargs.pop("http2", None)
            return httpx.AsyncClient(**base_kwargs)

    client = await _create_client()
    try:
        sem = asyncio.Semaphore(concurrency)

        async def bounded(u: str):
            async with sem:
                return await fetch_url(client, u, timeout, retries, use_head, jitter)

        tasks = [asyncio.create_task(bounded(u)) for u in urls]
        results: List[LinkResult] = []
        done_count = 0
        total = len(tasks)
        for coro in asyncio.as_completed(tasks):
            res = await coro
            results.append(res)
            done_count += 1
            if done_count % max(1, total // 20 or 1) == 0:
                print(f"Progress: {done_count}/{total} ({done_count/total:.0%})")
        return results
    finally:
        await client.aclose()


def write_reports(results: List[LinkResult], output_prefix: str):
    out_dir = Path(output_prefix).parent
    print(f"[DEBUG] 准备创建输出目录: {out_dir}")
    os.makedirs(out_dir, exist_ok=True)
    print(f"[DEBUG] 输出目录存在: {out_dir.exists()} 绝对路径: {out_dir.resolve()}")
    json_path = f"{output_prefix}.json"
    csv_path = f"{output_prefix}.csv"

    # JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)

    # CSV
    fieldnames = list(asdict(results[0]).keys()) if results else []
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    print(f"[OK] 报告已生成:\n  JSON: {json_path}\n  CSV : {csv_path}")


    def write_partial(results: List[LinkResult], output_prefix: str):
        """写入 partial 报告，避免长时间运行中断没有结果。"""
        out_dir = Path(output_prefix).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        part_path = f"{output_prefix}_partial.json"
        try:
            with open(part_path, 'w', encoding='utf-8') as f:
                json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)
            print(f"[DEBUG] 已写入增量 partial: {part_path} (共 {len(results)} 条)")
        except Exception as e:
            print(f"[WARN] 写入 partial 失败: {e}")


def print_summary(results: List[LinkResult]):
    from collections import Counter
    counter = Counter(r.category for r in results)
    total = len(results)
    ok_count = sum(1 for r in results if r.ok)
    print("\n===== 汇总 =====")
    print(f"总数: {total}")
    print(f"成功(ok): {ok_count}  ({ok_count/total:.1%})")
    for k in sorted(counter.keys()):
        print(f"{k}: {counter[k]}")
    # 列出失败示例
    failures = [r for r in results if not r.ok][:10]
    if failures:
        print("\n前 10 个失败示例:")
        for r in failures:
            print(f" - {r.url} | status={r.status_code} | err={r.error}")


def main():
    args = parse_args()
    if not args.inputs and not args.urls:
        print("[ERROR] 请至少提供 --inputs 或 --url")
        return 2

    urls = collect_urls(args.inputs, args.urls, args.allow_duplicate, args.extract_regex)
    if not urls:
        print("[WARN] 未收集到 URL")
        return 0

    print(f"共收集到 {len(urls)} 条 URL (去重后)")
    if args.limit is not None and args.limit > 0:
        urls = urls[: args.limit]
        print(f"[DEBUG] 已根据 --limit 截断为 {len(urls)} 条")

    output_prefix = args.output_prefix
    if not output_prefix:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_prefix = f"reports/link_check_report_{ts}"

    try:
        print("[DEBUG] 开始执行异步检测 ...")
        results = asyncio.run(
            run_checks(
                    urls=urls,
                    concurrency=args.concurrency,
                    timeout=args.timeout,
                    retries=args.retries,
                    use_head=not args.no_head,
                    jitter=args.jitter,
                    http2=args.http2,
                    proxy=args.proxy,
                )
        )
        print(f"[DEBUG] 异步检测完成，结果数: {len(results)}")
    except KeyboardInterrupt:
        print("\n[WARN] 用户中断，已收集部分结果。")
        results = []
    except Exception:
        print("[ERROR] 运行过程中发生异常:\n" + traceback.format_exc())
        return 1

    write_reports(results, output_prefix)
    print(f"[DEBUG] 结果数量: {len(results)} 即将打印汇总")
    print_summary(results)
    return 0


if __name__ == '__main__':
    sys.exit(main())
