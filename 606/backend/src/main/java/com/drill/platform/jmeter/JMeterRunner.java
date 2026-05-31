package com.drill.platform.jmeter;

import com.drill.platform.model.DrillResult;
import com.drill.platform.model.TrafficProfile;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.File;
import java.io.IOException;

@Slf4j
@Component
public class JMeterRunner {

    @Value("${drill.jmeter.home:jmeter}")
    private String jmeterHome;

    @Value("${drill.jmeter.result-dir:./drill-results}")
    private String resultDir;

    private final JMeterScriptGenerator scriptGenerator;
    private final JMeterResultParser resultParser;

    public JMeterRunner(JMeterScriptGenerator scriptGenerator, JMeterResultParser resultParser) {
        this.scriptGenerator = scriptGenerator;
        this.resultParser = resultParser;
    }

    public DrillResult runTest(TrafficProfile profile, String testId) {
        String scriptPath = scriptGenerator.generateTestPlan(profile, testId);
        String outputDir = resultDir + File.separator + testId;
        new File(outputDir).mkdirs();

        String csvPath = outputDir + File.separator + "results.csv";
        String jtlPath = outputDir + File.separator + "results.jtl";
        String logPath = outputDir + File.separator + "jmeter.log";

        ProcessBuilder pb = new ProcessBuilder(
                jmeterHome + File.separator + "bin" + File.separator + "jmeter",
                "-n",
                "-t", scriptPath,
                "-l", jtlPath,
                "-e",
                "-o", outputDir + File.separator + "report",
                "-j", logPath,
                "-Jjmeter.save.saveservice.output_format=csv"
        );
        pb.redirectErrorStream(true);

        try {
            log.info("Starting JMeter test: {}", testId);
            Process process = pb.start();

            try (java.io.BufferedReader reader = new java.io.BufferedReader(
                    new java.io.InputStreamReader(process.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    log.debug("JMeter: {}", line);
                }
            }

            int exitCode = process.waitFor();
            log.info("JMeter test {} completed with exit code: {}", testId, exitCode);

            convertJtlToCsv(jtlPath, csvPath);

            return resultParser.parseCsvResult(testId);
        } catch (IOException | InterruptedException e) {
            log.error("JMeter test execution failed", e);
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            return null;
        }
    }

    private void convertJtlToCsv(String jtlPath, String csvPath) {
        File jtlFile = new File(jtlPath);
        File csvFile = new File(csvPath);
        if (jtlFile.exists() && !csvFile.exists()) {
            try {
                java.nio.file.Files.copy(jtlFile.toPath(), csvFile.toPath());
            } catch (IOException e) {
                log.warn("Failed to convert JTL to CSV", e);
            }
        }
    }

    public boolean isJMeterAvailable() {
        File jmeterBin = new File(jmeterHome + File.separator + "bin" + File.separator + "jmeter");
        return jmeterBin.exists();
    }
}
