import random
from typing import List, Dict, Tuple

from app.models.schemas import MatchResult, InterviewQuestion, ResumeData, JobDescription


class InterviewQuestionGenerator:
    def __init__(self):
        self._init_question_templates()

    def _init_question_templates(self):
        self.skill_depth_templates = {
            "python": [
                "你在简历中提到了Python，能否介绍一下你在项目中是如何利用Python的特性来优化性能的？",
                "请分享一个你用Python解决复杂问题的经历，包括你的技术选型和实现思路。",
                "在Python项目中，你是如何进行代码结构设计和模块划分的？请举例说明。",
                "你遇到过的最棘手的Python问题是什么？你是如何定位和解决的？",
            ],
            "java": [
                "你在简历中提到了Java，能否描述一下你在JVM调优方面的经验？",
                "请分享一个你设计的Java系统架构，包括你是如何考虑扩展性和可维护性的。",
                "在Java并发编程方面，你有哪些实际经验？遇到过什么挑战？",
                "你是如何保证Java代码质量的？有哪些实践经验？",
            ],
            "javascript": [
                "你在简历中提到了JavaScript，能否分享你在前端性能优化方面的实践？",
                "请描述一个你参与的复杂前端项目，包括你是如何进行状态管理的。",
                "在JavaScript异步编程方面，你有哪些经验？Promise和async/await的使用场景有何不同？",
                "你是如何处理前端兼容性问题的？有哪些实际案例？",
            ],
            "go": [
                "你在简历中提到了Go，能否介绍一下你在Go并发编程方面的实践？",
                "请分享一个你用Go开发的高性能服务，包括你是如何进行性能调优的。",
                "在Go项目中，你是如何进行错误处理和日志记录的？",
                "你遇到过的Go语言陷阱有哪些？是如何避免的？",
            ],
            "rust": [
                "你在简历中提到了Rust，能否分享你对Rust所有权系统的理解和实践？",
                "请描述你用Rust解决的一个内存安全或性能问题。",
                "在Rust与其他语言交互方面，你有哪些经验？",
                "你是如何学习Rust的？有什么心得可以分享？",
            ],
            "react": [
                "你在简历中提到了React，能否分享你在大型React应用中的状态管理方案？",
                "请描述一个你优化React渲染性能的案例。",
                "在React组件设计方面，你有哪些原则和实践？",
                "你是如何进行React单元测试和集成测试的？",
            ],
            "vue": [
                "你在简历中提到了Vue，能否分享你在Vue3 Composition API方面的实践？",
                "请描述你在Vue项目中遇到的性能瓶颈和解决方案。",
                "在Vue组件库设计或使用方面，你有哪些经验？",
                "你是如何进行Vue项目的代码规范和工程化的？",
            ],
            "docker": [
                "你在简历中提到了Docker，能否分享你在容器化部署方面的最佳实践？",
                "请描述一个你设计的Docker镜像优化方案。",
                "在Docker网络和存储方面，你有哪些实践经验？",
                "你遇到过的Docker相关故障有哪些？是如何排查和解决的？",
            ],
            "kubernetes": [
                "你在简历中提到了Kubernetes，能否分享你在K8s集群运维方面的经验？",
                "请描述你设计的一个K8s应用部署方案，包括如何保证高可用。",
                "在K8s资源管理和调度优化方面，你有哪些实践？",
                "你是如何进行K8s故障排查的？有什么方法论？",
            ],
            "mysql": [
                "你在简历中提到了MySQL，能否分享你在SQL优化方面的经验？",
                "请描述一个你参与的MySQL数据库架构设计或优化项目。",
                "在MySQL事务和锁机制方面，你有哪些实际经验？",
                "你是如何进行MySQL备份和恢复的？有哪些策略？",
            ],
            "redis": [
                "你在简历中提到了Redis，能否分享你在Redis性能调优方面的实践？",
                "请描述你设计的一个Redis缓存方案，包括如何解决缓存穿透、击穿、雪崩问题。",
                "在Redis数据结构选型方面，你有哪些经验和原则？",
                "你遇到过的Redis故障有哪些？是如何处理的？",
            ],
            "mongodb": [
                "你在简历中提到了MongoDB，能否分享你在数据建模方面的经验？",
                "请描述一个你优化MongoDB查询性能的案例。",
                "在MongoDB集群部署和运维方面，你有哪些实践？",
                "MongoDB与关系型数据库的选型你是如何考虑的？",
            ],
            "tensorflow": [
                "你在简历中提到了TensorFlow，能否分享你在模型训练优化方面的经验？",
                "请描述你设计的一个深度学习模型部署方案。",
                "在TensorFlow与其他框架对比方面，你有哪些看法？",
                "你遇到过的模型训练问题有哪些？是如何解决的？",
            ],
            "pytorch": [
                "你在简历中提到了PyTorch，能否分享你在模型设计和训练方面的实践？",
                "请描述你解决的一个深度学习难题，包括你的思路和方法。",
                "在PyTorch模型优化和部署方面，你有哪些经验？",
                "你是如何进行深度学习实验管理的？",
            ],
        }

        self.gap_templates = [
            "我们注意到岗位要求{skill}，但你的简历中没有明确体现。你是否有相关的学习或使用经验？",
            "对于{skill}这项技术，你是否有了解或学习计划？",
            "在过往的项目中，你是否接触过与{skill}类似的技术？能否分享一下相关经验？",
            "如果工作中需要用到{skill}，你预计需要多长时间上手？你的学习路径会是怎样的？",
        ]

        self.highlight_templates = [
            "你的简历中提到了{highlight}，这是一个亮点。能否详细介绍一下相关的项目和你的贡献？",
            "我们注意到你有{highlight}的经验，这与我们的岗位很匹配。能否分享一下具体的技术实现细节？",
            "{highlight}是我们非常看重的能力。你在这方面有哪些深入的理解或独特的见解？",
            "请分享一个你运用{highlight}解决实际问题的案例。",
        ]

        self.general_templates = [
            "请做一个3分钟的自我介绍，重点突出与本岗位相关的经验和优势。",
            "为什么选择投递这个岗位？你对我们公司和团队有哪些了解？",
            "你理想的工作环境和团队氛围是怎样的？",
            "在未来1-3年，你在职业发展上有什么规划？",
        ]

        self.behavior_templates = [
            "请描述一次你在项目中遇到重大技术挑战的经历，以及你是如何克服的。",
            "当你的技术方案与团队成员产生分歧时，你会如何处理？请举例说明。",
            "请分享一次你主动承担额外责任或帮助团队解决问题的经历。",
            "在高压项目中，你是如何保证工作质量和进度的？",
        ]

    def generate_questions(
        self,
        match_result: MatchResult,
        resume: ResumeData,
        job: JobDescription,
        max_questions: int = 8,
    ) -> List[InterviewQuestion]:
        questions = []
        used_questions = set()

        diff = self._analyze_differences(resume, job, match_result)

        strength_questions = self._generate_strength_questions(diff, resume, job)
        for q in strength_questions:
            if q.question not in used_questions:
                questions.append(q)
                used_questions.add(q.question)

        gap_questions = self._generate_gap_questions(diff, resume, job)
        for q in gap_questions:
            if q.question not in used_questions:
                questions.append(q)
                used_questions.add(q.question)

        highlight_questions = self._generate_highlight_questions(resume, job)
        for q in highlight_questions:
            if q.question not in used_questions:
                questions.append(q)
                used_questions.add(q.question)

        exp_questions = self._generate_personalized_exp_questions(resume, job)
        for q in exp_questions:
            if q.question not in used_questions:
                questions.append(q)
                used_questions.add(q.question)

        behavior_count = min(1, max(0, max_questions - len(questions)))
        behavior_questions = random.sample(self.behavior_templates, behavior_count)
        for q_text in behavior_questions:
            if q_text not in used_questions:
                questions.append(InterviewQuestion(
                    question=q_text,
                    category="行为面试",
                    reason="考察候选人软技能和问题解决能力",
                ))
                used_questions.add(q_text)

        if len(questions) < max_questions:
            general_count = min(2, max_questions - len(questions))
            general_questions = random.sample(self.general_templates, general_count)
            for q_text in general_questions:
                if q_text not in used_questions:
                    questions.append(InterviewQuestion(
                        question=q_text,
                        category="综合考察",
                        reason="了解候选人求职动机和职业规划",
                    ))
                    used_questions.add(q_text)

        return questions[:max_questions]

    def _analyze_differences(
        self, resume: ResumeData, job: JobDescription, match_result: MatchResult
    ) -> Dict:
        resume_skills = set(s.lower() for s in resume.skills)
        required_skills = set(s.lower() for s in job.required_skills)

        matched_skills = set()
        for req in required_skills:
            for res in resume_skills:
                if req in res or res in req:
                    matched_skills.add(req)
                    break

        missing_skills = required_skills - matched_skills

        extra_skills = resume_skills - required_skills

        highlights = self._find_highlights(resume, job)

        return {
            "matched_skills": list(matched_skills),
            "missing_skills": list(missing_skills),
            "extra_skills": list(extra_skills),
            "highlights": highlights,
        }

    def _find_highlights(self, resume: ResumeData, job: JobDescription) -> List[str]:
        highlights = []
        job_desc_lower = job.description.lower()

        for skill in resume.skills:
            skill_lower = skill.lower()
            if skill_lower in job_desc_lower and len(skill_lower) > 3:
                highlights.append(skill)

        for proj in resume.projects:
            name = proj.get("name", "")
            desc = proj.get("description", "")
            if name and any(k in job_desc_lower for k in name.lower().split()):
                highlights.append(f"{name}项目经验")

        for exp in resume.work_experience:
            position = exp.get("position", "")
            if position and len(position) > 2:
                highlights.append(f"{position}岗位经验")

        return list(dict.fromkeys(highlights))[:3]

    def _generate_strength_questions(
        self, diff: Dict, resume: ResumeData, job: JobDescription
    ) -> List[InterviewQuestion]:
        questions = []
        matched = diff.get("matched_skills", [])

        top_skills = self._prioritize_skills(matched, job.required_skills)

        for skill in top_skills[:3]:
            skill_key = self._find_skill_key(skill)
            if skill_key and skill_key in self.skill_depth_templates:
                templates = self.skill_depth_templates[skill_key]
                q_text = random.choice(templates)
                questions.append(InterviewQuestion(
                    question=q_text,
                    category=f"优势深挖 - {skill_key}",
                    reason=f"候选人具备{skill_key}技能，且岗位有要求，深入考察技术深度",
                ))

        return questions

    def _generate_gap_questions(
        self, diff: Dict, resume: ResumeData, job: JobDescription
    ) -> List[InterviewQuestion]:
        questions = []
        missing = diff.get("missing_skills", [])

        for skill in missing[:2]:
            template = random.choice(self.gap_templates)
            q_text = template.format(skill=skill)
            questions.append(InterviewQuestion(
                question=q_text,
                category=f"差异弥补 - {skill}",
                reason=f"候选人简历中未明确体现{skill}，了解学习意愿和潜力",
            ))

        return questions

    def _generate_highlight_questions(
        self, resume: ResumeData, job: JobDescription
    ) -> List[InterviewQuestion]:
        questions = []

        for proj in resume.projects[:2]:
            name = proj.get("name", "")
            techs = proj.get("technologies", [])
            if name:
                tech_str = "、".join(techs[:3]) if techs else ""
                if tech_str:
                    q_text = f"你的简历中提到了{name}项目，使用了{tech_str}等技术。能否详细介绍一下这个项目的架构设计和你在其中的具体贡献？"
                else:
                    q_text = f"请详细介绍一下{name}这个项目，包括业务背景、技术方案和你个人的贡献。"
                questions.append(InterviewQuestion(
                    question=q_text,
                    category="项目深挖",
                    reason="基于候选人项目经验，考察实际技术能力和产出",
                ))

        for exp in resume.work_experience[:1]:
            company = exp.get("company", "上一家公司")
            position = exp.get("position", "该职位")
            q_text = f"在{company}担任{position}期间，你认为最有技术含量或最有成就感的工作是什么？请详细描述技术实现细节。"
            questions.append(InterviewQuestion(
                question=q_text,
                category="经验深挖",
                reason="基于候选人过往工作经历，深入了解实际能力",
            ))

        return questions

    def _generate_personalized_exp_questions(
        self, resume: ResumeData, job: JobDescription
    ) -> List[InterviewQuestion]:
        questions = []

        job_skills_lower = [s.lower() for s in job.required_skills]
        resume_skills_lower = [s.lower() for s in resume.skills]

        overlapping = []
        for js in job_skills_lower:
            for rs in resume_skills_lower:
                if js in rs or rs in js:
                    overlapping.append(js)
                    break

        if overlapping:
            techs_str = "、".join(overlapping[:3])
            q_text = f"我们注意到你有{techs_str}等相关技能。能否结合过往项目，介绍一下你是如何运用这些技术解决实际业务问题的？"
            questions.append(InterviewQuestion(
                question=q_text,
                category="技能应用",
                reason="考察候选人技能的实际应用能力",
            ))

        if len(resume.projects) >= 2:
            q_text = "在你参与的多个项目中，哪个项目的技术挑战最大？你是如何分析和解决这些挑战的？"
            questions.append(InterviewQuestion(
                question=q_text,
                category="问题解决",
                reason="考察候选人分析和解决复杂技术问题的能力",
            ))

        return questions

    def _prioritize_skills(self, skills: List[str], required: List[str]) -> List[str]:
        required_lower = [s.lower() for s in required]
        priority_map = {s: i for i, s in enumerate(required_lower)}

        def get_priority(skill):
            skill_lower = skill.lower()
            for req, idx in priority_map.items():
                if req in skill_lower or skill_lower in req:
                    return idx
            return len(required)

        return sorted(skills, key=get_priority)

    def _find_skill_key(self, skill: str) -> str:
        skill = skill.lower()
        for key in self.skill_depth_templates:
            if key in skill or skill in key:
                return key
        return ""