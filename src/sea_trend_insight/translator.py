from __future__ import annotations

import json
import logging
import re
from typing import Any

log = logging.getLogger("sea_trend_insight")

PHRASE_ZH: dict[str, str] = {
    "mpl ph season 14": "MPL菲律宾联赛 第14赛季",
    "mpl id season 14": "MPL印尼联赛 第14赛季",
    "genshin impact 5.0": "原神5.0版本",
    "genshin impact cosplay challenge": "原神Cos挑战",
    "valorant champions tour": "无畏契约冠军巡回赛",
    "free fire indonesia championship": "Free Fire印尼锦标赛",
    "ragnarok origin thailand": "仙境传说泰服上线",
    "rov pro league": "传说对决(泰服)职业联赛",
    "mlbb arlott gameplay": "无尽对决 阿洛特实机玩法",
    "typhoon carina": "台风卡琳娜",
    "bangkok flood warning": "曼谷洪水预警",
    "bangkok street food tiktok": "曼谷街头美食短视频",
    "thailand gdp growth": "泰国GDP增长",
    "thailand digital wallet": "泰国数字钱包政策",
    "edsa traffic plan": "EDSA大道交通规划",
    "philhealth contribution": "菲律宾国民健保缴费",
    "jakarta mrt extension": "雅加达地铁延伸工程",
    "miss universe philippines 2026": "2026菲律宾环球小姐",
    "bali tourism record": "巴厘岛旅游纪录",
    "muay thai world championship": "泰拳世锦赛",
    "songkran preparation": "泼水节筹备",
    "thai bl drama": "泰国耽美剧",
    "jollibee chickenjoy meme": "快乐蜂炸鸡乐梗",
    "indomie recipe challenge": "营多面食谱挑战",
    "citayam fashion week": "Citayam街头时装周",
    "indonesian food review viral": "印尼美食测评爆火",
    "sb19 pagtatag": "SB19乐队PAGTATAG巡演",
    "balikAral dance challenge": "BalikAral返校舞蹈挑战",
    "balikaral dance challenge": "BalikAral返校舞蹈挑战",
    "harga beras naik": "米价上涨",
    "pemilu 2026": "2026印尼大选",
}

TERM_ZH: dict[str, str] = {
    "genshin impact": "原神",
    "mobile legends": "无尽对决",
    "mlbb": "无尽对决",
    "valorant": "无畏契约",
    "free fire": "自由之火",
    "ragnarok origin": "仙境传说新启航",
    "ragnarok": "仙境传说",
    "honkai star rail": "崩坏星穹铁道",
    "honkai": "崩坏",
    "wuthering waves": "鸣潮",
    "zenless zone zero": "绝区零",
    "nikke": "胜利女神",
    "tower of fantasy": "幻塔",
    "pubg": "绝地求生",
    "call of duty": "使命召唤",
    "minecraft": "我的世界",
    "roblox": "罗布乐思",
    "fortnite": "堡垒之夜",
    "apex legends": "Apex英雄",
    "league of legends": "英雄联盟",
    "arena of valor": "传说对决",
    "rov": "传说对决",
    "clash of clans": "部落冲突",
    "mpl": "MPL职业联赛",
    "pro league": "职业联赛",
    "championship": "锦标赛",
    "champions tour": "冠军巡回赛",
    "esport": "电竞",
    "season": "赛季",
    "finals": "总决赛",
    "gameplay": "实机玩法",
    "gacha": "抽卡",
    "battle royale": "大逃杀",
    "cosplay": "Cos",
    "update": "更新",
    "typhoon": "台风",
    "earthquake": "地震",
    "flood warning": "洪水预警",
    "flood": "洪水",
    "election": "选举",
    "gdp growth": "GDP增长",
    "digital wallet": "数字钱包",
    "power outage": "停电",
    "traffic plan": "交通规划",
    "world championship": "世锦赛",
    "tourism record": "旅游纪录",
    "dance challenge": "舞蹈挑战",
    "recipe challenge": "食谱挑战",
    "street food": "街头美食",
    "food review": "美食测评",
    "bl drama": "耽美剧",
    "viral": "爆火",
    "meme": "梗",
    "challenge": "挑战",
    "mukbang": "吃播",
    "tiktok": "短视频",
    "songkran": "泼水节",
    "muay thai": "泰拳",
    "jollibee": "快乐蜂",
    "indomie": "营多面",
    "pemilu": "大选",
    "philhealth": "菲国健保",
    "edsa": "EDSA大道",
    "bangkok": "曼谷",
    "jakarta": "雅加达",
    "bali": "巴厘岛",
    "preparation": "筹备",
    "contribution": "缴费",
    "extension": "延伸",
    "miss universe": "环球小姐",
}


def _has_cjk(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            return True
    return False


def annotate_zh(text: str) -> str:
    if _has_cjk(text):
        return text

    lower = text.lower().strip()

    if lower in PHRASE_ZH:
        return f"{text}（{PHRASE_ZH[lower]}）"

    for phrase, zh in sorted(PHRASE_ZH.items(), key=lambda x: len(x[0]), reverse=True):
        if phrase in lower:
            return f"{text}（{zh}）"

    for term, zh in sorted(TERM_ZH.items(), key=lambda x: len(x[0]), reverse=True):
        if term in lower:
            return f"{text}（{zh}）"

    if lower in _llm_cache and _llm_cache[lower]:
        return f"{text}（{_llm_cache[lower]}）"

    return text


_llm_cache: dict[str, str] = {}


def batch_translate_zh(keywords: list[str], llm_cfg: dict[str, Any]) -> dict[str, str]:
    """Translate a list of keywords to Chinese using LLM. Returns {original: zh}."""
    need = []
    for kw in keywords:
        low = kw.lower().strip()
        if low not in _llm_cache and not _has_cjk(kw) and annotate_zh(kw) == kw:
            need.append(kw)

    if not need:
        return {kw: _llm_cache.get(kw.lower().strip(), "") for kw in keywords}

    from sea_trend_insight.llm import call_json

    BATCH = 40
    for i in range(0, len(need), BATCH):
        batch = need[i:i + BATCH]
        prompt = (
            "将以下东南亚热搜关键词翻译为简短的中文（不超过15字）。"
            "如果是人名则音译，如果是泰语/印尼语/菲律宾语则翻译含义。"
            "返回 JSON 对象，key 是原文，value 是中文翻译。\n\n"
            + json.dumps(batch, ensure_ascii=False)
        )
        try:
            result = call_json(
                [{"role": "user", "content": prompt}],
                llm_cfg,
                temperature=0.1,
            )
            if isinstance(result, dict):
                for k, v in result.items():
                    _llm_cache[k.lower().strip()] = v
                log.info("LLM translated %d/%d keywords", len(result), len(batch))
        except Exception as e:
            log.warning("LLM translation batch failed: %s", e)

    return {kw: _llm_cache.get(kw.lower().strip(), "") for kw in keywords}
