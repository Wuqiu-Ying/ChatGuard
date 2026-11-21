# 代码节点 cg_rules_v4（与平台 CG-OCR-WF 代码节点保持一致）
# v4 变更（2026-11-18）：
#   1. 按公安部《20 个防诈关键词》补齐缺口：百万保障 / 安全账户 / 洗钱新手法 / 帮信两卡 / 境外高薪 …
#   2. **收窄泛词**：「下载」「扫码」单独出现不再命中，改为「诱导下载」「扫码引流」组合规则
#   3. 规则只做"线索"，不做定性；命中有歧义时宁可不报（精确率优先）
# 输入：transcript (string)；extra (string) 占位
# 输出：payload (string) = JSON 字符串

import json
import re

# ---- 单词规则：出现即记一笔（词都经过挑选，尽量专有）----
TEXT_RULES = {
    # 传统六类（基于真实案例，recall 高）
    "垫付刷单": ["垫付", "刷单", "连本带利", "返利任务", "先垫后返", "做满三单", "三单"],
    "共享屏幕": ["共享屏幕", "屏幕共享", "远程控制", "远程协助", "投屏"],
    "先交钱": ["保证金", "押金", "定金", "入职费", "培训费", "审核费", "工号费",
              "资料费", "解冻费", "激活费", "会员费", "手续费", "代收"],
    "脱离平台": ["加我v", "加个微信", "加我微信", "加我q", "加qq", "换个地方聊",
                "私下交易", "私下卖", "平台收中介费", "省去中介", "不走平台", "直接转账"],
    "诱导贷款征信": ["校园贷", "征信修复", "修复征信", "注销校园贷", "刷流水",
                  "提额", "验资", "激活额度", "分期"],

    # 2026-11-18 新增（来自公安部 20 关键词）
    "百万保障": ["百万保障", "误开通", "关闭保障", "免费保险"],
    "安全账户": ["安全账户", "资金清查", "资金比对", "涉嫌洗钱", "涉案资金"],
    "冒充公检法": ["公检法", "公安局", "检察院", "警官证", "拘捕令", "逮捕令",
                 "案件编号", "协查"],
    "保密施压": ["不许告诉", "不能告诉任何人", "全程保密", "别挂电话",
              "不要告诉家人", "别跟别人说", "别跟老师", "别告诉我妈", "别跟我妈",
              "不要告诉导师", "别告诉别人"],
    "小众聊天软件": ["小众软件", "小众聊天", "加密聊天", "这个软件保密", "监管不到"],
    "洗钱新手法": ["现金黄金", "购买黄金", "购物卡", "取现", "跑腿", "网约车送"],
    "帮信两卡": ["两卡", "帮信", "租借银行卡", "卖卡", "借卡", "手机卡借用",
               "走账", "走一下账", "收款通道", "借我用"],
    "裸聊敲诈": ["裸聊", "录下来了", "通讯录", "发给你的同学", "社死"],
    "境外高薪": ["境外", "月薪过万", "包机票", "园区", "护照发我", "海外直招"],
    "内部渠道投资": ["内部渠道", "稳赚", "内部消息", "日化", "保本高收益", "老师带你"],
    "冒充客服退款": ["三倍赔付", "质量问题", "快递丢了", "理赔", "退款通道"],
    "紧急借钱": ["急用钱", "先借我", "明天就还", "马上还你", "我真的很急"],
    "伪造官方身份": ["客服", "专员", "稽查", "清算部"],

    # 校园常见变种
    "校园收费": ["教辅材料", "班费", "统一采购", "班群", "缴费通知"],
    "培训推销": ["保过", "包过", "上岸率", "早鸟价", "锁名额", "压题", "押题卷"],
    "票务代抢": ["内场票", "看台票", "主办方", "电子票", "锁票"],
    "涉密套取": ["实验数据", "设备清单", "课题数据", "数据给我", "署二作",
              "联合课题", "学术交流", "对比一下数据"],
    "低价钓鱼": ["先付款", "先付定金", "验机", "急出", "抵债", "先付一半"],

    # 2026-11-18 holdout v1 暴露的三类缺口（属于"没覆盖"，不是"调参"）
    "虚假中奖": ["一等奖", "中奖", "抽奖活动", "缴纳个人所得税", "领奖",
              "奖金", "名额保留"],
    "荐股带单": ["荐股", "交流群", "老师带", "涨停", "席位费", "回本",
              "带单", "荐股群"],
    "会销引流": ["免费体检", "送鸡蛋", "专家现场", "优惠套餐", "会销",
              "健康讲座", "免费送"],
}

