#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatGuard 评测脚本

用法：
    python run_eval.py                 # 全量（30 条，会真调后端，注意资源点）
    python run_eval.py --limit 5       # 只跑前 5 条
    python run_eval.py --ids P01,P02   # 指定用例
    python run_eval.py --demo          # 用 mock 数据跑一遍流程（不花钱，验证脚本本身）
    python run_eval.py --url http://127.0.0.1:15000

输出：
    1) 控制台逐条结果 + 汇总指标
    2) tests/results-<时间戳>.json（完整原始结果，便于复查）

指标口径（见 cases.json 的 label_rules）：
    召回率 = 正样本中 level ∈ {medium, high, critical} 的比例
    误报率 = 负样本中 level ∈ {high, critical} 的比例
    （漏报比误报代价高，所以召回是主指标）
"""

import argparse, json, os, sys, time, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases.json")
LEVEL_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def post(url, payload, timeout=200):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def run_one(base, case, demo=False):
    payload = {"demo": True, "scenario": "suspicious"} if demo else {
        "mode": "text", "text": case["text"]}
    t0 = time.time()
    try:
        out = post(base.rstrip("/") + "/api/analyze", payload)
        secs = round(time.time() - t0, 1)
        if not out.get("ok"):
            return {"ok": False, "error": out.get("error"), "secs": secs}
        j = out.get("judgment") or {}
        return {
            "ok": True, "secs": secs,
            "verdict": j.get("verdict"), "level": j.get("level"),
            "victim_state": j.get("victim_state"),
            "hypos": [h.get("name") for h in (j.get("hypotheses") or [])],
            "one_line": (j.get("one_line") or "")[:120],
            "evidence_n": len(j.get("evidence") or []),
        }
    except Exception as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e),
                "secs": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("CG_BFF", "http://127.0.0.1:15000"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", default="")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--file", default="", help="用例文件（默认 cases.json，可传 holdout.json）")
    args = ap.parse_args()

    cases_path = args.file or CASES
    if not os.path.isabs(cases_path):
        cases_path = os.path.join(HERE, cases_path)
    print("用例文件：%s" % os.path.basename(cases_path))
    with open(cases_path, encoding="utf-8") as f:
        data = json.load(f)
    cases = data["cases"]
    if args.ids:
        want = [x.strip().upper() for x in args.ids.split(",") if x.strip()]
        cases = [c for c in cases if c["id"].upper() in want]
    if args.limit:
        cases = cases[:args.limit]

    print("用例 %d 条 · 后端 %s%s\n" % (len(cases), args.url, " · DEMO" if args.demo else ""))
    results = []
    for c in cases:
        r = run_one(args.url, c, demo=args.demo)
        r.update({"id": c["id"], "label": c["label"], "type": c["type"]})
        results.append(r)
        mark = "?" if not r.get("ok") else ("✓" if r.get("level") else "-")
        print("  %-4s %-9s %-14s %-9s %5ss %s" % (
            c["id"], c["label"], c["type"],
            (r.get("level") or "ERR"), r.get("secs"), mark))
        if not r.get("ok"):
            print("        ! %s" % r.get("error"))

    ok = [r for r in results if r.get("ok")]
    pos = [r for r in ok if r["label"] == "positive"]
    neg = [r for r in ok if r["label"] == "negative"]

    def lv(r):
        return LEVEL_ORDER.get(r.get("level"), -1)

    hit = [r for r in pos if lv(r) >= 2]
    fp = [r for r in neg if lv(r) >= 3]
    recall = (len(hit) / len(pos) * 100) if pos else 0
    fpr = (len(fp) / len(neg) * 100) if neg else 0
    avg = (sum(r["secs"] for r in ok) / len(ok)) if ok else 0

    print("\n" + "=" * 56)
    print("正样本 %d 条：召回 %d/%d = %.1f%%" % (len(pos), len(hit), len(pos), recall))
    print("负样本 %d 条：误报 %d/%d = %.1f%%" % (len(neg), len(fp), len(neg), fpr))
    print("失败 %d 条 · 平均耗时 %.1f 秒" % (len(results) - len(ok), avg))
    if hit and len(hit) < len(pos):
        print("\n漏报的：")
        for r in pos:
            if r not in hit:
                print("  %s %s → %s" % (r["id"], r["type"], r.get("level")))
    if fp:
        print("\n误报的：")
        for r in fp:
            print("  %s %s → %s" % (r["id"], r["type"], r.get("level")))
    print("=" * 56)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(HERE, "results-%s.json" % stamp)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"meta": {"url": args.url, "demo": args.demo, "at": stamp,
                            "recall": recall, "fpr": fpr, "n": len(results)},
                   "results": results}, f, ensure_ascii=False, indent=2)
    print("已写入 %s" % out)


if __name__ == "__main__":
    main()
