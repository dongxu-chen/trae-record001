package com.smartschedule.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.DayOfWeek;
import java.util.Set;

@Data
@Entity
@Table(name = "employees")
public class Employee {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(unique = true, nullable = false, length = 50)
    private String employeeNo;

    @ManyToMany(fetch = FetchType.EAGER)
    @JoinTable(
        name = "employee_skills",
        joinColumns = @JoinColumn(name = "employee_id"),
        inverseJoinColumns = @JoinColumn(name = "skill_id")
    )
    private Set<Skill> skills;

    @Column(nullable = false)
    private Integer maxWeeklyHours = 40;

    @Column(nullable = false)
    private Integer maxDailyHours = 8;

    @Column(nullable = false)
    private Integer minWeeklyHours = 20;

    @Column(nullable = false)
    private Integer maxConsecutiveDays = 5;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "employee_preferred_shifts", joinColumns = @JoinColumn(name = "employee_id"))
    @Column(name = "shift_type")
    private Set<String> preferredShiftTypes;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "employee_unavailable_days", joinColumns = @JoinColumn(name = "employee_id"))
    @Column(name = "day_of_week")
    private Set<DayOfWeek> unavailableDays;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "employee_unwanted_shifts", joinColumns = @JoinColumn(name = "employee_id"))
    @Column(name = "shift_type")
    private Set<String> unwantedShiftTypes;

    private Boolean isActive = true;
}
