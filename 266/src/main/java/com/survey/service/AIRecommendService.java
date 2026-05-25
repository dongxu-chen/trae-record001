package com.survey.service;

import com.survey.dto.RecommendRequest;
import com.survey.dto.RecommendResponse;
import com.survey.entity.Question;
import com.survey.entity.SurveyTemplate;
import com.survey.enums.QuestionType;
import com.survey.model.MatrixColumn;
import com.survey.model.MatrixRow;
import com.survey.model.Option;
import com.survey.repository.SurveyTemplateRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AIRecommendService {

    private final SurveyTemplateRepository templateRepository;

    public RecommendResponse recommend(RecommendRequest request) {
        String topic = request.getTopic().toLowerCase();
        String industry = request.getIndustry() != null ? request.getIndustry().toLowerCase() : "";
        int questionCount = request.getQuestionCount() != null ? request.getQuestionCount() : 8;

        List<String> keywords = extractKeywords(topic + " " + industry);
        List<SurveyTemplate> matchedTemplates = findMatchingTemplates(keywords);

        RecommendResponse response = new RecommendResponse();
        response.setTitle(generateSurveyTitle(topic, industry));
        response.setDescription(generateSurveyDescription(topic));

        List<Question> recommendedQuestions = generateQuestions(topic, keywords, questionCount);
        response.setQuestions(recommendedQuestions);

        List<String> suggestions = generateSuggestions(topic, matchedTemplates);
        response.setSuggestions(suggestions);

        double score = calculateMatchScore(keywords, matchedTemplates);
        response.setMatchScore(score);

        return response;
    }

    private List<String> extractKeywords(String text) {
        List<String> keywords = new ArrayList<>();
        String[] words = text.split("[\\s,，。.！!？?;:：；]+");

        List<String> highValueWords = Arrays.asList(
                "满意度", "调研", "调查", "反馈", "评价", "问卷", "体验",
                "员工", "客户", "用户", "学生", "患者", "消费者",
                "产品", "服务", "培训", "活动", "会议", "课程",
                "市场", "品牌", "健康", "教育", "工作", "生活"
        );

        for (String word : words) {
            if (word.length() >= 2) {
                keywords.add(word);
                for (String hvWord : highValueWords) {
                    if (word.contains(hvWord) || hvWord.contains(word)) {
                        keywords.add(hvWord);
                    }
                }
            }
        }

        return keywords.stream().distinct().collect(Collectors.toList());
    }

    private List<SurveyTemplate> findMatchingTemplates(List<String> keywords) {
        List<SurveyTemplate> allTemplates = templateRepository.findAll();
        Map<SurveyTemplate, Integer> matchScores = new HashMap<>();

        for (SurveyTemplate template : allTemplates) {
            int score = 0;
            String templateText = (template.getName() + " " + template.getDescription() + " " +
                    (template.getTags() != null ? String.join(" ", template.getTags()) : "")).toLowerCase();

            for (String keyword : keywords) {
                if (templateText.contains(keyword)) {
                    score += 2;
                }
            }

            if (score > 0) {
                matchScores.put(template, score);
            }
        }

        return matchScores.entrySet().stream()
                .sorted((a, b) -> b.getValue() - a.getValue())
                .limit(5)
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }

    private String generateSurveyTitle(String topic, String industry) {
        List<String> prefixes = Arrays.asList(
                "关于", "", "", "2024年", "最新"
        );
        List<String> suffixes = Arrays.asList(
                "调查问卷", "满意度调查", "调研报告", "反馈问卷", "意见征集"
        );

        Random random = new Random();
        String prefix = prefixes.get(random.nextInt(prefixes.size()));
        String suffix = suffixes.get(random.nextInt(suffixes.size()));

        return prefix + topic + suffix;
    }

    private String generateSurveyDescription(String topic) {
        return "您好！为了更好地了解" + topic + "相关情况，我们诚邀您参与本次问卷调查。" +
                "您的意见对我们非常重要，问卷大约需要3-5分钟完成，感谢您的支持与配合！";
    }

    private List<Question> generateQuestions(String topic, List<String> keywords, int count) {
        List<Question> questions = new ArrayList<>();
        int questionIndex = 0;

        Question singleChoice = createSingleChoiceQuestion(topic, keywords, questionIndex++);
        questions.add(singleChoice);

        Question satisfaction = createSatisfactionQuestion(questionIndex++);
        questions.add(satisfaction);

        if (count > 2) {
            Question multipleChoice = createMultipleChoiceQuestion(topic, keywords, questionIndex++);
            questions.add(multipleChoice);
        }

        if (count > 3) {
            Question rating = createRatingQuestion(topic, questionIndex++);
            questions.add(rating);
        }

        if (count > 4) {
            Question matrix = createMatrixQuestion(topic, questionIndex++);
            questions.add(matrix);
        }

        if (count > 5) {
            Question textOpinion = createTextQuestion(topic, questionIndex++);
            questions.add(textOpinion);
        }

        if (count > 6) {
            Question yesNo = createYesNoQuestion(topic, questionIndex++);
            questions.add(yesNo);
        }

        if (count > 7) {
            Question frequency = createFrequencyQuestion(topic, questionIndex++);
            questions.add(frequency);
        }

        return questions;
    }

    private Question createSingleChoiceQuestion(String topic, List<String> keywords, int sortOrder) {
        Question question = new Question();
        question.setId(UUID.randomUUID().toString());
        question.setTitle("您是通过什么渠道了解到" + topic + "的？");
        question.setType(QuestionType.SINGLE_CHOICE);
        question.setRequired(true);
        question.setSortOrder(sortOrder);

        List<Option> options = Arrays.asList(
                createOption("网络搜索", 0),
                createOption("社交媒体", 1),
                createOption("朋友推荐", 2),
                createOption("线下活动", 3),
                createOption("其他", 4)
        );
        question.setOptions(options);

        return question;
    }

    private Question createSatisfactionQuestion(int sortOrder) {
        Question question = new Question();
        question.setId(UUID.randomUUID().toString());
        question.setTitle("您的整体满意度如何？");
        question.setType(QuestionType.SINGLE_CHOICE);
        question.setRequired(true);
        question.setSortOrder(sortOrder);

        List<Option> options = Arrays.asList(
                createOption("非常满意", 0),
                createOption("比较满意", 1),
                createOption("一般", 2),
                createOption("不太满意", 3),
                createOption("非常不满意", 4)
        );
        question.setOptions(options);

        return question;
    }

    private Question createMultipleChoiceQuestion(String topic, List<String> keywords, int sortOrder) {
        Question question = new Question();
        question.setId(UUID.randomUUID().toString());
        question.setTitle("您认为" + topic + "最重要的因素是什么？（可多选）");
        question.setType(QuestionType.MULTIPLE_CHOICE);
        question.setRequired(true);
        question.setSortOrder(sortOrder);
        question.setMaxSelect(3);

        List<Option> options = Arrays.asList(
                createOption("服务质量", 0),
                createOption("价格合理", 1),
                createOption("专业水平", 2),
                createOption("响应速度", 3),
                createOption("产品功能", 4),
                createOption("用户体验", 5)
        );
        question.setOptions(options);

        return question;
    }

    private Question createRatingQuestion(String topic, int sortOrder) {
        Question question = new Question();
        question.setId(UUID.randomUUID().toString());
        question.setTitle("请为以下方面打分（1-5分）");
        question.setType(QuestionType.MATRIX);
        question.setRequired(true);
        question.setSortOrder(sortOrder);

        List<MatrixRow> rows = Arrays.asList(
                createMatrixRow("整体满意度", 0),
                createMatrixRow("服务态度", 1),
                createMatrixRow("专业能力", 2),
                createMatrixRow("响应效率", 3)
        );
        question.setMatrixRows(rows);

        List<MatrixColumn> cols = Arrays.asList(
                createMatrixCol("1分", 0),
                createMatrixCol("2分", 1),
                createMatrixCol("3分", 2),
                createMatrixCol("4分", 3),
                createMatrixCol("5分", 4)
        );
        question.setMatrixColumns(cols);

        return question;
    }

    private Question createMatrixQuestion(String topic, int sortOrder) {
        Question question = new Question();
        question.setId(UUID.randomUUID().toString());
        question.setTitle("请对以下各项进行评价");
        question.setType(QuestionType.MATRIX);
        question.setRequired(true);
        question.setSortOrder(sortOrder);

        List<MatrixRow> rows = Arrays.asList(
                createMatrixRow("产品质量", 0),
                createMatrixRow("客户服务", 1),
                createMatrixRow("交付效率", 2),
                createMatrixRow("性价比", 3),
                createMatrixRow("售后支持", 4)
        );
        question.setMatrixRows(rows);

        List<MatrixColumn> cols = Arrays.asList(
                createMatrixCol("非常好", 0),
                createMatrixCol("好", 1),
                createMatrixCol("一般", 2),
                createMatrixCol("差", 3),
                createMatrixCol("非常差", 4)
        );
        question.setMatrixColumns(cols);

        return question;
    }

    private Question createTextQuestion(String topic, int sortOrder) {
        Question question = new Question();
        question.setId(UUID.randomUUID().toString());
        question.setTitle("您对" + topic + "有什么其他建议或意见？");
        question.setType(QuestionType.TEXT);
        question.setRequired(false);
        question.setSortOrder(sortOrder);

        return question;
    }

    private Question createYesNoQuestion(String topic, int sortOrder) {
        Question question = new Question();
        question.setId(UUID.randomUUID().toString());
        question.setTitle("您是否愿意向朋友推荐" + topic + "？");
        question.setType(QuestionType.SINGLE_CHOICE);
        question.setRequired(true);
        question.setSortOrder(sortOrder);

        List<Option> options = Arrays.asList(
                createOption("非常愿意", 0),
                createOption("愿意", 1),
                createOption("不确定", 2),
                createOption("不愿意", 3),
                createOption("非常不愿意", 4)
        );
        question.setOptions(options);

        return question;
    }

    private Question createFrequencyQuestion(String topic, int sortOrder) {
        Question question = new Question();
        question.setId(UUID.randomUUID().toString());
        question.setTitle("您接触" + topic + "的频率是？");
        question.setType(QuestionType.SINGLE_CHOICE);
        question.setRequired(true);
        question.setSortOrder(sortOrder);

        List<Option> options = Arrays.asList(
                createOption("每天", 0),
                createOption("每周", 1),
                createOption("每月", 2),
                createOption("偶尔", 3),
                createOption("第一次", 4)
        );
        question.setOptions(options);

        return question;
    }

    private Option createOption(String text, int order) {
        Option option = new Option();
        option.setId(UUID.randomUUID().toString());
        option.setText(text);
        option.setSortOrder(order);
        return option;
    }

    private MatrixRow createMatrixRow(String text, int order) {
        MatrixRow row = new MatrixRow();
        row.setId(UUID.randomUUID().toString());
        row.setText(text);
        row.setSortOrder(order);
        return row;
    }

    private MatrixColumn createMatrixCol(String text, int order) {
        MatrixColumn col = new MatrixColumn();
        col.setId(UUID.randomUUID().toString());
        col.setText(text);
        col.setSortOrder(order);
        return col;
    }

    private List<String> generateSuggestions(String topic, List<SurveyTemplate> templates) {
        List<String> suggestions = new ArrayList<>();

        suggestions.add("建议根据实际情况调整问题选项，使其更贴合您的" + topic + "调查目标");
        suggestions.add("可以考虑添加问题逻辑跳转，提升答题体验");
        suggestions.add("建议设置答题时间限制，防止随意作答");
        suggestions.add("可以开启匿名投票，提高数据真实性");

        if (!templates.isEmpty()) {
            suggestions.add("发现 " + templates.size() + " 个相关模板，您可以参考使用");
        }

        return suggestions;
    }

    private double calculateMatchScore(List<String> keywords, List<SurveyTemplate> templates) {
        if (keywords.isEmpty()) {
            return 0.5;
        }

        double baseScore = 0.7;
        double keywordBonus = Math.min(keywords.size() * 0.03, 0.2);
        double templateBonus = templates.isEmpty() ? 0 : 0.1;

        return Math.min(baseScore + keywordBonus + templateBonus, 1.0);
    }

    public List<SurveyTemplate> getAllTemplates() {
        return templateRepository.findAll();
    }

    public List<SurveyTemplate> getTemplatesByCategory(String category) {
        return templateRepository.findByCategory(category);
    }

    public SurveyTemplate createTemplate(SurveyTemplate template) {
        if (template.getUsageCount() == null) {
            template.setUsageCount(0);
        }
        if (template.getRating() == null) {
            template.setRating(0.0);
        }
        return templateRepository.save(template);
    }

    public void incrementTemplateUsage(String templateId) {
        templateRepository.findById(templateId).ifPresent(template -> {
            template.setUsageCount(template.getUsageCount() + 1);
            templateRepository.save(template);
        });
    }
}
