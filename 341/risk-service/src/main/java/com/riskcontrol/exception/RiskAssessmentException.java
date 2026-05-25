package com.riskcontrol.exception;

public class RiskAssessmentException extends RuntimeException {

    private final int code;

    public RiskAssessmentException(String message) {
        super(message);
        this.code = 500;
    }

    public RiskAssessmentException(String message, int code) {
        super(message);
        this.code = code;
    }

    public RiskAssessmentException(String message, Throwable cause) {
        super(message, cause);
        this.code = 500;
    }

    public int getCode() {
        return code;
    }
}
