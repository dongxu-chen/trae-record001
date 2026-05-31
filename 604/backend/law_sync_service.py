import json
import os
import logging
import hashlib
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

LAW_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "law_database")
LAW_DB_FILE = os.path.join(LAW_DB_DIR, "law_articles.json")
SYNC_RECORD_FILE = os.path.join(LAW_DB_DIR, "sync_record.json")
SYNC_INTERVAL_DAYS = 7


class LawSyncService:
    OFFICIAL_SOURCES = {
        "全国人大": "http://www.npc.gov.cn/npc/c2194/list.shtml",
        "国务院": "http://www.gov.cn/zhengfa/",
    }

    def __init__(self):
        self._laws: Dict[str, Dict[str, Any]] = {}
        self._last_sync: Optional[str] = None
        os.makedirs(LAW_DB_DIR, exist_ok=True)
        self._load_local_db()

    def _load_local_db(self):
        if os.path.exists(LAW_DB_FILE):
            try:
                with open(LAW_DB_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._laws = data.get("laws", {})
                    self._last_sync = data.get("last_sync")
                logger.info(f"法条库加载成功: {len(self._laws)} 条")
            except Exception as e:
                logger.error(f"法条库加载失败: {e}")
                self._init_default_laws()
        else:
            self._init_default_laws()

        if os.path.exists(SYNC_RECORD_FILE):
            try:
                with open(SYNC_RECORD_FILE, 'r', encoding='utf-8') as f:
                    record = json.load(f)
                    self._last_sync = record.get("last_sync", self._last_sync)
            except:
                pass

    def _init_default_laws(self):
        self._laws = {
            "民法典-第一百四十三条": {
                "content": "具备下列条件的民事法律行为有效：（一）行为人具有相应的民事行为能力；（二）意思表示真实；（三）不违反法律、行政法规的强制性规定，不违背公序良俗。",
                "source": "民法典",
                "chapter": "总则编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "民法典-第一百四十四条": {
                "content": "无民事行为能力人实施的民事法律行为无效。",
                "source": "民法典",
                "chapter": "总则编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "民法典-第一百四十五条": {
                "content": "限制民事行为能力人实施的纯获利益的民事法律行为或者与其年龄、智力、精神健康状况相适应的民事法律行为有效；实施的其他民事法律行为经法定代理人同意或者追认后有效。",
                "source": "民法典",
                "chapter": "总则编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "民法典-第五百零二条": {
                "content": "依法成立的合同，自成立时生效，但是法律另有规定或者当事人另有约定的除外。",
                "source": "民法典",
                "chapter": "合同编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "民法典-第五百零九条": {
                "content": "当事人应当按照约定全面履行自己的义务。当事人应当遵循诚信原则，根据合同的性质、目的和交易习惯履行通知、协助、保密等义务。",
                "source": "民法典",
                "chapter": "合同编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "民法典-第五百七十七条": {
                "content": "当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。",
                "source": "民法典",
                "chapter": "合同编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "民法典-第五百八十五条": {
                "content": "当事人可以约定一方违约时应当根据违约情况向对方支付一定数额的违约金，也可以约定因违约产生的损失赔偿额的计算方法。",
                "source": "民法典",
                "chapter": "合同编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "民法典-第六百六十七条": {
                "content": "借款合同是借款人向贷款人借款，到期返还借款并支付利息的合同。",
                "source": "民法典",
                "chapter": "合同编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "民法典-第六百七十九条": {
                "content": "自然人之间的借款合同，自贷款人提供借款时成立。",
                "source": "民法典",
                "chapter": "合同编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "民法典-第六百八十条": {
                "content": "禁止高利放贷，借款的利率不得违反国家有关规定。借款合同对支付利息没有约定的，视为没有利息。借款合同对支付利息约定不明确，当事人不能达成补充协议的，按照当地或者当事人的交易方式、交易习惯、市场利率等因素确定利息；自然人之间借款的，视为没有利息。",
                "source": "民法典",
                "chapter": "合同编",
                "effective_date": "2021-01-01",
                "status": "有效",
                "hash": "",
            },
            "刑法-第二百六十四条": {
                "content": "盗窃公私财物，数额较大的，或者多次盗窃、入户盗窃、携带凶器盗窃、扒窃的，处三年以下有期徒刑、拘役或者管制，并处或者单处罚金；数额巨大或者有其他严重情节的，处三年以上十年以下有期徒刑，并处罚金；数额特别巨大或者有其他特别严重情节的，处十年以上有期徒刑或者无期徒刑，并处罚金或者没收财产。",
                "source": "刑法",
                "chapter": "侵犯财产罪",
                "effective_date": "2021-03-01",
                "status": "有效",
                "hash": "",
            },
            "刑法-第二百六十六条": {
                "content": "诈骗公私财物，数额较大的，处三年以下有期徒刑、拘役或者管制，并处或者单处罚金；数额巨大或者有其他严重情节的，处三年以上十年以下有期徒刑，并处罚金；数额特别巨大或者有其他特别严重情节的，处十年以上有期徒刑或者无期徒刑，并处罚金或者没收财产。",
                "source": "刑法",
                "chapter": "侵犯财产罪",
                "effective_date": "2021-03-01",
                "status": "有效",
                "hash": "",
            },
            "刑法-第二百三十四条": {
                "content": "故意伤害他人身体的，处三年以下有期徒刑、拘役或者管制。犯前款罪，致人重伤的，处三年以上十年以下有期徒刑；致人死亡或者以特别残忍手段致人重伤造成严重残疾的，处十年以上有期徒刑、无期徒刑或者死刑。",
                "source": "刑法",
                "chapter": "侵犯公民人身权利、民主权利罪",
                "effective_date": "2021-03-01",
                "status": "有效",
                "hash": "",
            },
            "刑法-第六十七条": {
                "content": "犯罪以后自动投案，如实供述自己的罪行的，是自首。对于自首的犯罪分子，可以从轻或者减轻处罚。其中，犯罪较轻的，可以免除处罚。",
                "source": "刑法",
                "chapter": "总则",
                "effective_date": "2021-03-01",
                "status": "有效",
                "hash": "",
            },
            "刑法-第六十五条": {
                "content": "被判处有期徒刑以上刑罚的犯罪分子，刑罚执行完毕或者赦免以后，在五年以内再犯应当判处有期徒刑以上刑罚之罪的，是累犯，应当从重处罚，但是过失犯罪和不满十八周岁的人犯罪的除外。",
                "source": "刑法",
                "chapter": "总则",
                "effective_date": "2021-03-01",
                "status": "有效",
                "hash": "",
            },
            "民事诉讼法-第六十七条": {
                "content": "当事人对自己提出的主张，有责任提供证据。",
                "source": "民事诉讼法",
                "chapter": "证据",
                "effective_date": "2022-01-01",
                "status": "有效",
                "hash": "",
            },
            "民事诉讼法-第一百二十二条": {
                "content": "起诉必须符合下列条件：（一）原告是与本案有直接利害关系的公民、法人和其他组织；（二）有明确的被告；（三）有具体的诉讼请求和事实、理由；（四）属于人民法院受理民事诉讼的范围和受诉人民法院管辖。",
                "source": "民事诉讼法",
                "chapter": "审判程序",
                "effective_date": "2022-01-01",
                "status": "有效",
                "hash": "",
            },
            "劳动法-第五十条": {
                "content": "工资应当以货币形式按月支付给劳动者本人。不得克扣或者无故拖欠劳动者的工资。",
                "source": "劳动法",
                "chapter": "工资",
                "effective_date": "1995-01-01",
                "status": "有效",
                "hash": "",
            },
            "劳动合同法-第四十七条": {
                "content": "经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付。六个月以上不满一年的，按一年计算；不满六个月的，向劳动者支付半个月工资的经济补偿。",
                "source": "劳动合同法",
                "chapter": "劳动合同的解除和终止",
                "effective_date": "2008-01-01",
                "status": "有效",
                "hash": "",
            },
        }
        for law_id, law_data in self._laws.items():
            law_data["hash"] = self._compute_hash(law_data["content"])
        self._save_to_disk()

    def _compute_hash(self, content: str) -> str:
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _save_to_disk(self):
        data = {
            "laws": self._laws,
            "last_sync": self._last_sync,
            "version": "2.0",
            "updated_at": datetime.now().isoformat(),
        }
        try:
            with open(LAW_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"法条库已保存: {len(self._laws)} 条")
        except Exception as e:
            logger.error(f"法条库保存失败: {e}")

    def get_law(self, law_id: str) -> Optional[Dict[str, Any]]:
        return self._laws.get(law_id)

    def get_all_laws(self) -> Dict[str, Dict[str, Any]]:
        return self._laws.copy()

    def get_law_content(self, law_id: str) -> str:
        law = self._laws.get(law_id, {})
        return law.get("content", "")

    def search_laws(self, keyword: str, source: str = None) -> List[Dict[str, Any]]:
        results = []
        for law_id, law_data in self._laws.items():
            if source and law_data.get("source") != source:
                continue
            if keyword in law_data.get("content", "") or keyword in law_id:
                results.append({
                    "law_id": law_id,
                    **law_data
                })
        return results

    def get_laws_by_source(self, source: str) -> Dict[str, Dict[str, Any]]:
        return {
            law_id: law_data
            for law_id, law_data in self._laws.items()
            if law_data.get("source") == source
        }

    def add_or_update_law(self, law_id: str, content: str, source: str, chapter: str = "", effective_date: str = "", status: str = "有效"):
        content_hash = self._compute_hash(content)
        if law_id in self._laws:
            existing = self._laws[law_id]
            if existing.get("hash") == content_hash:
                return False
            existing["content"] = content
            existing["hash"] = content_hash
            existing["source"] = source
            existing["chapter"] = chapter
            existing["effective_date"] = effective_date
            existing["status"] = status
            existing["updated_at"] = datetime.now().isoformat()
            logger.info(f"法条更新: {law_id}")
        else:
            self._laws[law_id] = {
                "content": content,
                "source": source,
                "chapter": chapter,
                "effective_date": effective_date,
                "status": status,
                "hash": content_hash,
                "created_at": datetime.now().isoformat(),
            }
            logger.info(f"法条新增: {law_id}")
        self._save_to_disk()
        return True

    def needs_sync(self) -> bool:
        if not self._last_sync:
            return True
        try:
            last = datetime.fromisoformat(self._last_sync)
            return (datetime.now() - last).days >= SYNC_INTERVAL_DAYS
        except:
            return True

    def sync_from_official(self) -> Dict[str, Any]:
        sync_result = {
            "success": False,
            "added": 0,
            "updated": 0,
            "unchanged": 0,
            "errors": [],
            "sync_time": datetime.now().isoformat(),
        }

        try:
            logger.info("开始从官方源同步法条数据...")

            crawled = self._crawl_official_sources()

            for law_id, law_data in crawled.items():
                content = law_data.get("content", "")
                if not content:
                    continue
                changed = self.add_or_update_law(
                    law_id=law_id,
                    content=content,
                    source=law_data.get("source", ""),
                    chapter=law_data.get("chapter", ""),
                    effective_date=law_data.get("effective_date", ""),
                    status=law_data.get("status", "有效"),
                )
                if changed:
                    if law_id in self._laws and self._laws[law_id].get("created_at") != self._laws[law_id].get("updated_at"):
                        sync_result["updated"] += 1
                    else:
                        sync_result["added"] += 1
                else:
                    sync_result["unchanged"] += 1

            self._last_sync = datetime.now().isoformat()
            sync_record = {
                "last_sync": self._last_sync,
                "result": sync_result,
            }
            with open(SYNC_RECORD_FILE, 'w', encoding='utf-8') as f:
                json.dump(sync_record, f, ensure_ascii=False, indent=2)

            self._save_to_disk()
            sync_result["success"] = True
            logger.info(f"法条同步完成: 新增{sync_result['added']}, 更新{sync_result['updated']}, 未变{sync_result['unchanged']}")

        except Exception as e:
            sync_result["errors"].append(str(e))
            logger.error(f"法条同步失败: {e}")

        return sync_result

    def _crawl_official_sources(self) -> Dict[str, Dict[str, Any]]:
        crawled = {}
        try:
            import urllib.request
            for source_name, url in self.OFFICIAL_SOURCES.items():
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        html = response.read().decode('utf-8', errors='ignore')
                        parsed = self._parse_law_html(html, source_name)
                        crawled.update(parsed)
                except Exception as e:
                    logger.warning(f"从{source_name}抓取失败: {e}")
                    sync_fallback = self._get_sync_fallback(source_name)
                    crawled.update(sync_fallback)
        except ImportError:
            logger.warning("urllib不可用，使用备用法条数据")
            crawled = self._get_sync_fallback("all")

        return crawled

    def _parse_law_html(self, html: str, source: str) -> Dict[str, Dict[str, Any]]:
        parsed = {}
        article_patterns = [
            r'第[一二三四五六七八九十百千\d]+条\s*([^第]+?)(?=第[一二三四五六七八九十百千\d]+条|$)',
        ]
        for pattern in article_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for i, content in enumerate(matches):
                content = re.sub(r'<[^>]+>', '', content).strip()
                content = re.sub(r'\s+', ' ', content).strip()
                if len(content) > 10:
                    law_id = f"{source}-第{self._num_to_chinese(i + 1)}条"
                    parsed[law_id] = {
                        "content": content,
                        "source": source,
                        "chapter": "",
                        "effective_date": "",
                        "status": "有效",
                    }
        return parsed

    def _num_to_chinese(self, num: int) -> str:
        mapping = list("零一二三四五六七八九")
        if num < 10:
            return mapping[num]
        if num < 20:
            return "十" + (mapping[num - 10] if num > 10 else "")
        if num < 100:
            tens = num // 10
            ones = num % 10
            return mapping[tens] + "十" + (mapping[ones] if ones else "")
        if num < 1000:
            hundreds = num // 100
            remainder = num % 100
            result = mapping[hundreds] + "百"
            if remainder == 0:
                return result
            if remainder < 10:
                return result + "零" + mapping[remainder]
            return result + self._num_to_chinese(remainder)
        return str(num)

    def _get_sync_fallback(self, source: str) -> Dict[str, Dict[str, Any]]:
        fallback = {
            "民法典-第五百七十九条": {
                "content": "当事人一方未支付价款、报酬、租金、利息，或者不履行其他金钱债务的，对方可以请求其支付。",
                "source": "民法典",
                "chapter": "合同编",
                "effective_date": "2021-01-01",
                "status": "有效",
            },
            "刑法-第二百六十三条": {
                "content": "以暴力、胁迫或者其他方法抢劫公私财物的，处三年以上十年以下有期徒刑，并处罚金；有下列情形之一的，处十年以上有期徒刑、无期徒刑或者死刑，并处罚金或者没收财产。",
                "source": "刑法",
                "chapter": "侵犯财产罪",
                "effective_date": "2021-03-01",
                "status": "有效",
            },
            "刑法-第七十二条": {
                "content": "对于被判处拘役、三年以下有期徒刑的犯罪分子，同时符合下列条件的，可以宣告缓刑，对其中不满十八周岁的人、怀孕的妇女和已满七十五周岁的人，应当宣告缓刑。",
                "source": "刑法",
                "chapter": "总则",
                "effective_date": "2021-03-01",
                "status": "有效",
            },
        }
        if source == "all":
            return fallback
        return {k: v for k, v in fallback.items() if v.get("source") == source}

    def get_sync_status(self) -> Dict[str, Any]:
        return {
            "total_laws": len(self._laws),
            "last_sync": self._last_sync,
            "needs_sync": self.needs_sync(),
            "sync_interval_days": SYNC_INTERVAL_DAYS,
            "sources": list(self.OFFICIAL_SOURCES.keys()),
            "law_sources": {
                source: len([l for l in self._laws.values() if l.get("source") == source])
                for source in set(l.get("source", "") for l in self._laws.values())
            },
        }

    def get_laws_for_knowledge_graph(self) -> Dict[str, str]:
        return {
            law_id: law_data.get("content", "")
            for law_id, law_data in self._laws.items()
            if law_data.get("status") == "有效"
        }

    def force_sync(self) -> Dict[str, Any]:
        self._last_sync = None
        return self.sync_from_official()


law_sync_service = LawSyncService()
