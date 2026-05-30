package com.api.validator.service;

import com.api.validator.model.ComparisonResult;
import com.api.validator.model.ValidationResult;
import org.springframework.stereotype.Service;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.StringWriter;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class ReportGenerationService {

    public String generateJUnitXmlReport(ValidationResult validationResult) {
        try {
            DocumentBuilderFactory docFactory = DocumentBuilderFactory.newInstance();
            DocumentBuilder docBuilder = docFactory.newDocumentBuilder();
            
            org.w3c.dom.Document doc = docBuilder.newDocument();
            
            org.w3c.dom.Element testsuites = doc.createElement("testsuites");
            doc.appendChild(testsuites);
            
            int totalTests = Math.max(1, validationResult.getErrors().size());
            int failures = validationResult.getErrors().size();
            
            org.w3c.dom.Element testsuite = doc.createElement("testsuite");
            testsuite.setAttribute("name", "API Response Validation");
            testsuite.setAttribute("tests", String.valueOf(totalTests));
            testsuite.setAttribute("failures", String.valueOf(failures));
            testsuite.setAttribute("errors", "0");
            testsuite.setAttribute("skipped", "0");
            testsuite.setAttribute("timestamp", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            testsuite.setAttribute("hostname", "api-validator");
            
            if (validationResult.getPath() != null) {
                testsuite.setAttribute("path", validationResult.getPath());
                testsuite.setAttribute("method", validationResult.getMethod() != null ? validationResult.getMethod() : "GET");
            }
            
            testsuites.appendChild(testsuite);
            
            if (validationResult.getErrors() == null || validationResult.getErrors().isEmpty()) {
                org.w3c.dom.Element testcase = doc.createElement("testcase");
                testcase.setAttribute("classname", "Validation");
                testcase.setAttribute("name", String.format("%s %s - Schema validation", 
                    validationResult.getMethod() != null ? validationResult.getMethod() : "GET",
                    validationResult.getPath() != null ? validationResult.getPath() : "unknown"));
                testsuite.appendChild(testcase);
            } else {
                int testIndex = 0;
                for (ValidationResult.ValidationError error : validationResult.getErrors()) {
                    org.w3c.dom.Element testcase = doc.createElement("testcase");
                    testcase.setAttribute("classname", "Validation");
                    testcase.setAttribute("name", String.format("[%s] %s - %s", 
                        error.getSeverity() != null ? error.getSeverity() : "MEDIUM",
                        error.getField(),
                        error.getType()));
                    testcase.setAttribute("time", "0.00" + (testIndex++));
                    
                    org.w3c.dom.Element failure = doc.createElement("failure");
                    failure.setAttribute("message", escapeXml(error.getMessage()));
                    failure.setAttribute("type", error.getType().name());
                    if (error.getSeverity() != null) {
                        failure.setAttribute("severity", error.getSeverity().name());
                    }
                    failure.setTextContent(String.format("Field: %s%nError: %s%nType: %s%nSeverity: %s",
                        error.getField(),
                        error.getMessage(),
                        error.getType(),
                        error.getSeverity() != null ? error.getSeverity() : "MEDIUM"));
                    
                    testcase.appendChild(failure);
                    testsuite.appendChild(testcase);
                }
            }
            
            TransformerFactory transformerFactory = TransformerFactory.newInstance();
            Transformer transformer = transformerFactory.newTransformer();
            transformer.setOutputProperty("indent", "yes");
            transformer.setOutputProperty("{http://xml.apache.org/xslt}indent-amount", "2");
            
            StringWriter writer = new StringWriter();
            transformer.transform(new DOMSource(doc), new StreamResult(writer));
            
            return writer.toString();
            
        } catch (Exception e) {
            return generateFallbackJUnitXml(validationResult, e);
        }
    }

    public String generateJUnitXmlReport(ComparisonResult comparisonResult) {
        try {
            DocumentBuilderFactory docFactory = DocumentBuilderFactory.newInstance();
            DocumentBuilder docBuilder = docFactory.newDocumentBuilder();
            
            org.w3c.dom.Document doc = docBuilder.newDocument();
            
            org.w3c.dom.Element testsuites = doc.createElement("testsuites");
            doc.appendChild(testsuites);
            
            int validationFailures = 0;
            int validationTests = 0;
            if (comparisonResult.getEnv1Validation() != null) {
                validationTests += Math.max(1, comparisonResult.getEnv1Validation().getErrors().size());
                validationFailures += comparisonResult.getEnv1Validation().getErrors().size();
            }
            if (comparisonResult.getEnv2Validation() != null) {
                validationTests += Math.max(1, comparisonResult.getEnv2Validation().getErrors().size());
                validationFailures += comparisonResult.getEnv2Validation().getErrors().size();
            }
            
            int comparisonTests = Math.max(1, comparisonResult.getDifferences().size());
            int comparisonFailures = comparisonResult.getDifferences().size();
            
            int totalTests = validationTests + comparisonTests;
            int totalFailures = validationFailures + comparisonFailures;
            
            org.w3c.dom.Element testsuite = doc.createElement("testsuite");
            testsuite.setAttribute("name", String.format("API Comparison: %s vs %s", 
                comparisonResult.getEnv1Name(), comparisonResult.getEnv2Name()));
            testsuite.setAttribute("tests", String.valueOf(totalTests));
            testsuite.setAttribute("failures", String.valueOf(totalFailures));
            testsuite.setAttribute("errors", "0");
            testsuite.setAttribute("skipped", "0");
            testsuite.setAttribute("timestamp", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            testsuite.setAttribute("hostname", "api-validator");
            testsuite.setAttribute("env1", comparisonResult.getEnv1Name());
            testsuite.setAttribute("env2", comparisonResult.getEnv2Name());
            if (comparisonResult.getPath() != null) {
                testsuite.setAttribute("path", comparisonResult.getPath());
                testsuite.setAttribute("method", comparisonResult.getMethod() != null ? comparisonResult.getMethod() : "GET");
            }
            
            testsuites.appendChild(testsuite);
            
            int testIndex = 0;
            
            if (comparisonResult.getEnv1Validation() != null) {
                testIndex = addValidationTestCases(doc, testsuite, comparisonResult.getEnv1Validation(), 
                    comparisonResult.getEnv1Name(), testIndex);
            }
            
            if (comparisonResult.getEnv2Validation() != null) {
                testIndex = addValidationTestCases(doc, testsuite, comparisonResult.getEnv2Validation(), 
                    comparisonResult.getEnv2Name(), testIndex);
            }
            
            if (comparisonResult.getDifferences() == null || comparisonResult.getDifferences().isEmpty()) {
                org.w3c.dom.Element testcase = doc.createElement("testcase");
                testcase.setAttribute("classname", "Comparison");
                testcase.setAttribute("name", String.format("%s vs %s - No differences found",
                    comparisonResult.getEnv1Name(), comparisonResult.getEnv2Name()));
                testsuite.appendChild(testcase);
            } else {
                for (ComparisonResult.Difference diff : comparisonResult.getDifferences()) {
                    org.w3c.dom.Element testcase = doc.createElement("testcase");
                    testcase.setAttribute("classname", "Comparison");
                    testcase.setAttribute("name", String.format("[%s] %s - %s",
                        diff.getSeverity() != null ? diff.getSeverity() : "LOW",
                        diff.getField(),
                        diff.getType()));
                    testcase.setAttribute("time", "0.00" + (testIndex++));
                    
                    org.w3c.dom.Element failure = doc.createElement("failure");
                    failure.setAttribute("message", escapeXml(diff.getDescription()));
                    failure.setAttribute("type", diff.getType().name());
                    if (diff.getSeverity() != null) {
                        failure.setAttribute("severity", diff.getSeverity().name());
                    }
                    
                    StringBuilder detail = new StringBuilder();
                    detail.append(String.format("Field: %s%n", diff.getField()));
                    detail.append(String.format("Type: %s%n", diff.getType()));
                    detail.append(String.format("Severity: %s%n", diff.getSeverity() != null ? diff.getSeverity() : "LOW"));
                    detail.append(String.format("Description: %s%n", diff.getDescription()));
                    if (diff.getEnv1Value() != null) {
                        detail.append(String.format("%s value: %s%n", comparisonResult.getEnv1Name(), diff.getEnv1Value()));
                    }
                    if (diff.getEnv2Value() != null) {
                        detail.append(String.format("%s value: %s%n", comparisonResult.getEnv2Name(), diff.getEnv2Value()));
                    }
                    
                    failure.setTextContent(detail.toString());
                    testcase.appendChild(failure);
                    testsuite.appendChild(testcase);
                }
            }
            
            TransformerFactory transformerFactory = TransformerFactory.newInstance();
            Transformer transformer = transformerFactory.newTransformer();
            transformer.setOutputProperty("indent", "yes");
            transformer.setOutputProperty("{http://xml.apache.org/xslt}indent-amount", "2");
            
            StringWriter writer = new StringWriter();
            transformer.transform(new DOMSource(doc), new StreamResult(writer));
            
            return writer.toString();
            
        } catch (Exception e) {
            return generateFallbackJUnitXml(comparisonResult, e);
        }
    }

    private int addValidationTestCases(org.w3c.dom.Document doc, org.w3c.dom.Element testsuite,
                                        ValidationResult validationResult, String envName, int startIndex) {
        int testIndex = startIndex;
        
        if (validationResult.getErrors() == null || validationResult.getErrors().isEmpty()) {
            org.w3c.dom.Element testcase = doc.createElement("testcase");
            testcase.setAttribute("classname", "Validation." + envName);
            testcase.setAttribute("name", String.format("[%s] Schema validation - PASSED", envName));
            testcase.setAttribute("time", "0.00" + (testIndex++));
            testsuite.appendChild(testcase);
        } else {
            for (ValidationResult.ValidationError error : validationResult.getErrors()) {
                org.w3c.dom.Element testcase = doc.createElement("testcase");
                testcase.setAttribute("classname", "Validation." + envName);
                testcase.setAttribute("name", String.format("[%s][%s] %s - %s",
                    envName,
                    error.getSeverity() != null ? error.getSeverity() : "MEDIUM",
                    error.getField(),
                    error.getType()));
                testcase.setAttribute("time", "0.00" + (testIndex++));
                
                org.w3c.dom.Element failure = doc.createElement("failure");
                failure.setAttribute("message", escapeXml(error.getMessage()));
                failure.setAttribute("type", error.getType().name());
                if (error.getSeverity() != null) {
                    failure.setAttribute("severity", error.getSeverity().name());
                }
                failure.setAttribute("environment", envName);
                failure.setTextContent(String.format("Environment: %s%nField: %s%nError: %s%nType: %s%nSeverity: %s",
                    envName,
                    error.getField(),
                    error.getMessage(),
                    error.getType(),
                    error.getSeverity() != null ? error.getSeverity() : "MEDIUM"));
                
                testcase.appendChild(failure);
                testsuite.appendChild(testcase);
            }
        }
        
        return testIndex;
    }

    public Map<String, Object> generateEnhancedJsonReport(ComparisonResult comparisonResult) {
        Map<String, Object> report = new LinkedHashMap<>();
        
        report.put("reportVersion", "2.0");
        report.put("generatedAt", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        report.put("env1Name", comparisonResult.getEnv1Name());
        report.put("env2Name", comparisonResult.getEnv2Name());
        report.put("path", comparisonResult.getPath());
        report.put("method", comparisonResult.getMethod());
        report.put("hasDifferences", comparisonResult.isHasDifferences());
        report.put("totalDifferences", comparisonResult.getDifferences().size());
        
        Map<String, Integer> severityCount = new LinkedHashMap<>();
        severityCount.put("CRITICAL", 0);
        severityCount.put("HIGH", 0);
        severityCount.put("MEDIUM", 0);
        severityCount.put("LOW", 0);
        
        Map<String, Integer> typeCount = new LinkedHashMap<>();
        
        for (ComparisonResult.Difference diff : comparisonResult.getDifferences()) {
            String severity = diff.getSeverity() != null ? diff.getSeverity().name() : "LOW";
            severityCount.put(severity, severityCount.getOrDefault(severity, 0) + 1);
            
            String type = diff.getType().name();
            typeCount.put(type, typeCount.getOrDefault(type, 0) + 1);
        }
        
        report.put("severityBreakdown", severityCount);
        report.put("typeBreakdown", typeCount);
        
        report.put("criticalIssues", severityCount.getOrDefault("CRITICAL", 0));
        report.put("highIssues", severityCount.getOrDefault("HIGH", 0));
        report.put("mediumIssues", severityCount.getOrDefault("MEDIUM", 0));
        report.put("lowIssues", severityCount.getOrDefault("LOW", 0));
        
        if (comparisonResult.getEnv1Validation() != null) {
            Map<String, Object> env1Report = new LinkedHashMap<>();
            env1Report.put("valid", comparisonResult.getEnv1Validation().isValid());
            env1Report.put("errorCount", comparisonResult.getEnv1Validation().getErrors().size());
            env1Report.put("errors", comparisonResult.getEnv1Validation().getErrors());
            report.put("env1Validation", env1Report);
        }
        
        if (comparisonResult.getEnv2Validation() != null) {
            Map<String, Object> env2Report = new LinkedHashMap<>();
            env2Report.put("valid", comparisonResult.getEnv2Validation().isValid());
            env2Report.put("errorCount", comparisonResult.getEnv2Validation().getErrors().size());
            env2Report.put("errors", comparisonResult.getEnv2Validation().getErrors());
            report.put("env2Validation", env2Report);
        }
        
        report.put("differences", comparisonResult.getDifferences());
        
        boolean passed = comparisonResult.getDifferences().isEmpty() 
            && severityCount.getOrDefault("CRITICAL", 0) == 0
            && severityCount.getOrDefault("HIGH", 0) == 0;
        
        if (comparisonResult.getEnv1Validation() != null && !comparisonResult.getEnv1Validation().isValid()) {
            passed = false;
        }
        if (comparisonResult.getEnv2Validation() != null && !comparisonResult.getEnv2Validation().isValid()) {
            passed = false;
        }
        
        report.put("passed", passed);
        
        return report;
    }

    private String escapeXml(String input) {
        if (input == null) return "";
        return input.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace("\"", "&quot;")
                   .replace("'", "&apos;");
    }

    private String generateFallbackJUnitXml(ValidationResult result, Exception e) {
        return String.format(
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>%n" +
            "<testsuites>%n" +
            "  <testsuite name=\"API Validation\" tests=\"1\" failures=\"1\" errors=\"1\" timestamp=\"%s\">%n" +
            "    <testcase classname=\"Validation\" name=\"Report Generation\">%n" +
            "      <error message=\"%s\"/>%n" +
            "    </testcase>%n" +
            "  </testsuite>%n" +
            "</testsuites>",
            LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
            escapeXml(e.getMessage())
        );
    }

    private String generateFallbackJUnitXml(ComparisonResult result, Exception e) {
        return String.format(
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>%n" +
            "<testsuites>%n" +
            "  <testsuite name=\"API Comparison\" tests=\"1\" failures=\"1\" errors=\"1\" timestamp=\"%s\">%n" +
            "    <testcase classname=\"Comparison\" name=\"Report Generation\">%n" +
            "      <error message=\"%s\"/>%n" +
            "    </testcase>%n" +
            "  </testsuite>%n" +
            "</testsuites>",
            LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
            escapeXml(e.getMessage())
        );
    }
}
