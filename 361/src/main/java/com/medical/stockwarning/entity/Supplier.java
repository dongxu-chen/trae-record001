package com.medical.stockwarning.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@Entity
@Table(name = "t_supplier")
public class Supplier extends BaseEntity {

    @Column(name = "supplier_code", nullable = false, length = 32, unique = true)
    private String supplierCode;

    @Column(name = "supplier_name", nullable = false, length = 200)
    private String supplierName;

    @Column(name = "contact_person", length = 50)
    private String contactPerson;

    @Column(name = "contact_phone", length = 30)
    private String contactPhone;

    @Column(name = "address", length = 300)
    private String address;

    @Column(name = "lead_time_days")
    private Integer leadTimeDays = 14;

    @Column(name = "min_order_quantity")
    private Integer minOrderQuantity = 1;

    @Column(name = "is_active")
    private Integer isActive = 1;
}
