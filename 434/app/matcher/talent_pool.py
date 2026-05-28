import hashlib
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

from app.models.schemas import (
    ResumeData,
    TalentPoolRecord,
    DedupResult,
)


class TalentPool:
    def __init__(self):
        self._records: Dict[str, TalentPoolRecord] = {}
        self._phone_index: Dict[str, List[str]] = {}
        self._email_index: Dict[str, List[str]] = {}
        self._name_index: Dict[str, List[str]] = {}
        self._fingerprint_index: Dict[str, List[str]] = {}

    def generate_fingerprint(self, resume: ResumeData) -> str:
        fingerprint_parts = []

        if resume.candidate_name:
            fingerprint_parts.append(resume.candidate_name.strip().lower())

        if resume.phone:
            phone_clean = re.sub(r"\D", "", resume.phone)
            if len(phone_clean) >= 7:
                fingerprint_parts.append(phone_clean)

        if resume.email:
            fingerprint_parts.append(resume.email.strip().lower())

        skill_sig = "".join(sorted([s.lower().strip() for s in resume.skills[:10]]))
        fingerprint_parts.append(skill_sig[:50])

        if resume.work_experience:
            companies = []
            for exp in resume.work_experience[:3]:
                company = exp.get("company", "")
                if company:
                    companies.append(company.strip().lower())
            if companies:
                fingerprint_parts.append("|".join(companies))

        fingerprint_str = "||".join(fingerprint_parts)

        hasher = hashlib.sha256()
        hasher.update(fingerprint_str.encode("utf-8"))
        return hasher.hexdigest()[:32]

    def generate_short_fingerprint(self, resume: ResumeData) -> str:
        name = (resume.candidate_name or "").strip().lower()
        phone = re.sub(r"\D", "", resume.phone or "")[:7]
        email = (resume.email or "").strip().lower().split("@")[0]

        short_key = f"{name}|{phone}|{email}"
        hasher = hashlib.md5()
        hasher.update(short_key.encode("utf-8"))
        return hasher.hexdigest()[:16]

    def check_duplicate(
        self,
        resume: ResumeData,
        threshold: float = 0.85,
    ) -> DedupResult:
        short_fp = self.generate_short_fingerprint(resume)
        candidates = []

        if resume.phone:
            phone_clean = re.sub(r"\D", "", resume.phone)
            for record_id in self._phone_index.get(phone_clean, []):
                if record_id not in candidates:
                    candidates.append(record_id)

        if resume.email:
            email_key = resume.email.strip().lower()
            for record_id in self._email_index.get(email_key, []):
                if record_id not in candidates:
                    candidates.append(record_id)

        if resume.candidate_name:
            name_key = resume.candidate_name.strip().lower()
            for record_id in self._name_index.get(name_key, []):
                if record_id not in candidates:
                    candidates.append(record_id)

        for record_id in self._fingerprint_index.get(short_fp, []):
            if record_id not in candidates:
                candidates.append(record_id)

        best_match = None
        best_score = 0.0
        matched_fields = []

        for record_id in candidates:
            record = self._records.get(record_id)
            if not record or record.status == "blacklisted":
                continue

            score, fields = self._compute_similarity(resume, record.resume)
            if score > best_score:
                best_score = score
                best_match = record
                matched_fields = fields

        if best_score >= threshold:
            return DedupResult(
                is_duplicate=True,
                confidence=best_score,
                duplicate_with=best_match.record_id,
                duplicate_candidate=best_match.candidate_name,
                matched_fields=matched_fields,
                suggestion="建议合并或更新现有记录，避免重复推荐",
            )

        return DedupResult(
            is_duplicate=False,
            confidence=best_score,
            suggestion="可以安全入库，无明显重复",
        )

    def _compute_similarity(
        self, resume1: ResumeData, resume2: ResumeData
    ) -> Tuple[float, List[str]]:
        score = 0.0
        matched_fields = []
        total_weight = 0.0

        weights = {
            "phone": 0.30,
            "email": 0.25,
            "name": 0.15,
            "skills": 0.15,
            "work": 0.10,
            "education": 0.05,
        }

        if resume1.phone and resume2.phone:
            phone1_clean = re.sub(r"\D", "", resume1.phone)
            phone2_clean = re.sub(r"\D", "", resume2.phone)
            if phone1_clean == phone2_clean and len(phone1_clean) >= 7:
                score += weights["phone"]
                matched_fields.append("phone")
                if len(phone1_clean) >= 11:
                    score += 0.10
            total_weight += weights["phone"]

        if resume1.email and resume2.email:
            email1 = resume1.email.strip().lower()
            email2 = resume2.email.strip().lower()
            if email1 == email2:
                score += weights["email"]
                matched_fields.append("email")
            total_weight += weights["email"]

        if resume1.candidate_name and resume2.candidate_name:
            name1 = resume1.candidate_name.strip().lower()
            name2 = resume2.candidate_name.strip().lower()
            if name1 == name2 and len(name1) >= 2:
                score += weights["name"]
                matched_fields.append("name")
            total_weight += weights["name"]

        skills1 = set([s.lower().strip() for s in resume1.skills])
        skills2 = set([s.lower().strip() for s in resume2.skills])
        if skills1 and skills2:
            intersection = skills1 & skills2
            union = skills1 | skills2
            skill_sim = len(intersection) / len(union) if union else 0
            if skill_sim > 0.5:
                score += weights["skills"] * skill_sim
                matched_fields.append("skills")
        total_weight += weights["skills"]

        companies1 = set([
            exp.get("company", "").strip().lower()
            for exp in resume1.work_experience
            if exp.get("company")
        ])
        companies2 = set([
            exp.get("company", "").strip().lower()
            for exp in resume2.work_experience
            if exp.get("company")
        ])
        if companies1 & companies2:
            score += weights["work"]
            matched_fields.append("work_experience")
        total_weight += weights["work"]

        schools1 = set([
            edu.get("school", "").strip().lower()
            for edu in resume1.education
            if edu.get("school")
        ])
        schools2 = set([
            edu.get("school", "").strip().lower()
            for edu in resume2.education
            if edu.get("school")
        ])
        if schools1 & schools2:
            score += weights["education"]
            matched_fields.append("education")
        total_weight += weights["education"]

        normalized_score = score / total_weight if total_weight > 0 else 0
        return min(normalized_score, 1.0), matched_fields

    def add_record(
        self,
        resume: ResumeData,
        source: Optional[str] = None,
        force: bool = False,
    ) -> Tuple[TalentPoolRecord, DedupResult]:
        dedup_result = self.check_duplicate(resume)

        if dedup_result.is_duplicate and not force:
            existing = self._records.get(dedup_result.duplicate_with)
            return existing, dedup_result

        fingerprint = self.generate_fingerprint(resume)
        short_fp = self.generate_short_fingerprint(resume)
        record_id = f"TP{datetime.now().strftime('%Y%m%d%H%M%S')}{len(self._records):04d}"

        record = TalentPoolRecord(
            record_id=record_id,
            candidate_name=resume.candidate_name or "未知候选人",
            phone=resume.phone,
            email=resume.email,
            resume=resume,
            fingerprint=fingerprint,
            source=source,
            tags=self._auto_tag(resume),
        )

        self._records[record_id] = record

        if resume.phone:
            phone_clean = re.sub(r"\D", "", resume.phone)
            if phone_clean not in self._phone_index:
                self._phone_index[phone_clean] = []
            if record_id not in self._phone_index[phone_clean]:
                self._phone_index[phone_clean].append(record_id)

        if resume.email:
            email_key = resume.email.strip().lower()
            if email_key not in self._email_index:
                self._email_index[email_key] = []
            if record_id not in self._email_index[email_key]:
                self._email_index[email_key].append(record_id)

        if resume.candidate_name:
            name_key = resume.candidate_name.strip().lower()
            if name_key not in self._name_index:
                self._name_index[name_key] = []
            if record_id not in self._name_index[name_key]:
                self._name_index[name_key].append(record_id)

        if short_fp not in self._fingerprint_index:
            self._fingerprint_index[short_fp] = []
        if record_id not in self._fingerprint_index[short_fp]:
            self._fingerprint_index[short_fp].append(record_id)

        dedup_result = DedupResult(
            is_duplicate=False,
            confidence=0.0,
            suggestion="已成功加入人才库",
        )

        return record, dedup_result

    def _auto_tag(self, resume: ResumeData) -> List[str]:
        tags = []

        skills_lower = [s.lower() for s in resume.skills]

        tech_stacks = {
            "Python技术栈": ["python", "django", "flask", "fastapi"],
            "Java技术栈": ["java", "spring", "springboot"],
            "前端开发": ["javascript", "typescript", "react", "vue", "angular"],
            "Go技术栈": ["go", "golang", "gin", "echo"],
            "数据开发": ["hadoop", "spark", "hive", "flink"],
            "算法/AI": ["tensorflow", "pytorch", "机器学习", "深度学习"],
            "云原生": ["docker", "kubernetes", "k8s", "云原生"],
            "数据库专家": ["mysql", "postgresql", "mongodb", "redis"],
        }

        for tag, keywords in tech_stacks.items():
            if any(kw in skills_lower for kw in keywords):
                tags.append(tag)

        total_years = 0
        for exp in resume.work_experience:
            try:
                start = exp.get("start_date", "")
                end = exp.get("end_date", "至今")
                start_year = int(re.search(r"\d{4}", start).group()) if re.search(r"\d{4}", start) else 2020
                if end in ("至今", "现在", "present", ""):
                    end_year = 2026
                else:
                    end_year = int(re.search(r"\d{4}", end).group()) if re.search(r"\d{4}", end) else 2020
                total_years += max(0, end_year - start_year)
            except Exception:
                pass

        if total_years >= 5:
            tags.append("资深")
        elif total_years >= 3:
            tags.append("中级")
        else:
            tags.append("初级")

        return tags[:8]

    def get_record(self, record_id: str) -> Optional[TalentPoolRecord]:
        return self._records.get(record_id)

    def search_records(
        self,
        keyword: Optional[str] = None,
        skills: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[TalentPoolRecord]:
        results = []
        keyword_lower = keyword.lower() if keyword else None
        skills_lower = [s.lower() for s in skills] if skills else None

        for record in self._records.values():
            if status and record.status != status:
                continue

            if tags and not any(t in record.tags for t in tags):
                continue

            if skills_lower:
                resume_skills = [s.lower() for s in record.resume.skills]
                if not any(s in resume_skills for s in skills_lower):
                    continue

            if keyword_lower:
                text_fields = [
                    record.candidate_name.lower(),
                    record.resume.full_text.lower(),
                    " ".join(record.tags).lower(),
                ]
                if not any(keyword_lower in field for field in text_fields):
                    continue

            results.append(record)
            if len(results) >= limit:
                break

        return results

    def get_recent_additions(self, days: int = 7) -> List[TalentPoolRecord]:
        cutoff = datetime.now() - timedelta(days=days)
        return [
            record
            for record in self._records.values()
            if record.added_time >= cutoff
        ]

    def update_record_status(self, record_id: str, status: str) -> bool:
        record = self._records.get(record_id)
        if record:
            record.status = status
            record.last_updated = datetime.now()
            return True
        return False

    def get_statistics(self) -> dict:
        total = len(self._records)
        active = len([r for r in self._records.values() if r.status == "active"])
        archived = len([r for r in self._records.values() if r.status == "archived"])
        blacklisted = len([r for r in self._records.values() if r.status == "blacklisted"])
        recent = len(self.get_recent_additions(7))

        tag_counts = {}
        for record in self._records.values():
            for tag in record.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_records": total,
            "active_records": active,
            "archived_records": archived,
            "blacklisted_records": blacklisted,
            "recent_additions_7d": recent,
            "tag_distribution": tag_counts,
        }