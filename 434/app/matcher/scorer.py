import re
import math
from typing import List, Tuple, Dict, Optional

from app.models.schemas import ResumeData, JobDescription, MatchResult, MatchReason
from app.parser.nlp_processor import NLPProcessor
from app.utils.text_utils import compute_levenshtein_similarity, compute_jaccard_similarity


class MatchScorer:
    def __init__(self, nlp_processor: NLPProcessor):
        self.nlp = nlp_processor
        self.weights = {
            "skill": 0.35,
            "experience": 0.25,
            "education": 0.15,
            "project": 0.15,
            "semantic": 0.10,
        }
        self.skill_vocab = self._build_skill_vocab()

    def _build_skill_vocab(self) -> Dict[str, int]:
        common_skills = [
            "python", "java", "javascript", "typescript", "go", "golang", "rust",
            "c++", "c#", "c", "php", "ruby", "swift", "kotlin", "scala", "r", "matlab",
            "react", "vue", "angular", "next.js", "nuxt", "svelte", "jquery",
            "django", "flask", "fastapi", "spring", "springboot", "express", "nestjs",
            "gin", "echo", "fiber", "laravel", "rails",
            "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "oracle",
            "sqlserver", "sqlite", "dynamodb", "cassandra",
            "docker", "kubernetes", "k8s", "jenkins", "gitlab", "github", "git", "svn",
            "linux", "unix", "windows", "macos", "aws", "azure", "gcp", "aliyun", "tencent",
            "tensorflow", "pytorch", "keras", "sklearn", "pandas", "numpy", "opencv",
            "html", "html5", "css", "css3", "sass", "less", "webpack", "vite",
            "restful", "graphql", "grpc", "websocket", "mqtt", "kafka", "rabbitmq",
            "agile", "scrum", "jira", "confluence",
        ]
        return {skill: idx for idx, skill in enumerate(common_skills)}

    def score_resume(self, resume: ResumeData, job: JobDescription) -> MatchResult:
        skill_score, skill_matched, skill_missing = self._score_skills(resume, job)
        experience_score, exp_detail = self._score_experience(resume, job)
        education_score, edu_detail = self._score_education(resume, job)
        project_score, proj_detail = self._score_projects(resume, job)
        semantic_score, sem_detail = self._score_semantic(resume, job)

        overall = (
            skill_score * self.weights["skill"]
            + experience_score * self.weights["experience"]
            + education_score * self.weights["education"]
            + project_score * self.weights["project"]
            + semantic_score * self.weights["semantic"]
        )

        reasons = []
        if skill_matched:
            reasons.append(MatchReason(
                category="技能匹配",
                detail=f"已匹配技能: {', '.join(skill_matched[:10])}",
                score=skill_score,
                weight=self.weights["skill"],
            ))
        if skill_missing:
            reasons.append(MatchReason(
                category="技能缺失",
                detail=f"缺失技能: {', '.join(skill_missing[:10])}",
                score=0.0,
                weight=0.0,
            ))
        reasons.append(MatchReason(
            category="经验匹配",
            detail=exp_detail,
            score=experience_score,
            weight=self.weights["experience"],
        ))
        reasons.append(MatchReason(
            category="学历匹配",
            detail=edu_detail,
            score=education_score,
            weight=self.weights["education"],
        ))
        reasons.append(MatchReason(
            category="项目匹配",
            detail=proj_detail,
            score=project_score,
            weight=self.weights["project"],
        ))
        reasons.append(MatchReason(
            category="语义匹配",
            detail=sem_detail,
            score=semantic_score,
            weight=self.weights["semantic"],
        ))

        return MatchResult(
            candidate_name=resume.candidate_name or "未知候选人",
            overall_score=round(overall, 4),
            skill_score=round(skill_score, 4),
            experience_score=round(experience_score, 4),
            education_score=round(education_score, 4),
            project_score=round(project_score, 4),
            match_reasons=reasons,
            interview_questions=[],
        )

    def rank_candidates(self, resumes: List[ResumeData], job: JobDescription) -> List[MatchResult]:
        results = []
        for resume in resumes:
            result = self.score_resume(resume, job)
            results.append(result)
        results.sort(key=lambda r: r.overall_score, reverse=True)
        return results

    def _score_skills(self, resume: ResumeData, job: JobDescription) -> Tuple[float, List[str], List[str]]:
        if not job.required_skills:
            return 1.0, [], []

        resume_skills_lower = [s.lower() for s in resume.skills]
        required_skills_lower = [s.lower() for s in job.required_skills]

        vector_size = len(self.skill_vocab)
        resume_vec = [0.0] * vector_size
        job_vec = [0.0] * vector_size

        for skill in resume_skills_lower:
            idx = self._find_skill_index(skill)
            if idx is not None:
                resume_vec[idx] = 1.0

        for skill in required_skills_lower:
            idx = self._find_skill_index(skill)
            if idx is not None:
                job_vec[idx] = 1.0

        resume_norm = self._l2_normalize(resume_vec)
        job_norm = self._l2_normalize(job_vec)

        cosine_similarity = self._dot_product(resume_norm, job_norm)

        matched = []
        missing = []
        for req_skill in required_skills_lower:
            found = False
            for res_skill in resume_skills_lower:
                if req_skill == res_skill or req_skill in res_skill or res_skill in req_skill:
                    matched.append(req_skill)
                    found = True
                    break
            if not found:
                missing.append(req_skill)

        base_score, _, _ = self.nlp.compute_skill_match(resume.skills, job.required_skills)
        final_score = cosine_similarity * 0.6 + base_score * 0.4

        return final_score, matched, missing

    def _find_skill_index(self, skill: str) -> Optional[int]:
        skill_lower = skill.lower()
        for vocab_skill, idx in self.skill_vocab.items():
            if vocab_skill == skill_lower or vocab_skill in skill_lower or skill_lower in vocab_skill:
                return idx
        return None

    def _l2_normalize(self, vector: List[float]) -> List[float]:
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            return vector
        return [x / norm for x in vector]

    def _dot_product(self, vec1: List[float], vec2: List[float]) -> float:
        return sum(a * b for a, b in zip(vec1, vec2))

    def _score_experience(self, resume: ResumeData, job: JobDescription) -> Tuple[float, str]:
        total_years = 0
        exp_descriptions = []

        for exp in resume.work_experience:
            years = self._extract_years(exp.get("start_date", ""), exp.get("end_date", ""))
            total_years += years
            if exp.get("description"):
                exp_descriptions.append(exp["description"])

        job_years_range = self._parse_experience_expression(job.min_experience_years)
        job_min_years = job_years_range["min"]
        job_max_years = job_years_range["max"]
        job_preferred_years = job_years_range["preferred"]

        if job_min_years > 0:
            if total_years >= job_min_years:
                if total_years <= job_max_years:
                    year_score = 1.0
                else:
                    overage = total_years - job_max_years
                    year_score = max(0.8, 1.0 - overage * 0.05)
            else:
                year_score = total_years / job_min_years * 0.7
        else:
            year_score = 0.5 if total_years > 0 else 0.0

        desc_score = 0.0
        if exp_descriptions and job.description:
            combined_exp = " ".join(exp_descriptions)
            desc_score = self.nlp.compute_similarity_bert(combined_exp, job.description)

        score = year_score * 0.5 + desc_score * 0.5

        range_desc = self._format_range_description(job_years_range)
        detail = f"工作经验约 {total_years:.1f} 年（要求{range_desc}），岗位经验相关度: {desc_score:.2f}"
        return score, detail

    def _parse_experience_expression(self, expr) -> Dict[str, float]:
        if isinstance(expr, (int, float)):
            num = float(expr)
            return {
                "min": num,
                "max": num + 2.0,
                "preferred": num + 1.0,
                "type": "exact"
            }

        expr_str = str(expr).lower().strip()

        patterns = [
            (r"(\d+(?:\.\d+)?)\s*[-~至到]\s*(\d+(?:\.\d+)?)\s*年?", "range"),
            (r"(\d+(?:\.\d+)?)\s*年以上?", "above"),
            (r"(\d+(?:\.\d+)?)\s*\+\s*年?", "above"),
            (r">=\s*(\d+(?:\.\d+)?)\s*年?", "above"),
            (r"(\d+(?:\.\d+)?)\s*年以下?", "below"),
            (r"<=\s*(\d+(?:\.\d+)?)\s*年?", "below"),
            (r"约\s*(\d+(?:\.\d+)?)\s*年", "about"),
            (r"(\d+(?:\.\d+)?)\s*年左右", "about"),
            (r"(\d+(?:\.\d+)?)\s*年", "exact"),
        ]

        for pattern, ptype in patterns:
            match = re.search(pattern, expr_str)
            if match:
                if ptype == "range":
                    min_y = float(match.group(1))
                    max_y = float(match.group(2))
                    return {
                        "min": min_y,
                        "max": max_y,
                        "preferred": (min_y + max_y) / 2,
                        "type": "range",
                        "raw": expr_str
                    }
                elif ptype == "above":
                    min_y = float(match.group(1))
                    return {
                        "min": min_y,
                        "max": min_y + 5.0,
                        "preferred": min_y + 2.0,
                        "type": "above",
                        "raw": expr_str
                    }
                elif ptype == "below":
                    max_y = float(match.group(1))
                    return {
                        "min": 0.0,
                        "max": max_y,
                        "preferred": max_y * 0.7,
                        "type": "below",
                        "raw": expr_str
                    }
                elif ptype == "about":
                    target = float(match.group(1))
                    return {
                        "min": max(0.0, target - 1.0),
                        "max": target + 1.0,
                        "preferred": target,
                        "type": "about",
                        "raw": expr_str
                    }
                elif ptype == "exact":
                    target = float(match.group(1))
                    return {
                        "min": target,
                        "max": target + 2.0,
                        "preferred": target + 1.0,
                        "type": "exact",
                        "raw": expr_str
                    }

        return {
            "min": 0.0,
            "max": 10.0,
            "preferred": 3.0,
            "type": "unknown",
            "raw": expr_str
        }

    def _format_range_description(self, range_info: Dict) -> str:
        rtype = range_info.get("type", "exact")
        if rtype == "range":
            return f"{range_info['min']:.0f}-{range_info['max']:.0f}年"
        elif rtype == "above":
            return f"{range_info['min']:.0f}年以上"
        elif rtype == "below":
            return f"{range_info['max']:.0f}年以下"
        elif rtype == "about":
            return f"约{range_info['preferred']:.0f}年"
        else:
            return f"{range_info['min']:.0f}年以上"

    def _score_education(self, resume: ResumeData, job: JobDescription) -> Tuple[float, str]:
        if not resume.education:
            return 0.0, "未找到教育经历"

        level_map = {
            "博士": 5, "phd": 5, "doctor": 5,
            "硕士": 4, "master": 4, "研究生": 4,
            "本科": 3, "bachelor": 3, "学士": 3,
            "大专": 2, "college": 2, "associate": 2,
            "高中": 1, "high school": 1,
            "中专": 1, "technical secondary": 1,
        }

        highest = 0
        edu_detail = ""
        for edu in resume.education:
            lvl = edu.get("level", "")
            if lvl:
                val = level_map.get(lvl.lower(), 0)
                if val > highest:
                    highest = val
                    edu_detail = f"{edu.get('school', '')} {lvl}"

        min_req = level_map.get(job.min_education.lower(), 3)

        if highest >= min_req:
            score = 1.0
        elif highest == 0:
            score = 0.2
            edu_detail = "未识别到明确学历"
        else:
            score = highest / min_req * 0.6

        return score, edu_detail or "学历信息不完整"

    def _score_projects(self, resume: ResumeData, job: JobDescription) -> Tuple[float, str]:
        if not resume.projects:
            return 0.0, "无项目经验"

        project_texts = []
        for proj in resume.projects:
            desc = proj.get("description", "")
            name = proj.get("name", "")
            project_texts.append(f"{name} {desc}".strip())

        if not project_texts:
            return 0.0, "项目描述为空"

        combined = " ".join(project_texts)
        score = self.nlp.compute_similarity_bert(combined, job.description)

        detail = f"共 {len(resume.projects)} 个项目经验，相关度: {score:.2f}"
        return score, detail

    def _score_semantic(self, resume: ResumeData, job: JobDescription) -> Tuple[float, str]:
        resume_text = resume.full_text or resume.raw_text
        if not resume_text:
            return 0.0, "简历文本为空"

        similarity = self.nlp.compute_similarity_bert(resume_text, job.description)
        detail = f"简历与岗位描述语义相似度: {similarity:.2f}"
        return similarity, detail

    def _extract_years(self, start: str, end: str) -> float:
        try:
            start_year = int(re.search(r"\d{4}", start).group()) if re.search(r"\d{4}", start) else 2020
            if end in ("至今", "现在", "present", ""):
                end_year = 2026
            else:
                end_year = int(re.search(r"\d{4}", end).group()) if re.search(r"\d{4}", end) else 2020
            return max(0.0, end_year - start_year)
        except (ValueError, AttributeError):
            return 0.0