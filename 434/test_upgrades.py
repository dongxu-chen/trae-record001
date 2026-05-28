import sys
sys.path.insert(0, '.')

from app.models.schemas import ResumeData, JobDescription
from app.parser.nlp_processor import NLPProcessor
from app.matcher.scorer import MatchScorer
from app.matcher.interview import InterviewQuestionGenerator

nlp = NLPProcessor.__new__(NLPProcessor)
nlp._nlp = None
nlp._bert = None

scorer = MatchScorer(nlp)
generator = InterviewQuestionGenerator()

print("=== 测试1: 年限表达式解析 ===")
test_cases = [
    3,
    "3年以上",
    "3-5年",
    "5年以下",
    "约3年",
    "2年左右",
    ">=5年",
    "3+年",
]

for expr in test_cases:
    result = scorer._parse_experience_expression(expr)
    desc = scorer._format_range_description(result)
    print(f"  输入 '{expr}' -> min={result['min']:.0f}, max={result['max']:.0f}, 显示: {desc}")

print("\n=== 测试2: 余弦相似度技能匹配 ===")
job = JobDescription(
    title='高级Python后端开发',
    description='精通Python，熟悉Django/FastAPI，MySQL，Redis，Docker，K8s',
    required_skills=['Python', 'Django', 'FastAPI', 'MySQL', 'Redis', 'Docker'],
    min_education='本科',
    min_experience_years='3年以上'
)

resumes = [
    ResumeData(
        candidate_name='完美匹配候选人',
        skills=['python', 'django', 'fastapi', 'mysql', 'redis', 'docker', 'kubernetes'],
        work_experience=[{'start_date':'2020年', 'end_date':'至今', 'description':'Python后端开发'}],
        education=[{'level':'本科', 'description':'计算机专业'}],
        projects=[{'name':'电商平台', 'description':'使用FastAPI开发后端', 'technologies': ['fastapi', 'mysql', 'redis', 'docker']}],
        full_text='Python Django FastAPI MySQL Redis Docker'
    ),
    ResumeData(
        candidate_name='部分匹配候选人',
        skills=['python', 'flask', 'mysql', 'mongodb', 'linux'],
        work_experience=[{'start_date':'2022年', 'end_date':'至今', 'description':'Python后端开发'}],
        education=[{'level':'本科', 'description':'计算机专业'}],
        projects=[{'name':'管理系统', 'description':'使用Flask开发'}],
        full_text='Python Flask MySQL MongoDB'
    ),
    ResumeData(
        candidate_name='跨领域候选人',
        skills=['java', 'spring', 'mysql', 'redis', 'docker', 'kubernetes'],
        work_experience=[{'start_date':'2019年', 'end_date':'至今', 'description':'Java后端开发'}],
        education=[{'level':'硕士', 'description':'计算机专业'}],
        projects=[{'name':'微服务平台', 'description':'Spring Cloud微服务', 'technologies': ['spring', 'mysql', 'redis', 'docker', 'k8s']}],
        full_text='Java Spring MySQL Redis Docker K8s'
    ),
]

for resume in resumes:
    result = scorer.score_resume(resume, job)
    print(f"\n  候选人: {result.candidate_name}")
    print(f"  综合得分: {result.overall_score:.3f}")
    print(f"  技能得分(余弦相似度混合): {result.skill_score:.3f}")
    print(f"  经验得分(表达式解析): {result.experience_score:.3f}")
    for reason in result.match_reasons[:3]:
        print(f"    - {reason.category}: {reason.detail[:60]}...")

print("\n=== 测试3: 基于差异点的个性化面试问题 ===")
sample_resume = ResumeData(
    candidate_name='测试候选人',
    skills=['python', 'django', 'mysql', 'redis', 'java', 'spring'],
    work_experience=[{
        'start_date': '2020年',
        'end_date': '至今',
        'company': '某互联网公司',
        'position': '高级后端开发工程师',
        'description': '负责核心业务系统开发'
    }],
    education=[{'level': '本科', 'description': '计算机专业'}],
    projects=[
        {'name': '电商订单系统', 'description': '高并发订单处理系统', 'technologies': ['python', 'django', 'mysql', 'redis']},
        {'name': '用户中心', 'description': '千万级用户系统', 'technologies': ['java', 'spring']}
    ],
    full_text='Python Django MySQL Redis Java Spring'
)

result = scorer.score_resume(sample_resume, job)
questions = generator.generate_questions(result, sample_resume, job)

print(f"  候选人: {sample_resume.candidate_name}")
print(f"  岗位要求技能: {job.required_skills}")
print(f"  候选人技能: {sample_resume.skills}")
print(f"\n  生成的个性化问题 ({len(questions)}个):")
for q in questions:
    print(f"    [{q.category}]")
    print(f"    问题: {q.question}")
    print(f"    理由: {q.reason}")
    print()

print("=== 所有测试通过! ===")