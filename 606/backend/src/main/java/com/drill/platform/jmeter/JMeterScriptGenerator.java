package com.drill.platform.jmeter;

import com.drill.platform.model.TrafficProfile;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

@Slf4j
@Component
public class JMeterScriptGenerator {

    @Value("${drill.jmeter.result-dir:./drill-results}")
    private String resultDir;

    public String generateTestPlan(TrafficProfile profile, String testId) {
        String script = buildJmxScript(profile, testId);
        String scriptPath = resultDir + File.separator + testId + File.separator + "test_plan.jmx";
        saveScript(scriptPath, script);
        log.info("Generated JMeter script at: {}", scriptPath);
        return scriptPath;
    }

    private String buildJmxScript(TrafficProfile profile, String testId) {
        int totalDuration = profile.getRampUpSeconds() + profile.getSustainSeconds() + profile.getRampDownSeconds();
        int rampUp = profile.getRampUpSeconds();
        String threadGroupType = getThreadGroupType(profile.getPattern());

        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
        sb.append("<jmeterTestPlan version=\"1.2\" properties=\"5.0\" jmeter=\"5.6\">\n");
        sb.append("  <hashTree>\n");
        sb.append("    <TestPlan guiclass=\"TestPlanGui\" testclass=\"TestPlan\" testname=\"Drill-")
          .append(testId).append("\">\n");
        sb.append("      <boolProp name=\"TestPlan.functional_mode\">false</boolProp>\n");
        sb.append("      <boolProp name=\"TestPlan.serialize_threadgroups\">true</boolProp>\n");
        sb.append("    </TestPlan>\n");
        sb.append("    <hashTree>\n");

        sb.append("      <").append(threadGroupType).append(" guiclass=\"ThreadGroupGui\" ")
          .append("testclass=\"ThreadGroup\" testname=\"Drill Traffic\">\n");
        sb.append("        <intProp name=\"ThreadGroup.num_threads\">")
          .append(profile.getConcurrentUsers()).append("</intProp>\n");
        sb.append("        <intProp name=\"ThreadGroup.ramp_time\">")
          .append(rampUp).append("</intProp>\n");
        sb.append("        <boolProp name=\"ThreadGroup.same_user_on_next_iteration\">true</boolProp>\n");
        sb.append("        <stringProp name=\"ThreadGroup.on_sample_error\">continue</stringProp>\n");
        sb.append("        <elementProp name=\"ThreadGroup.main_controller\" ")
          .append("elementType=\"LoopController\">\n");
        sb.append("          <stringProp name=\"LoopController.loops\">-1</stringProp>\n");
        sb.append("          <boolProp name=\"LoopController.continue_forever\">false</boolProp>\n");
        sb.append("        </elementProp>\n");
        sb.append("        <stringProp name=\"ThreadGroup.duration\">")
          .append(totalDuration).append("</stringProp>\n");
        sb.append("        <stringProp name=\"ThreadGroup.delay\">0</stringProp>\n");
        sb.append("        <boolProp name=\"ThreadGroup.scheduler\">true</boolProp>\n");
        sb.append("      </").append(threadGroupType).append(">\n");
        sb.append("      <hashTree>\n");

        sb.append("        <HTTPSamplerProxy guiclass=\"HttpTestSampleGui\" ")
          .append("testclass=\"HTTPSamplerProxy\" testname=\"Drill Request\">\n");
        sb.append("          <stringProp name=\"HTTPSampler.domain\">")
          .append(extractDomain(profile.getTargetUrl())).append("</stringProp>\n");
        sb.append("          <stringProp name=\"HTTPSampler.port\">")
          .append(extractPort(profile.getTargetUrl())).append("</stringProp>\n");
        sb.append("          <stringProp name=\"HTTPSampler.protocol\">")
          .append(extractProtocol(profile.getTargetUrl())).append("</stringProp>\n");
        sb.append("          <stringProp name=\"HTTPSampler.path\">")
          .append(extractPath(profile.getTargetUrl())).append("</stringProp>\n");
        sb.append("          <stringProp name=\"HTTPSampler.method\">")
          .append(profile.getHttpMethod()).append("</stringProp>\n");
        sb.append("          <boolProp name=\"HTTPSampler.use_keepalive\">true</boolProp>\n");
        sb.append("          <boolProp name=\"HTTPSampler.follow_redirects\">true</boolProp>\n");
        sb.append("          <stringProp name=\"HTTPSampler.connect_timeout\">")
          .append(profile.getConnectTimeoutMs()).append("</stringProp>\n");
        sb.append("          <stringProp name=\"HTTPSampler.response_timeout\">")
          .append(profile.getReadTimeoutMs()).append("</stringProp>\n");

        if (profile.getRequestBody() != null && !profile.getRequestBody().isEmpty()) {
            sb.append("          <boolProp name=\"HTTPSampler.postBodyRaw\">true</boolProp>\n");
            sb.append("          <elementProp name=\"HTTPsampler.Arguments\" ")
              .append("elementType=\"Arguments\">\n");
            sb.append("            <collectionProp name=\"Arguments.arguments\">\n");
            sb.append("              <elementProp name=\"\" elementType=\"HTTPArgument\">\n");
            sb.append("                <stringProp name=\"Argument.value\">")
              .append(escapeXml(profile.getRequestBody())).append("</stringProp>\n");
            sb.append("              </elementProp>\n");
            sb.append("            </collectionProp>\n");
            sb.append("          </elementProp>\n");
        }

        sb.append("        </HTTPSamplerProxy>\n");
        sb.append("        <hashTree>\n");

        sb.append("          <ConstantTimer guiclass=\"ConstantTimerGui\" ")
          .append("testclass=\"ConstantTimer\" testname=\"Timer\">\n");
        int delayMs = profile.getPeakQps() > 0 ? 1000 / profile.getPeakQps() : 100;
        sb.append("            <stringProp name=\"ConstantTimer.delay\">")
          .append(delayMs).append("</stringProp>\n");
        sb.append("          </ConstantTimer>\n");
        sb.append("          <hashTree/>\n");

        sb.append("        </hashTree>\n");
        sb.append("      </hashTree>\n");
        sb.append("    </hashTree>\n");
        sb.append("  </hashTree>\n");
        sb.append("</jmeterTestPlan>\n");

        return sb.toString();
    }

