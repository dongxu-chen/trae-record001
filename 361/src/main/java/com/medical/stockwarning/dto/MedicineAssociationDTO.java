package com.medical.stockwarning.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class MedicineAssociationDTO {

    private Long medicineId;
    private String medicineName;
    private Long associatedMedicineId;
    private String associatedMedicineName;
    private Integer coOccurrenceCount;
    private Integer medicineOccurrenceCount;
    private Integer associatedOccurrenceCount;
    private Double support;
    private Double confidence;
    private Double lift;
    private Integer associationCount;
    private Boolean isStrongAssociation;
}
