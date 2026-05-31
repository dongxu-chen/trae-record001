package com.dlq.platform.analysis.rules;

import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;
import lombok.extern.slf4j.Slf4j;
import org.jeasy.rules.annotation.Action;
import org.jeasy.rules.annotation.Condition;
import org.jeasy.rules.annotation.Fact;
import org.jeasy.rules.annotation.Rule;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
@Rule(name = "NullPointerExceptionRule", description = "空指针异常规则", priority = 3)
public class NullPointerExceptionRule {

    private static final Pattern NPE_PATTERN = Pattern.compile(
            "NullPointerException.*?at\\s+([\\w.$]+)\\.([\\w$]+)\\(([^:]+):(\\d+)\\)");

    @Condition
    public boolean checkNPE(@Fact("message") DeadLetterMessage message) {
        String stackTrace = message.getStackTrace();
        String deadReason = message.getDeadReason();

        if (stackTrace != null && stackTrace.contains("NullPointerException")) {
            return true;
        }
        return deadReason != null && deadReason.contains("NullPointerException");
    }

    @Action
    public void applyRule(@Fact("message") DeadLetterMessage message,
                        @Fact("result") AnalysisResult result) {
        String stackTrace = message.getStackTrace();
        List<String> repairSteps = new ArrayList<>();

        String rootCause = "发生空指针异常";
        double confidence = 0.9;

        if (stackTrace != null) {
            Matcher matcher = NPE_PATTERN.matcher(stackTrace);
            if (matcher.find()) {
                String className = matcher.group(1);
                String methodName = matcher.group(2);
                String fileName = matcher.group(3);
                String lineNumber = matcher.group(4);

                rootCause = String.format("空指针异常发生在 %s.%s(%s:%s)",
                        className, methodName, fileName, lineNumber);

                result.getDetails().put("className", className);
                result.getDetails().put("methodName", methodName);
                result.getDetails().put("fileName", fileName);
                result.getDetails().put("lineNumber", lineNumber);
            }
        }

        result.setRootCause(rootCause);
        result.setSuggestedAction("检查代码中的空值判断，添加非空校验");

        repairSteps.add("检查相关代码，添加null检查");
        repairSteps.add("使用Optional或@NonNull注解避免空指针");
        repairSteps.add("修复后重新部署并测试");
        repairSteps.add("考虑添加单元测试覆盖空值场景");

        result.getDetails().put("ruleName", "NullPointerExceptionRule");
        result.getDetails().put("exceptionType", "NullPointerException");
        result.setConfidence(Math.max(result.getConfidence(), confidence));
        result.setRepairSteps(repairSteps);
    }
}
