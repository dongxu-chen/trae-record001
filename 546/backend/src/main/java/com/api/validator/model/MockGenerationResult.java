package com.api.validator.model;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class MockGenerationResult {

    private String path;
    private String method;
    private Integer statusCode;
    private String mockResponse;
    private boolean generated;
    private List<String> generationNotes = new ArrayList<>();

    public void addNote(String note) {
        this.generationNotes.add(note);
    }
}
