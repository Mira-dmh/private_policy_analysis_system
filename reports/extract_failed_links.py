#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract failed entries from reports/index_table_links_report.json, keeping only id and url (with status and error),
generate dedicated failure reports (JSON/CSV/Markdown), and optionally delete other existing report files.

Usage:
    python extract_failed_links.py --report reports/index_table_links_report.json \
        --output-prefix reports/index_table_links_failed --delete-others

Arguments:
    --report         Input complete report JSON (from check_index_table_links.py output)
    --output-prefix  Failed report prefix (default: reports/index_table_links_failed)
    --delete-others  Delete other report files in directory (keep failure reports themselves)
"""
from __future__ import annotations
import argparse, json, csv, sys, os
from pathlib import Path
from typing import List


def parse_args():
    p = argparse.ArgumentParser(description="Extract failed links")
    p.add_argument('--report', default='reports/index_table_links_report.json', help='Original JSON report path')
    p.add_argument('--output-prefix', default='reports/index_table_links_failed', help='Failed output file prefix')
    p.add_argument('--delete-others', action='store_true', help='Delete other report files in same directory')
    return p.parse_args()


def load_report(path: Path):
    if not path.exists():
        print(f"[ERROR] 报告文件不存在: {path}")
        sys.exit(2)
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            print('[ERROR] 报告 JSON 顶层不是数组')
            sys.exit(3)
        return data
    except Exception as e:
        print(f'[ERROR] 读取报告失败: {e}')
        sys.exit(4)


def filter_failed(rows: List[dict]):
    failed = [r for r in rows if not r.get('ok')]
    return failed


def write_outputs(failed: List[dict], prefix: str):
    out_dir = Path(prefix).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = Path(prefix + '.json')
    csv_path = Path(prefix + '.csv')
    md_path = Path(prefix + '.md')

    # 精简数据: 只保留 id,url,status_code,error,final_url
    slim = []
    for r in failed:
        slim.append({
            'id': r.get('id'),
            'url': r.get('url'),
            'final_url': r.get('final_url'),
            'status_code': r.get('status_code'),
            'error': r.get('error'),
        })

    with json_path.open('w', encoding='utf-8') as f:
        json.dump(slim, f, ensure_ascii=False, indent=2)

    with csv_path.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id','url','final_url','status_code','error'])
        for r in slim:
            w.writerow([r['id'], r['url'], r['final_url'], r['status_code'], (r['error'] or '')])

    with md_path.open('w', encoding='utf-8') as f:
        f.write('# Failed Links\n\n')
        f.write(f'Total Failed: {len(slim)}\n\n')
        f.write('| id | status | url | error |\n|----|--------|-----|-------|\n')
        for r in slim:
            err_short = (r['error'] or '')[:100].replace('\n',' ')
            f.write(f"| {r['id']} | {r['status_code']} | {r['url']} | {err_short} |\n")

    print('[OK] 失败报告已生成:')
    print('  JSON:', json_path)
    print('  CSV :', csv_path)
    print('  MD  :', md_path)
    return json_path, csv_path, md_path


def delete_others(keep_files, base_dir: Path):
    patterns_remove = [
        'link_check_full.*', 'link_check_manual.*',
        'index_table_links_report.*',  # 原始完整报告
        # 旧的可能文件
    ]
    removed = []
    for pat in patterns_remove:
        for p in base_dir.glob(pat):
            if p in keep_files:
                continue
            try:
                p.unlink()
                removed.append(p.name)
            except Exception as e:
                print(f'[WARN] 删除失败 {p}: {e}')
    if removed:
        print('[OK] 已删除其它报告文件:')
        for name in removed:
            print('  -', name)
    else:
        print('[INFO] 没有发现可删除的其它报告文件')


def main():
    args = parse_args()
    report_path = Path(args.report)
    rows = load_report(report_path)
    failed = filter_failed(rows)
    print(f'原始记录: {len(rows)}  失败: {len(failed)}')
    if not failed:
        print('[INFO] 没有失败条目，不生成失败报告。')
        return 0
    json_path, csv_path, md_path = write_outputs(failed, args.output_prefix)
    if args.delete_others:
        delete_others({json_path, csv_path, md_path}, base_dir=report_path.parent)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
