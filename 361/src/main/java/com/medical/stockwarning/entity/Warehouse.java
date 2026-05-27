package com.medical.stockwarning.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@Entity
@Table(name = "t_warehouse")
public class Warehouse extends BaseEntity {

    @Column(name = "warehouse_code", nullable = false, length = 32, unique = true)
    private String warehouseCode;

    @Column(name = "warehouse_name", nullable = false, length = 100)
    private String warehouseName;

    @Column(name = "location", nullable = false, length = 200)
    private String location;

    @Column(name = "capacity")
    private Integer capacity = 0;

    @Column(name = "status")
    private Integer status = 1;

    @Column(name = "is_main")
    private Integer isMain = 0;
}
