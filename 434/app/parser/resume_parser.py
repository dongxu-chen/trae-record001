import os
import re
import tempfile
from typing import Optional

from pypdf import PdfReader
import pdfplumber
from docx import Document

from app.models.schemas import ResumeData
from app.utils.text_utils import clean_text


class ResumeParser:
    def __init__(self):
        self._init_patterns()

    def _init_patterns(self):
        self.name_pattern = re.compile(r"(?:姓\s*名[:：]?\s*|^)([\u4e00-\u9fa5]{2,4})(?:\s|$)", re.MULTILINE)
        self.phone_pattern = re.compile(r"(?:1[3-9]\d{9}|\+?\d{1,3}[-\s]?\d{3,4}[-\s]?\d{4})")
        self.email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        self.education_keywords = ["教育背景", "教育经历", "学历", "学习经历", "Education"]
        self.work_keywords = ["工作经历", "工作经验", "职业经历", "Work Experience", "Experience"]
        self.project_keywords = ["项目经验", "项目经历", "Projects", "Project"]
        self.skill_keywords = ["专业技能", "技能", "技术栈", "Skills", "Skill"]
        self.cert_keywords = ["证书", "资质", "Certifications", "Certs"]
        self.language_keywords = ["语言", "Language"]
        self.education_levels = {
            "博士": 5, "phd": 5, "doctor": 5,
            "硕士": 4, "master": 4, "研究生": 4,
            "本科": 3, "bachelor": 3, "学士": 3,
            "大专": 2, "college": 2, "associate": 2,
            "高中": 1, "high school": 1,
            "中专": 1, "technical secondary": 1,
        }

    def parse(self, file_path: str) -> ResumeData:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            text = self._extract_pdf_text(file_path)
        elif ext in (".docx", ".doc"):
            text = self._extract_docx_text(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        text = clean_text(text)
        return self._extract_resume_data(text)

    def parse_bytes(self, content: bytes, filename: str) -> ResumeData:
        ext = os.path.splitext(filename)[1].lower()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        try:
            tmp.write(content)
            tmp.close()
            return self.parse(tmp.name)
        finally:
            os.unlink(tmp.name)

    def _extract_pdf_text(self, file_path: str) -> str:
        text_parts = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        except Exception:
            try:
                reader = PdfReader(file_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            except Exception:
                raise ValueError("Failed to extract text from PDF")
        return "\n".join(text_parts)

    def _extract_docx_text(self, file_path: str) -> str:
        try:
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        except Exception:
            raise ValueError("Failed to extract text from Word document")

    def _extract_resume_data(self, text: str) -> ResumeData:
        data = ResumeData(full_text=text, raw_text=text)

        name_match = self.name_pattern.search(text)
        if name_match:
            data.candidate_name = name_match.group(1).strip()

        phone_match = self.phone_pattern.search(text)
        if phone_match:
            data.phone = phone_match.group(0)

        email_match = self.email_pattern.search(text)
        if email_match:
            data.email = email_match.group(0)

        sections = self._split_sections(text)

        data.skills = self._extract_skills(sections, text)
        data.work_experience = self._extract_work_experience(sections, text)
        data.education = self._extract_education(sections, text)
        data.projects = self._extract_projects(sections, text)
        data.certifications = self._extract_list_items(sections, self.cert_keywords)
        data.languages = self._extract_list_items(sections, self.language_keywords)

        return data

    def _split_sections(self, text: str) -> dict:
        sections = {}
        lines = text.split("\n")
        current_section = "other"
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_content:
                    sections.setdefault(current_section, []).append("\n".join(current_content))
                    current_content = []
                continue

            matched = False
            for keyword in self.education_keywords + self.work_keywords + self.project_keywords + self.skill_keywords + self.cert_keywords + self.language_keywords:
                if keyword.lower() in stripped.lower() and len(stripped) < 30:
                    if current_content:
                        sections.setdefault(current_section, []).append("\n".join(current_content))
                    current_section = self._map_keyword_to_section(keyword)
                    current_content = []
                    matched = True
                    break

            if not matched:
                current_content.append(stripped)

        if current_content:
            sections.setdefault(current_section, []).append("\n".join(current_content))

        return sections

    def _map_keyword_to_section(self, keyword: str) -> str:
        keyword_lower = keyword.lower()
        if keyword_lower in [k.lower() for k in self.education_keywords]:
            return "education"
        if keyword_lower in [k.lower() for k in self.work_keywords]:
            return "work"
        if keyword_lower in [k.lower() for k in self.project_keywords]:
            return "project"
        if keyword_lower in [k.lower() for k in self.skill_keywords]:
            return "skill"
        if keyword_lower in [k.lower() for k in self.cert_keywords]:
            return "certification"
        if keyword_lower in [k.lower() for k in self.language_keywords]:
            return "language"
        return "other"

    def _extract_skills(self, sections: dict, full_text: str) -> list:
        skills = []
        skill_text = " ".join(sections.get("skill", []))
        if not skill_text:
            skill_text = full_text

        tech_patterns = [
            r"\b(?:python|java|c\+\+|c#|javascript|typescript|go|golang|rust|swift|kotlin|ruby|php|scala|r|matlab)\b",
            r"\b(?:react|vue|angular|next\.js|nuxt|svelte)\b",
            r"\b(?:django|flask|fastapi|spring|express|nestjs|gin|echo|fiber)\b",
            r"\b(?:mysql|postgresql|mongodb|redis|elasticsearch|oracle|sqlserver|sqlite)\b",
            r"\b(?:docker|kubernetes|k8s|jenkins|gitlab|github|git|svn)\b",
            r"\b(?:linux|unix|windows|macos|aws|azure|gcp|aliyun|tencent)\b",
            r"\b(?:tensorflow|pytorch|keras|scikit-learn|sklearn|pandas|numpy|opencv)\b",
            r"\b(?:html5?|css3?|sass|less|webpack|vite|gulp|grunt)\b",
            r"\b(?:restful?|graphql|grpc|websocket|mqtt|kafka|rabbitmq)\b",
            r"\b(?:敏捷|scrum|jira|confluence)\b",
            r"(?:[\u4e00-\u9fa5]+开发|[\u4e00-\u9fa5]+架构|[\u4e00-\u9fa5]+分析)",
        ]

        all_matches = set()
        for pattern in tech_patterns:
            matches = re.findall(pattern, skill_text, re.IGNORECASE)
            all_matches.update(matches)

        skills = list(all_matches)

        common_skills = [
            "python", "java", "javascript", "typescript", "go", "rust",
            "react", "vue", "angular",
            "django", "flask", "fastapi", "spring", "express",
            "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
            "docker", "kubernetes", "jenkins", "git",
            "linux", "aws", "azure", "gcp",
            "tensorflow", "pytorch", "sklearn", "pandas", "numpy",
            "html", "css", "sass", "webpack",
            "restful", "graphql", "kafka", "rabbitmq",
        ]
        for cs in common_skills:
            if cs.lower() in skill_text.lower() and cs not in skills:
                skills.append(cs)

        return skills[:50]

    def _extract_work_experience(self, sections: dict, full_text: str) -> list:
        work_text = " ".join(sections.get("work", []))
        if not work_text:
            work_text = full_text

        experiences = []
        pattern = re.compile(
            r"(\d{4}[.\-/年]\s*\d{0,2}[.\-/月]?)\s*[-–~至到]\s*(\d{4}[.\-/年]\s*\d{0,2}[.\-/月]?|至今|现在|present)"
            r"(.*?)(?=\d{4}[.\-/年]\s*\d{0,2}[.\-/月]?\s*[-–~至到]|$)",
            re.DOTALL
        )
        matches = pattern.findall(work_text)

        for start, end, desc in matches:
            exp = {
                "start_date": start.strip(),
                "end_date": end.strip(),
                "description": desc.strip()[:500],
            }
            company_match = re.search(r"(?:在|于|@|@)\s*([^\s,，。.；;]{2,30})\s*(?:公司|集团|科技|有限)", desc)
            if company_match:
                exp["company"] = company_match.group(1)
            position_match = re.search(r"(?:担任|任职|职位|role|position)\s*[:：]?\s*([^\s,，。.；;]{2,30})", desc, re.IGNORECASE)
            if position_match:
                exp["position"] = position_match.group(1)
            experiences.append(exp)

        return experiences[:20]

    def _extract_education(self, sections: dict, full_text: str) -> list:
        edu_text = " ".join(sections.get("education", []))
        if not edu_text:
            edu_text = full_text

        educations = []
        pattern = re.compile(
            r"(\d{4}[.\-/年])\s*[-–~至到]\s*(\d{4}[.\-/年]|至今|现在)"
            r"(.*?)(?=\d{4}[.\-/年]|$)",
            re.DOTALL
        )
        matches = pattern.findall(edu_text)

        for start, end, desc in matches:
            edu = {
                "start_date": start.strip(),
                "end_date": end.strip(),
                "description": desc.strip()[:500],
            }
            level = self._extract_education_level(desc)
            if level:
                edu["level"] = level
            school_match = re.search(r"([\u4e00-\u9fa5]{2,20}(?:大学|学院|学校|University|College|Institute))", desc, re.IGNORECASE)
            if school_match:
                edu["school"] = school_match.group(1)
            major_match = re.search(r"(?:专业|major)\s*[:：]?\s*([\u4e00-\u9fa5a-zA-Z\s]{2,30})", desc, re.IGNORECASE)
            if major_match:
                edu["major"] = major_match.group(1).strip()
            educations.append(edu)

        return educations[:10]

    def _extract_education_level(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for level, _ in sorted(self.education_levels.items(), key=lambda x: x[1], reverse=True):
            if level in text_lower:
                return level
        return None

    def _extract_projects(self, sections: dict, full_text: str) -> list:
        project_text = " ".join(sections.get("project", []))
        if not project_text:
            project_text = full_text

        projects = []
        pattern = re.compile(
            r"(?:项目名称|project|项目)[:：]?\s*([^\n,，。.；;]{2,50})",
            re.IGNORECASE
        )
        matches = pattern.findall(project_text)

        project_blocks = re.split(r"(?:\n\s*\n|\n(?=\d{4}))", project_text)
        for block in project_blocks:
            if len(block.strip()) > 20:
                proj = {"description": block.strip()[:500]}
                name_match = re.search(r"(?:项目名称|项目)[:：]?\s*([^\n,，。.；;]{2,50})", block)
                if name_match:
                    proj["name"] = name_match.group(1).strip()
                tech_match = re.findall(r"\b([a-zA-Z][a-zA-Z0-9+#.]{1,20})\b", block)
                if tech_match:
                    proj["technologies"] = list(set(tech_match))[:20]
                projects.append(proj)

        return projects[:20]

    def _extract_list_items(self, sections: dict, keywords: list) -> list:
        items = []
        for section_key in ["certification", "language"]:
            text = " ".join(sections.get(section_key, []))
            if text:
                lines = [l.strip("•●\t- -") for l in text.split("\n") if l.strip()]
                items.extend(lines)
        return items[:30]