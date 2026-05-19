package com.smartschedule.config;

import com.smartschedule.entity.*;
import com.smartschedule.repository.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;
import java.util.Set;

@Component
@Profile("demo")
public class SampleDataInitializer implements CommandLineRunner {

    @Autowired
    private SkillRepository skillRepository;

    @Autowired
    private ShiftTypeRepository shiftTypeRepository;

    @Autowired
    private EmployeeRepository employeeRepository;

    @Override
    public void run(String... args) {
        if (skillRepository.count() == 0) {
            initializeSkills();
        }
        if (shiftTypeRepository.count() == 0) {
            initializeShiftTypes();
        }
        if (employeeRepository.count() == 0) {
            initializeEmployees();
        }
    }

    private void initializeSkills() {
        String[][] skills = {
            {"医生", "具备执业医师资格"},
            {"护士", "注册护士资格"},
            {"药师", "药学专业资格"},
            {"检验师", "医学检验资格"},
            {"影像师", "医学影像资格"}
        };

        for (String[] s : skills) {
            Skill skill = new Skill();
            skill.setName(s[0]);
            skill.setDescription(s[1]);
            skillRepository.save(skill);
        }
    }

    private void initializeShiftTypes() {
        Object[][] shiftTypes = {
            {"MORNING", "早班", LocalTime.of(8, 0), LocalTime.of(16, 0), 8, "#4CAF50"},
            {"AFTERNOON", "中班", LocalTime.of(14, 0), LocalTime.of(22, 0), 8, "#FF9800"},
            {"NIGHT", "夜班", LocalTime.of(22, 0), LocalTime.of(6, 0), 8, "#9C27B0"},
            {"DAY", "白班", LocalTime.of(9, 0), LocalTime.of(17, 0), 8, "#2196F3"}
        };

        for (Object[] st : shiftTypes) {
            ShiftType shiftType = new ShiftType();
            shiftType.setCode((String) st[0]);
            shiftType.setName((String) st[1]);
            shiftType.setStartTime((LocalTime) st[2]);
            shiftType.setEndTime((LocalTime) st[3]);
            shiftType.setDurationHours((Integer) st[4]);
            shiftType.setColor((String) st[5]);
            shiftType.setIsActive(true);
            shiftTypeRepository.save(shiftType);
        }
    }

    private void initializeEmployees() {
        List<Skill> allSkills = skillRepository.findAll();
        Skill doctorSkill = allSkills.stream().filter(s -> s.getName().equals("医生")).findFirst().orElse(null);
        Skill nurseSkill = allSkills.stream().filter(s -> s.getName().equals("护士")).findFirst().orElse(null);
        Skill pharmacistSkill = allSkills.stream().filter(s -> s.getName().equals("药师")).findFirst().orElse(null);
        Skill labSkill = allSkills.stream().filter(s -> s.getName().equals("检验师")).findFirst().orElse(null);
        Skill imagingSkill = allSkills.stream().filter(s -> s.getName().equals("影像师")).findFirst().orElse(null);

        createEmployee("张三", "EMP001", Set.of(doctorSkill, nurseSkill),
                Set.of("MORNING", "DAY"), Set.of(DayOfWeek.SUNDAY), Set.of("NIGHT"));
        createEmployee("李四", "EMP002", Set.of(nurseSkill),
                Set.of("AFTERNOON"), Set.of(), Set.of("NIGHT"));
        createEmployee("王五", "EMP003", Set.of(nurseSkill, pharmacistSkill),
                Set.of("MORNING"), Set.of(DayOfWeek.SATURDAY), Set.of());
        createEmployee("赵六", "EMP004", Set.of(nurseSkill),
                Set.of("NIGHT"), Set.of(), Set.of("MORNING"));
        createEmployee("钱七", "EMP005", Set.of(labSkill),
                Set.of("DAY"), Set.of(DayOfWeek.SUNDAY, DayOfWeek.SATURDAY), Set.of());
        createEmployee("孙八", "EMP006", Set.of(nurseSkill),
                Set.of("AFTERNOON"), Set.of(), Set.of("NIGHT"));
        createEmployee("周九", "EMP007", Set.of(imagingSkill),
                Set.of("MORNING"), Set.of(DayOfWeek.SUNDAY), Set.of());
        createEmployee("吴十", "EMP008", Set.of(nurseSkill),
                Set.of("MORNING"), Set.of(), Set.of());
    }

    private void createEmployee(String name, String employeeNo, Set<Skill> skills,
                                Set<String> preferredShifts, Set<DayOfWeek> unavailableDays,
                                Set<String> unwantedShifts) {
        Employee employee = new Employee();
        employee.setName(name);
        employee.setEmployeeNo(employeeNo);
        employee.setSkills(skills);
        employee.setMaxWeeklyHours(40);
        employee.setMaxDailyHours(8);
        employee.setMinWeeklyHours(20);
        employee.setMaxConsecutiveDays(5);
        employee.setPreferredShiftTypes(preferredShifts);
        employee.setUnavailableDays(unavailableDays);
        employee.setUnwantedShiftTypes(unwantedShifts);
        employee.setIsActive(true);
        employeeRepository.save(employee);
    }

    public void createSampleScheduleRequirements(Schedule schedule) {
        List<ShiftType> shiftTypes = shiftTypeRepository.findAll();
        ShiftType morning = shiftTypes.stream().filter(s -> s.getCode().equals("MORNING")).findFirst().orElse(null);
        ShiftType afternoon = shiftTypes.stream().filter(s -> s.getCode().equals("AFTERNOON")).findFirst().orElse(null);
        ShiftType night = shiftTypes.stream().filter(s -> s.getCode().equals("NIGHT")).findFirst().orElse(null);

        LocalDate startDate = schedule.getStartDate();
        LocalDate endDate = schedule.getEndDate();

        List<Skill> allSkills = skillRepository.findAll();
        Skill nurseSkill = allSkills.stream().filter(s -> s.getName().equals("护士")).findFirst().orElse(null);

        for (LocalDate date = startDate; !date.isAfter(endDate); date = date.plusDays(1)) {
            if (morning != null) {
                ShiftRequirement req1 = new ShiftRequirement();
                req1.setDate(date);
                req1.setShiftType(morning);
                req1.setRequiredSkill(nurseSkill);
                req1.setRequiredCount(2);
                req1.setSchedule(schedule);
            }

            if (afternoon != null) {
                ShiftRequirement req2 = new ShiftRequirement();
                req2.setDate(date);
                req2.setShiftType(afternoon);
                req2.setRequiredSkill(nurseSkill);
                req2.setRequiredCount(2);
                req2.setSchedule(schedule);
            }

            if (night != null) {
                ShiftRequirement req3 = new ShiftRequirement();
                req3.setDate(date);
                req3.setShiftType(night);
                req3.setRequiredSkill(nurseSkill);
                req3.setRequiredCount(1);
                req3.setSchedule(schedule);
            }
        }
    }
}
