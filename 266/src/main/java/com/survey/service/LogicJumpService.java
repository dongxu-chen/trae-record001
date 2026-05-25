package com.survey.service;

import com.survey.entity.Answer;
import com.survey.entity.Survey;
import com.survey.exception.BusinessException;
import com.survey.model.LogicJump;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class LogicJumpService {

    public String getNextQuestionId(Survey survey, String currentQuestionId, List<Answer> answers,
                                    Set<String> visitedQuestions) {
        if (visitedQuestions == null) {
            visitedQuestions = new HashSet<>();
        }

        if (visitedQuestions.contains(currentQuestionId)) {
            return null;
        }
        visitedQuestions.add(currentQuestionId);

        if (survey.getLogicJumps() == null || survey.getLogicJumps().isEmpty()) {
            return getNextQuestionByOrder(survey, currentQuestionId);
        }

        Map<String, Answer> answerMap = answers.stream()
                .collect(Collectors.toMap(Answer::getQuestionId, a -> a));

        for (LogicJump jump : survey.getLogicJumps()) {
            if (jump.getFromQuestionId().equals(currentQuestionId)) {
                Answer answer = answerMap.get(currentQuestionId);
                if (answer != null && evaluateCondition(jump, answer)) {
                    String nextQuestionId = jump.getToQuestionId();
                    if (visitedQuestions.contains(nextQuestionId)) {
                        return null;
                    }
                    return nextQuestionId;
                }
            }
        }

        return getNextQuestionByOrder(survey, currentQuestionId);
    }

    public void validateLogicJumps(Survey survey) {
        if (survey.getLogicJumps() == null || survey.getLogicJumps().isEmpty()) {
            return;
        }

        if (survey.getQuestions() == null || survey.getQuestions().isEmpty()) {
            return;
        }

        Set<String> questionIds = survey.getQuestions().stream()
                .map(com.survey.entity.Question::getId)
                .collect(Collectors.toSet());

        for (LogicJump jump : survey.getLogicJumps()) {
            if (!questionIds.contains(jump.getFromQuestionId())) {
                throw new BusinessException("逻辑跳转源问题不存在: " + jump.getFromQuestionId());
            }
            if (!questionIds.contains(jump.getToQuestionId())) {
                throw new BusinessException("逻辑跳转目标问题不存在: " + jump.getToQuestionId());
            }
            if (jump.getFromQuestionId().equals(jump.getToQuestionId())) {
                throw new BusinessException("逻辑跳转不能指向自身: " + jump.getFromQuestionId());
            }
        }

        for (String startQuestionId : questionIds) {
            checkLoop(survey, startQuestionId, new HashSet<>(), new HashSet<>());
        }
    }

    private void checkLoop(Survey survey, String currentQuestionId,
                           Set<String> visited, Set<String> recursionStack) {
        if (recursionStack.contains(currentQuestionId)) {
            throw new BusinessException("检测到逻辑跳转循环: " + currentQuestionId);
        }

        if (visited.contains(currentQuestionId)) {
            return;
        }

        visited.add(currentQuestionId);
        recursionStack.add(currentQuestionId);

        Set<String> nextQuestionIds = getNextQuestionIdsForLoopCheck(survey, currentQuestionId);
        for (String nextId : nextQuestionIds) {
            checkLoop(survey, nextId, visited, recursionStack);
        }

        recursionStack.remove(currentQuestionId);
    }

    private Set<String> getNextQuestionIdsForLoopCheck(Survey survey, String currentQuestionId) {
        Set<String> nextIds = new HashSet<>();

        if (survey.getLogicJumps() != null) {
            for (LogicJump jump : survey.getLogicJumps()) {
                if (jump.getFromQuestionId().equals(currentQuestionId)) {
                    nextIds.add(jump.getToQuestionId());
                }
            }
        }

        String nextByOrder = getNextQuestionByOrder(survey, currentQuestionId);
        if (nextByOrder != null) {
            nextIds.add(nextByOrder);
        }

        return nextIds;
    }

    private boolean evaluateCondition(LogicJump jump, Answer answer) {
        List<String> selectedValues = answer.getSelectedOptions();
        if (selectedValues == null || selectedValues.isEmpty()) {
            return false;
        }

        String conditionType = jump.getConditionType();
        List<String> conditionValues = jump.getConditionValues();

        if (conditionValues == null || conditionValues.isEmpty()) {
            return false;
        }

        return switch (conditionType != null ? conditionType : "EQUALS") {
            case "EQUALS" -> selectedValues.stream().anyMatch(conditionValues::contains);
            case "NOT_EQUALS" -> selectedValues.stream().noneMatch(conditionValues::contains);
            case "ALL_EQUALS" -> selectedValues.containsAll(conditionValues);
            default -> selectedValues.stream().anyMatch(conditionValues::contains);
        };
    }

    private String getNextQuestionByOrder(Survey survey, String currentQuestionId) {
        if (survey.getQuestions() == null) {
            return null;
        }

        int currentIndex = -1;
        for (int i = 0; i < survey.getQuestions().size(); i++) {
            if (survey.getQuestions().get(i).getId().equals(currentQuestionId)) {
                currentIndex = i;
                break;
            }
        }

        if (currentIndex == -1 || currentIndex >= survey.getQuestions().size() - 1) {
            return null;
        }

        return survey.getQuestions().get(currentIndex + 1).getId();
    }
}