    private String getThreadGroupType(TrafficProfile.TrafficPattern pattern) {
        return "ThreadGroup";
    }

    private String extractDomain(String url) {
        try {
            String cleaned = url.replaceFirst("^https?://", "");
            return cleaned.split("/")[0].split(":")[0];
        } catch (Exception e) {
            return "localhost";
        }
    }

    private String extractPort(String url) {
        try {
            String cleaned = url.replaceFirst("^https?://", "");
            String[] parts = cleaned.split("/")[0].split(":");
            if (parts.length > 1) return parts[1];
            return url.startsWith("https") ? "443" : "80";
        } catch (Exception e) {
            return "8080";
        }
    }

    private String extractProtocol(String url) {
        return url.startsWith("https") ? "https" : "http";
    }

    private String extractPath(String url) {
        try {
            String cleaned = url.replaceFirst("^https?://", "");
            int pathStart = cleaned.indexOf("/");
            return pathStart >= 0 ? cleaned.substring(pathStart) : "/";
        } catch (Exception e) {
            return "/";
        }
    }

    private String escapeXml(String input) {
        if (input == null) return "";
        return input.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&apos;");
    }

    private void saveScript(String path, String content) {
        File file = new File(path);
        file.getParentFile().mkdirs();
        try (FileWriter writer = new FileWriter(file)) {
            writer.write(content);
        } catch (IOException e) {
            log.error("Failed to save JMeter script", e);
            throw new RuntimeException("Failed to save JMeter script", e);
        }
    }
}