# ---- 组合规则：两个条件同时出现才算命中（用来接住"下载/扫码/验证码"这类泛词）----
# 结构：名称 -> (必须出现的词, 还须出现其一的词)
TEXT_RULE_GROUPS = {
    "索要验证码": (["验证码", "校验码", "动态码"],
                ["发我", "给我", "提供", "告诉我", "说一下", "念一下",
                 "填", "输入", "报一下", "报给", "收到后"]),
    "诱导下载": (["下载", "安装", "装个", "下个"],
                ["app", "软件", "这个", "链接", "包", "客户端"]),
    "扫码引流": (["扫码", "扫一下", "扫这个", "二维码"],
                ["领", "进群", "下载", "支付", "转账", "添加", "客服"]),
    "加好友引流": (["加好友", "加个好友", "通过一下"],
                 ["手机号", "微信", "qq", "号"]),
}

FILE_RULES = {
    "涉密文件名": ["内部文件", "严禁外传", "涉密", "机密", "不准外传", "绝密"],
    "可疑脚本": [".php", ".exe", ".bat", ".sh", ".vbs", ".js", ".jar", ".scr", ".msi", "payload"],
    "安卓安装包": [".apk", ".ipa", ".dmg"],
    "可疑网页文件": [".html", ".url", ".hta"],
}

URL_RE = re.compile(r"https?://[^\s\u4e00-\u9fff，。；、）】]+", re.I)
DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9][a-z0-9-]{0,62}\.)+(?:com|cn|net|org|top|xyz|cc|vip|shop|link|ml|tk|buzz|icu)\b",
    re.I,
)


def _has(text_lower, kws):
    return any(k.lower() in text_lower for k in kws)


def _match(text_lower, names_text_lower):
    """返回命中的规则名列表"""
    hits = []
    for name, kws in TEXT_RULES.items():
        if _has(text_lower, kws):
            hits.append(name)
    for name, (a, b) in TEXT_RULE_GROUPS.items():
        if _has(text_lower, a) and _has(text_lower, b):
            hits.append(name)
    for name, kws in FILE_RULES.items():
        if _has(names_text_lower, kws):
            hits.append("文件:" + name)
    return hits


def main(transcript: str, extra: str) -> dict:
    s = (transcript or "").strip()

    fence = chr(96) * 3
    if s.startswith(fence):
        s = s[len(fence):].lstrip()
    if s.endswith(fence):
        s = s[:-len(fence)].rstrip()

    a, b = s.find("["), s.rfind("]")
    if 0 <= a < b:
        s = s[a:b + 1]

    try:
        msgs = json.loads(s)
        if isinstance(msgs, dict) and msgs.get("error") == "NO_IMAGE":
            return {"payload": json.dumps({
                "ok": False, "count": 0, "turns": 0, "files": [],
                "rule_hits": [], "carriers": [], "messages": [],
                "note": "没收到图片：请先上传一张聊天截图",
            }, ensure_ascii=False)}
        if isinstance(msgs, dict) and msgs.get("error") == "NO_TEXT":
            return {"payload": json.dumps({
                "ok": False, "count": 0, "turns": 0, "files": [],
                "rule_hits": [], "carriers": [], "messages": [],
                "note": "没收到文本：请先贴一段聊天记录",
            }, ensure_ascii=False)}
        if not isinstance(msgs, list):
            raise ValueError("not list")
        ok = True
    except Exception:
        msgs, ok = [], False

    if not ok:
        return {"payload": json.dumps({
            "ok": False, "count": 0, "turns": 0, "files": [],
            "rule_hits": [], "carriers": [], "messages": [],
            "note": "转录结果不是合法 JSON，已降级",
        }, ensure_ascii=False)}

    for m in msgs:
        m["text"] = re.sub(r"\s+", " ", (m.get("text") or "")).strip()
        if m.get("type") == "transfer":
            m["speaker"] = "unknown"

    texts = [m["text"] for m in msgs if m.get("type") == "text"]
    names = [m.get("name") or "" for m in msgs if m.get("type") == "file"]
    jt = "\n".join(texts)
    jn = "\n".join(names)
    all_text = jt + "\n" + jn

    hits = _match(jt.lower(), jn.lower())

    # 载体提取：链接 / 域名（去重、保序）
    carriers = []
    seen = set()
    for u in URL_RE.findall(all_text):
        u = u.rstrip(".,;)】")
        if u and u not in seen:
            seen.add(u)
            carriers.append({"type": "url", "value": u})
    for d in DOMAIN_RE.findall(all_text):
        d = d.lower()
        if d not in seen:
            seen.add(d)
            carriers.append({"type": "domain", "value": d})

    if carriers and "可疑链接" not in hits:
        hits.append("可疑链接")

    return {"payload": json.dumps({
        "ok": True,
        "count": len(msgs),
        "turns": len(texts),
        "files": names,
        "rule_hits": hits,
        "carriers": carriers,
        "messages": msgs,
    }, ensure_ascii=False)}
