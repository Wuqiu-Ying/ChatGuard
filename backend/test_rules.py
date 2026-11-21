#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则自测（不调平台、不花额度）

把 tests/cases.json 里的对话文本转成 messages 列表，喂给 code_node_rules.main()，
看 rule_hits 命中情况：
  - 正样本：希望命中（漏了说明规则不够）
  - 负样本：希望**不**命中（命中了说明规则太宽，会误导研判）

用法：
    python test_rules.py            # 汇总
    python test_rules.py -v         # 逐条打印命中
"""

import json, os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from code_node_rules import main as rules_main   # noqa: E402

TESTS = os.path.join(os.path.dirname(HERE), "tests")


def _pick_cases_file(argv):
    """--file holdout.json / --file tests/holdout.json / 默认 cases.json"""
    for i, a in enumerate(argv):
        if a == "--file" and i + 1 < len(argv):
            p = argv[i + 1]
            return p if os.path.isabs(p) else os.path.join(TESTS, os.path.basename(p))
    return os.path.join(TESTS, "cases.json")


def to_messages(text):
    """'对方: xxx' / '我: xxx' → [{type,speaker,text}]"""
    msgs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(对方|我)[（(][^）)]*[）)]?\s*[:：]\s*(.*)$", line) or \
            re.match(r"^(对方|我)\s*[:：]\s*(.*)$", line)
        if m:
            spk = "them" if m.group(1) == "对方" else "me"
            msgs.append({"i": len(msgs) + 1, "type": "text", "speaker": spk,
                         "text": m.group(2), "name": "", "size": ""})
        else:
            msgs.append({"i": len(msgs) + 1, "type": "text", "speaker": "unknown",
                         "text": line, "name": "", "size": ""})
    return msgs


def main():
    verbose = "-v" in sys.argv
    cases_file = _pick_cases_file(sys.argv)
    with open(cases_file, encoding="utf-8") as f:
        data = json.load(f)
    print("用例文件：%s\n" % os.path.relpath(cases_file, os.path.dirname(HERE)))

    pos_hit = pos_all = neg_hit = neg_all = 0
    rows = []
    for c in data["cases"]:
        out = json.loads(rules_main(json.dumps(to_messages(c["text"]), ensure_ascii=False), "")["payload"])
        hits = out.get("rule_hits", [])
        rows.append((c["id"], c["label"], c["type"], hits))
        if c["label"] == "positive":
            pos_all += 1
            pos_hit += 1 if hits else 0
        else:
            neg_all += 1
            neg_hit += 1 if hits else 0

    if verbose:
        print("id   label     type                 hits")
        for i, l, t, h in rows:
            print("%-5s %-9s %-20s %s" % (i, l, t, ", ".join(h) if h else "—"))

    print("\n正样本命中率（覆盖率）：%d/%d = %.0f%%" % (pos_hit, pos_all, pos_hit / pos_all * 100))
    print("负样本误命中率（噪声）  ：%d/%d = %.0f%%" % (neg_hit, neg_all, neg_hit / neg_all * 100))

    miss = [(i, t) for i, l, t, h in rows if l == "positive" and not h]
    noise = [(i, t, h) for i, l, t, h in rows if l == "negative" and h]
    if miss:
        print("\n未命中的正样本（规则缺口）：")
        for i, t in miss:
            print("  %s %s" % (i, t))
    if noise:
        print("\n误命中的负样本（规则太宽）：")
        for i, t, h in noise:
            print("  %s %s → %s" % (i, t, ", ".join(h)))


if __name__ == "__main__":
    main()
