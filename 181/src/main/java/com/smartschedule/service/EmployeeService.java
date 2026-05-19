package com.smartschedule.service;

import com.smartschedule.entity.Employee;
import com.smartschedule.repository.EmployeeRepository;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class EmployeeService {

    @Autowired
    private EmployeeRepository employeeRepository;

    @Transactional
    public Employee createEmployee(Employee employee) {
        return employeeRepository.save(employee);
    }

    public Employee getEmployee(Long id) {
        return employeeRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Employee not found with id: " + id));
    }

    public List<Employee> getAllEmployees() {
        return employeeRepository.findAll();
    }

    public List<Employee> getActiveEmployees() {
        return employeeRepository.findByIsActiveTrue();
    }

    @Transactional
    public Employee updateEmployee(Long id, Employee employeeDetails) {
        Employee employee = getEmployee(id);
        employee.setName(employeeDetails.getName());
        employee.setEmployeeNo(employeeDetails.getEmployeeNo());
        employee.setSkills(employeeDetails.getSkills());
        employee.setMaxWeeklyHours(employeeDetails.getMaxWeeklyHours());
        employee.setMaxDailyHours(employeeDetails.getMaxDailyHours());
        employee.setMinWeeklyHours(employeeDetails.getMinWeeklyHours());
        employee.setMaxConsecutiveDays(employeeDetails.getMaxConsecutiveDays());
        employee.setPreferredShiftTypes(employeeDetails.getPreferredShiftTypes());
        employee.setUnavailableDays(employeeDetails.getUnavailableDays());
        employee.setUnwantedShiftTypes(employeeDetails.getUnwantedShiftTypes());
        employee.setIsActive(employeeDetails.getIsActive());
        return employeeRepository.save(employee);
    }

    @Transactional
    public void deleteEmployee(Long id) {
        employeeRepository.deleteById(id);
    }
}
