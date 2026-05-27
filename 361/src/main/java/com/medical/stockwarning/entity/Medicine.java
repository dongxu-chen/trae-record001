package com.medical.stockwarning.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@Entity
@Table(name = "t_medicine")
public class Medicine extends BaseEntity {

    @Column(name = "medicine_code", nullable = false, length = 32, unique = true)
    private String medicineCode;

    @Column(name = "medicine_name", nullable = false, length = 200)
    private String medicineName;

    @Column(name = "generic_name", length = 200)
    private String genericName;

    @Column(name = "specification", length = 100)
    private String specification;

    @Column(name = "manufacturer", length = 200)
    private String manufacturer;

    @Column(name = "unit", nullable = false, length = 20)
    private String unit;

    @Column(name = "category", length = 50)
    private String category;

    @Column(name = "dosage_form", length = 50)
    private String dosageForm;

    @Column(name = "is_prescription")
    private Integer isPrescription = 0;

    @Column(name = "is_active")
    private Integer isActive = 1;
}
