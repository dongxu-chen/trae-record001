package com.mfa.service;

import com.mfa.dto.AuthHealthDashboard;
import com.mfa.dto.AuthMethodStats;

import java.time.LocalDate;
import java.util.List;

public interface AuthHealthService {

    AuthHealthDashboard getDashboard();

    List<AuthMethodStats> getAuthMethodStats(LocalDate startDate, LocalDate endDate);

    AuthHealthDashboard getDashboardForDateRange(LocalDate startDate, LocalDate endDate);
}
