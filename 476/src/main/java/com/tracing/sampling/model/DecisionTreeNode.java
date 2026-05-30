package com.tracing.sampling.model;

import java.util.ArrayList;
import java.util.List;

public class DecisionTreeNode {
    
    private String nodeId;
    private String condition;
    private String description;
    private boolean result;
    private String decision;
    private double contribution;
    private List<DecisionTreeNode> children;
    
    private String variableName;
    private String operator;
    private String thresholdValue;
    private String actualValue;
    private String pass;

    public DecisionTreeNode() {
        this.children = new ArrayList<>();
    }

    public DecisionTreeNode(String nodeId, String condition, String description) {
        this.nodeId = nodeId;
        this.condition = condition;
        this.description = description;
        this.children = new ArrayList<>();
    }

    public String getNodeId() {
        return nodeId;
    }

    public void setNodeId(String nodeId) {
        this.nodeId = nodeId;
    }

    public String getCondition() {
        return condition;
    }

    public void setCondition(String condition) {
        this.condition = condition;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public boolean isResult() {
        return result;
    }

    public void setResult(boolean result) {
        this.result = result;
    }

    public String getDecision() {
        return decision;
    }

    public void setDecision(String decision) {
        this.decision = decision;
    }

    public double getContribution() {
        return contribution;
    }

    public void setContribution(double contribution) {
        this.contribution = contribution;
    }

    public List<DecisionTreeNode> getChildren() {
        return children;
    }

    public void setChildren(List<DecisionTreeNode> children) {
        this.children = children;
    }

    public void addChild(DecisionTreeNode child) {
        this.children.add(child);
    }

    public String getVariableName() {
        return variableName;
    }

    public void setVariableName(String variableName) {
        this.variableName = variableName;
    }

    public String getOperator() {
        return operator;
    }

    public void setOperator(String operator) {
        this.operator = operator;
    }

    public String getThresholdValue() {
        return thresholdValue;
    }

    public void setThresholdValue(String thresholdValue) {
        this.thresholdValue = thresholdValue;
    }

    public String getActualValue() {
        return actualValue;
    }

    public void setActualValue(String actualValue) {
        this.actualValue = actualValue;
    }

    public String getPass() {
        return pass;
    }

    public void setPass(String pass) {
        this.pass = pass;
    }
}
