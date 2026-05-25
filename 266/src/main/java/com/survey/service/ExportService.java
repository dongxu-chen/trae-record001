package com.survey.service;

import com.survey.entity.Answer;
import com.survey.entity.Survey;
import com.survey.entity.VoteRecord;
import com.survey.enums.QuestionType;
import com.survey.exception.BusinessException;
import com.survey.repository.SurveyRepository;
import com.survey.repository.VoteRecordRepository;
import lombok.RequiredArgsConstructor;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.StringWriter;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Service
@RequiredArgsConstructor
public class ExportService {

    private final SurveyRepository surveyRepository;
    private final VoteRecordRepository voteRecordRepository;
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public byte[] exportToExcel(String surveyId) {
        Survey survey = surveyRepository.findById(surveyId)
                .orElseThrow(() -> new BusinessException("问卷不存在"));

        List<VoteRecord> records = voteRecordRepository.findBySurveyId(surveyId);

        try (Workbook workbook = new XSSFWorkbook()) {
            Sheet sheet = workbook.createSheet("调查结果");

            Row headerRow = sheet.createRow(0);
            headerRow.createCell(0).setCellValue("提交时间");
            headerRow.createCell(1).setCellValue("耗时(秒)");

            Map<String, Integer> questionIndexMap = new HashMap<>();
            int colIndex = 2;
            if (survey.getQuestions() != null) {
                for (com.survey.entity.Question question : survey.getQuestions()) {
                    headerRow.createCell(colIndex).setCellValue(question.getTitle());
                    questionIndexMap.put(question.getId(), colIndex);
                    colIndex++;
                }
            }

            int rowIndex = 1;
            for (VoteRecord record : records) {
                Row row = sheet.createRow(rowIndex++);
                row.createCell(0).setCellValue(record.getSubmittedAt() != null ?
                        record.getSubmittedAt().format(DATE_FORMATTER) : "");
                row.createCell(1).setCellValue(record.getTimeTaken() != null ? record.getTimeTaken() : 0);

                if (record.getAnswers() != null) {
                    for (Answer answer : record.getAnswers()) {
                        Integer idx = questionIndexMap.get(answer.getQuestionId());
                        if (idx != null) {
                            String value = formatAnswerValue(answer, survey);
                            row.createCell(idx).setCellValue(value);
                        }
                    }
                }
            }

            for (int i = 0; i < colIndex; i++) {
                sheet.autoSizeColumn(i);
            }

            ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
            workbook.write(outputStream);
            return outputStream.toByteArray();
        } catch (IOException e) {
            throw new BusinessException("导出Excel失败: " + e.getMessage());
        }
    }

    public String exportToCSV(String surveyId) {
        Survey survey = surveyRepository.findById(surveyId)
                .orElseThrow(() -> new BusinessException("问卷不存在"));

        List<VoteRecord> records = voteRecordRepository.findBySurveyId(surveyId);

        StringWriter writer = new StringWriter();

        writer.append("提交时间,耗时(秒)");
        Map<String, Integer> questionIndexMap = new HashMap<>();
        List<String> questionIds = new ArrayList<>();
        if (survey.getQuestions() != null) {
            for (com.survey.entity.Question question : survey.getQuestions()) {
                writer.append(",").append(escapeCSV(question.getTitle()));
                questionIds.add(question.getId());
            }
        }
        writer.append("\n");

        for (VoteRecord record : records) {
            writer.append(record.getSubmittedAt() != null ? record.getSubmittedAt().format(DATE_FORMATTER) : "")
                    .append(",")
                    .append(String.valueOf(record.getTimeTaken() != null ? record.getTimeTaken() : 0));

            Map<String, Answer> answerMap = new HashMap<>();
            if (record.getAnswers() != null) {
                for (Answer answer : record.getAnswers()) {
                    answerMap.put(answer.getQuestionId(), answer);
                }
            }

            for (String questionId : questionIds) {
                Answer answer = answerMap.get(questionId);
                String value = answer != null ? formatAnswerValue(answer, survey) : "";
                writer.append(",").append(escapeCSV(value));
            }
            writer.append("\n");
        }

        return writer.toString();
    }

    private String formatAnswerValue(Answer answer, Survey survey) {
        String questionType = answer.getQuestionType();

        if (QuestionType.SINGLE_CHOICE.name().equals(questionType) ||
                QuestionType.MULTIPLE_CHOICE.name().equals(questionType)) {
            List<String> selectedOptions = answer.getSelectedOptions();
            if (selectedOptions == null || selectedOptions.isEmpty()) {
                return "";
            }

            Map<String, String> optionTextMap = getOptionTextMap(survey, answer.getQuestionId());
            List<String> optionTexts = new ArrayList<>();
            for (String optionId : selectedOptions) {
                String text = optionTextMap.getOrDefault(optionId, optionId);
                optionTexts.add(text);
            }
            return String.join("; ", optionTexts);
        } else if (QuestionType.TEXT.name().equals(questionType)) {
            return answer.getTextValue() != null ? answer.getTextValue() : "";
        } else if (QuestionType.MATRIX.name().equals(questionType)) {
            Map<String, String> matrixValues = answer.getMatrixValues();
            if (matrixValues == null || matrixValues.isEmpty()) {
                return "";
            }

            Map<String, String> rowTextMap = getMatrixRowTextMap(survey, answer.getQuestionId());
            Map<String, String> colTextMap = getMatrixColumnTextMap(survey, answer.getQuestionId());

            List<String> matrixTexts = new ArrayList<>();
            for (Map.Entry<String, String> entry : matrixValues.entrySet()) {
                String rowText = rowTextMap.getOrDefault(entry.getKey(), entry.getKey());
                String colText = colTextMap.getOrDefault(entry.getValue(), entry.getValue());
                matrixTexts.add(rowText + ":" + colText);
            }
            return String.join("; ", matrixTexts);
        }

        return "";
    }

    private Map<String, String> getOptionTextMap(Survey survey, String questionId) {
        Map<String, String> map = new HashMap<>();
        if (survey.getQuestions() != null) {
            for (com.survey.entity.Question q : survey.getQuestions()) {
                if (q.getId().equals(questionId) && q.getOptions() != null) {
                    for (com.survey.model.Option opt : q.getOptions()) {
                        map.put(opt.getId(), opt.getText());
                    }
                }
            }
        }
        return map;
    }

    private Map<String, String> getMatrixRowTextMap(Survey survey, String questionId) {
        Map<String, String> map = new HashMap<>();
        if (survey.getQuestions() != null) {
            for (com.survey.entity.Question q : survey.getQuestions()) {
                if (q.getId().equals(questionId) && q.getMatrixRows() != null) {
                    for (com.survey.model.MatrixRow row : q.getMatrixRows()) {
                        map.put(row.getId(), row.getText());
                    }
                }
            }
        }
        return map;
    }

    private Map<String, String> getMatrixColumnTextMap(Survey survey, String questionId) {
        Map<String, String> map = new HashMap<>();
        if (survey.getQuestions() != null) {
            for (com.survey.entity.Question q : survey.getQuestions()) {
                if (q.getId().equals(questionId) && q.getMatrixColumns() != null) {
                    for (com.survey.model.MatrixColumn col : q.getMatrixColumns()) {
                        map.put(col.getId(), col.getText());
                    }
                }
            }
        }
        return map;
    }

    private String escapeCSV(String value) {
        if (value == null) {
            return "";
        }
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
}
