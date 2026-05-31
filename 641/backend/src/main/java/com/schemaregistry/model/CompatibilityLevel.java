package com.schemaregistry.model;

public enum CompatibilityLevel {
    NONE,
    FORWARD,
    BACKWARD,
    FULL,
    FORWARD_TRANSITIVE,
    BACKWARD_TRANSITIVE,
    FULL_TRANSITIVE
}
