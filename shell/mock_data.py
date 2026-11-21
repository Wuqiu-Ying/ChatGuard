#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据模块（只在演示/联调时被 api.py 加载）

约定：
- api.py 里不存放任何判定样本；
- 请求带 {"demo": true} 时，api.py 动态 import 本模块并原样返回；
- 真实链路不可用时，壳子会主动降级到这里，保证演示不中断。

加新场景：往 SCENARIOS 里加一条，key 用英文短名。
"""

# 一次真实跑出来的结果（示例场景：熟人互发"内部文件" + 脚本文件 + 5 元转账）
SUSPICIOUS = {
    "ok": True,
    "transcript": {"count": 33, "turns": 19},
    "rules": {"hits": ["文件:涉密文件名", "文件:可疑脚本"]},
    "judgment": {
        "verdict": "suspicious",
        "level": "high",
        "take": ["info", "action"],
        "persona": ["acquaintance", "peer"],
        "lever": ["bond", "authority"],
        "victim_state": "none",
        "evidence": [
            {"quote": "rce_test.php",
             "why": "PHP 可执行脚本，\"rce\"通常指远程代码执行，是典型的攻击测试或恶意载荷命名，不像普通文档。"},
            {"quote": "【内部文件 严禁外传】关于向博...的通知.pdf",
             "why": "\"内部文件/严禁外传\"是制造稀缺与权威感的常见手法，配合仅 1.3KB 的体积，更像诱饵。"},
            {"quote": "明天你过来的时候帮我打印一下资料",
             "why": "用\"打印资料\"这种正当理由降低警惕，诱导你在别处打开这两个文件。"},
        ],
        "hypotheses": [
            {"name": "账号被盗/被控", "confidence": 0.85,
             "supports": "发来攻击性文件名，且与日常话题错位",
             "against": "对话有自然铺垫，转账是双向的"},
            {"name": "熟人技术玩笑", "confidence": 0.15,
             "supports": "关系亲密、互道爱意，可能对方在测试脚本",
             "against": "伪造\"严禁外传\"的文件并不像玩笑"},
        ],
        "rule_check": "命中两条均来自文件名，不是对话内容，属\"技术特征\"而非\"对话行为\"。",
        "identity_check": "通过电话/视频/当面确认：1) 是否真的发了这两个文件 2) 为什么要打印 .php 3) 那个\"内部通知\"是什么。切勿在当前聊天窗口里确认。",
        "what_to_do": [
            "绝对不要打开或打印 rce_test.php",
            "不要打开那个 1.3KB 的 PDF",
            "换渠道核实对方身份",
            "如确认账号异常，提醒对方改密",
        ],
        "uncertain": [
            "对方是否计算机安全方向，这会不会是\"硬核玩笑\"？",
            "你事先知道他要发这两个文件吗？",
            "那个 PDF 会不会只是个空壳或快捷方式？",
        ],
        "one_line": "可能是账号被盗用于投递恶意脚本，也可能是极不恰当的熟人技术玩笑；先电话核验身份，绝对不要打开那个 PHP 文件。",
        "disclaimer": "AI 判断，仅供参考，不构成法律结论。",
    },
    "meta": {"secs": 35, "demo": True},
}

# 刷单话术（红色样例，用于演示"高置信度直判"）
SCAM = {
    "ok": True,
    "transcript": None,
    "rules": {"hits": ["垫付刷单"]},
    "judgment": {
        "verdict": "likely_scam",
        "level": "critical",
        "take": ["money"],
        "persona": ["stranger", "recruiter"],
        "lever": ["benefit", "urgency"],
        "victim_state": "none",
        "evidence": [
            {"quote": "先垫付三单，做完连本带利返给你",
             "why": "刷单诈骗的核心句式：先出钱、后返现，钱一旦出去就不会回来。"},
            {"quote": "第一单 298，加我 V：abc12345",
             "why": "用小额降低戒心，同时把你拉去私聊，脱离平台留证。"},
        ],
        "hypotheses": [
            {"name": "典型刷单返利诈骗", "confidence": 0.93,
             "supports": "垫付+返利+脱离平台三要素齐全",
             "against": "暂无相反证据"},
            {"name": "正规兼职（可能性极低）", "confidence": 0.07,
             "supports": "确实存在\"兼职\"这一外壳",
             "against": "正规兼职不会要求先垫钱"},
        ],
        "rule_check": "命中\"垫付刷单\"，与对话内容一致，属高可信。",
        "identity_check": "不必核实对方是谁——这个话术本身就是结论。直接停止接触。",
        "what_to_do": [
            "不要转任何钱，一分都不要",
            "不要加对方私人微信/QQ",
            "保存截图后举报该账号",
            "如已转账，立即拨打 96110",
        ],
        "uncertain": ["你是否已经转过钱？金额多少？"],
        "one_line": "这是典型的刷单诈骗话术，先垫付后返现是骗局核心，请立即停止接触并举报。",
        "disclaimer": "AI 判断，仅供参考，不构成法律结论。",
    },
    "meta": {"secs": 18, "demo": True},
}

# 无明显风险（用于演示"暂未发现"与追问）
CLEAN = {
    "ok": True,
    "transcript": None,
    "rules": {"hits": []},
    "judgment": {
        "verdict": "insufficient",
        "level": "low",
        "take": [], "persona": ["acquaintance"], "lever": [],
        "victim_state": "none",
        "evidence": [],
        "hypotheses": [
            {"name": "普通日常沟通", "confidence": 0.7,
             "supports": "内容为约饭、时间地点，无索取动作",
             "against": "你把它拿来询问，说明有某处让你不安"},
            {"name": "存在未说出口的风险点", "confidence": 0.3,
             "supports": "主动求证本身是一个信号",
             "against": "本案所有内容中未出现金钱、链接或身份索取"},
        ],
        "rule_check": "未命中任何规则——但\"没命中\"只代表没抓到关键词。",
        "identity_check": "如果是熟人，建议打个电话确认近况；不必在当前聊天里追问。",
        "what_to_do": ["正常沟通即可，但留意后续是否出现借钱、链接或验证码要求"],
        "uncertain": [
            "到底是什么让你觉得不对劲？",
            "对方最近有没有换过账号、借过钱、或者突然换了聊天风格？",
            "你们平时会这么说话吗？",
        ],
        "one_line": "目前看到的这部分只是日常聊天，暂未发现风险；但这只代表\"看到的这部分\"没问题，如果后面出现谈钱、要验证码、让你下载软件，请再发我一次。",
        "disclaimer": "AI 判断，仅供参考，不构成法律结论。",
    },
    "meta": {"secs": 16, "demo": True},
}

SCENARIOS = {"suspicious": SUSPICIOUS, "scam": SCAM, "clean": CLEAN}


def get(name=None):
    """取一个演示场景；name 为空时返回 suspicious。"""
    return SCENARIOS.get(name or "suspicious", SUSPICIOUS)


# ---------------------------------------------------------------------------
# B 端（学校工作台）演示数据
# 重要：按 08/11 的设计，学校端**只能看到事件，看不到聊天原文**
#   - 不含 quote / 原文 / 聊天内容
#   - 学生用匿名 ID（校内映射由学校自己维护）
#   - 摘要字段 status: pending / contacted / closed
# ---------------------------------------------------------------------------

B_SCHOOL = "某大学 · 学生工作处"

B_STATS = {
    "week_total": 128,     # 本周研判量
    "pending": 6,          # 待处理
    "high": 2,             # 高危（P0/P1）
    "students": 41,        # 涉及学生数
    "delta": "+12%",
}

B_EVENTS = [
    {
        "id": "E-2f31", "anon": "S-4F2A", "type": "刷单返利", "level": "critical",
        "at": "11-18 14:20", "victim_state": "money_lost",
        "action": "已产生资金损失，建议今日内电话联系本人",
        "status": "pending",
        "timeline": [
            {"t": "11-18 13:58", "what": "对方引导下载陌生 APP"},
            {"t": "11-18 14:05", "what": "对方要求垫付 298 元做任务"},
            {"t": "11-18 14:19", "what": "用户完成首次转账"},
        ],
    },
    {
        "id": "E-2f30", "anon": "S-9C11", "type": "涉密信息套取", "level": "high",
        "at": "11-18 11:02", "victim_state": "none",
        "action": "涉及实验室信息，建议转保密部门复核（已进入人工复核队列）",
        "status": "pending",
        "timeline": [
            {"t": "11-18 10:40", "what": "对方以学术合作名义索取实验数据"},
            {"t": "11-18 10:55", "what": "对方要求不要告知导师"},
        ],
    },
    {
        "id": "E-2f29", "anon": "S-1A73", "type": "冒充客服退款", "level": "high",
        "at": "11-17 21:40", "victim_state": "info_leaked",
        "action": "已提供验证码，建议立即协助改密并关注账户异动",
        "status": "contacted",
        "timeline": [
            {"t": "11-17 21:22", "what": "对方自称平台客服要求核验信息"},
            {"t": "11-17 21:38", "what": "用户提供了短信验证码"},
        ],
    },
    {
        "id": "E-2f28", "anon": "S-7B02", "type": "兼职押金", "level": "medium",
        "at": "11-17 16:10", "victim_state": "money_lost",
        "action": "金额较小，建议班会上做一次案例提醒",
        "status": "pending",
        "timeline": [{"t": "11-17 15:50", "what": "对方以工号费名义收取 198 元"}],
    },
    {
        "id": "E-2f27", "anon": "S-3D55", "type": "裸聊敲诈", "level": "critical",
        "at": "11-17 01:12", "victim_state": "in_danger",
        "action": "P0：存在影像要挟，建议立即联系并协助报警",
        "status": "contacted",
        "timeline": [
            {"t": "11-17 00:50", "what": "对方诱导视频通话"},
            {"t": "11-17 01:10", "what": "对方以影像要挟索要钱款"},
        ],
    },
    {
        "id": "E-2f26", "anon": "S-6E80", "type": "游戏账号交易", "level": "medium",
        "at": "11-16 19:30", "victim_state": "none",
        "action": "已劝阻成功，建议保持关注",
        "status": "closed",
        "timeline": [{"t": "11-16 19:20", "what": "对方要求走非官方交易平台"}],
    },
]

B_WEEKLY = {
    "range": "11-11 ~ 11-17",
    "top_scripts": [
        {"name": "先垫付后返现（刷单）", "count": 23},
        {"name": "退款要先验证码", "count": 17},
        {"name": "内部文件 / 严禁外传", "count": 9},
        {"name": "脱离平台私下转账", "count": 8},
        {"name": "加私人微信继续聊", "count": 6},
    ],
    "by_type": [
        {"type": "刷单返利", "count": 38},
        {"type": "冒充客服", "count": 26},
        {"type": "兼职押金", "count": 22},
        {"type": "游戏账号", "count": 19},
        {"type": "涉密套取", "count": 9},
        {"type": "其他", "count": 14},
    ],
    "done": {"研判": 128, "预警": 23, "已联系": 17, "待处理": 6},
}


def get_b_events():
    return {"ok": True, "school": B_SCHOOL, "stats": B_STATS, "events": B_EVENTS}


def get_b_weekly():
    return {"ok": True, "school": B_SCHOOL, "weekly": B_WEEKLY}


# ---------------------------------------------------------------------------
# G 端（执法 / 运营商 / 监管）演示数据
# 按 09 §4.2 的字段白名单：只有"载体线索"和"趋势"，没有任何个人身份与原文
# ---------------------------------------------------------------------------

G_ROLES = {
    "telecom": {
        "title": "运营商 · 涉诈载体线索",
        "sub": "用于关停、拦截、加黑。不含受害人身份、不含聊天内容。",
        "visible": ["载体值", "类型", "被报告次数", "首次/最近", "可伪造度"],
        "hidden": ["当事人身份", "聊天原文", "精确到个人的时间戳"],
    },
    "police": {
        "title": "反诈中心 · 态势与线索",
        "sub": "用于预警发布与线索发现。个案追溯须走法定程序。",
        "visible": ["类型分布", "话术变种", "载体线索（去人化）", "区域趋势"],
        "hidden": ["当事人身份", "聊天原文", "事件级明细"],
    },
    "edu": {
        "title": "教育主管 · 高校反诈态势",
        "sub": "用于考核与资源投放。各校只看到自己的明细，主管看到的是聚合。",
        "visible": ["各校研判量", "预警量", "处置率", "季度趋势"],
        "hidden": ["学生身份", "聊天原文", "单个事件"],
    },
}

G_CARRIERS = [
    {"v": "138****1234", "t": "手机号", "n": 15, "first": "11-10", "last": "11-16", "forge": "高", "note": "疑似改号，同一号段多号轮换"},
    {"v": "http://abc-xx.top/join", "t": "短链", "n": 9, "first": "11-12", "last": "11-17", "forge": "中", "note": "落地页已 404"},
    {"v": "chatg_safe.apk", "t": "安装包", "n": 7, "first": "11-14", "last": "11-18", "forge": "低", "note": "包名伪装成安全工具"},
    {"v": "wxid_9fk2****", "t": "社交账号", "n": 12, "first": "11-11", "last": "11-18", "forge": "低", "note": "多起刷单话术共用"},
    {"v": "6222****8899", "t": "收款账户", "n": 23, "first": "11-09", "last": "11-18", "forge": "低", "note": "资金归集账户"},
    {"v": "95588", "t": "被冒用官方号", "n": 4, "first": "11-15", "last": "11-17", "forge": "—", "note": "白名单：永不进黑名单，仅提示"},
]

G_TYPES = [
    {"type": "刷单返利", "count": 412, "delta": "+18%"},
    {"type": "冒充客服退款", "count": 287, "delta": "+6%"},
    {"type": "兼职押金", "count": 196, "delta": "+22%"},
    {"type": "游戏账号交易", "count": 154, "delta": "-4%"},
    {"type": "涉密信息套取", "count": 23, "delta": "+9%"},
    {"type": "裸聊敲诈", "count": 61, "delta": "+3%"},
]

G_VARIANTS = [
    {"name": "三单连做 / 系统卡单", "type": "刷单返利", "seen": 88},
    {"name": "退款要先给验证码", "type": "冒充客服", "seen": 71},
    {"name": "「内部文件 严禁外传」伪装附件", "type": "涉密套取", "seen": 19},
    {"name": "加我 V / 换平台聊", "type": "通用", "seen": 143},
    {"name": "押金入职费，做满退你", "type": "兼职押金", "seen": 64},
]

G_SCHOOLS = [
    {"name": "示例大学A", "n": 128, "warn": 23, "done": 17, "rate": "73.9%"},
    {"name": "示例学院B", "n": 96, "warn": 18, "done": 12, "rate": "66.7%"},
    {"name": "示例学院C", "n": 74, "warn": 11, "done": 9, "rate": "81.8%"},
    {"name": "黑龙江交通职业技术学院", "n": 62, "warn": 14, "done": 8, "rate": "57.1%"},
    {"name": "示例学院D", "n": 41, "warn": 7, "done": 6, "rate": "85.7%"},
]

G_QUARTER = [
    {"m": "9月", "n": 88}, {"m": "10月", "n": 176}, {"m": "11月", "n": 401},
]


def get_g(view="telecom"):
    role = G_ROLES.get(view, G_ROLES["telecom"])
    out = {"ok": True, "view": view, "role": role, "updated": "2026-11-18 08:00"}
    if view == "telecom":
        out["carriers"] = G_CARRIERS
    elif view == "police":
        out["types"] = G_TYPES
        out["variants"] = G_VARIANTS
        out["carriers"] = G_CARRIERS[:4]
    else:
        out["schools"] = G_SCHOOLS
        out["quarter"] = G_QUARTER
    return out
