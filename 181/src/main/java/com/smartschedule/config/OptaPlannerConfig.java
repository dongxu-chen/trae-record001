package com.smartschedule.config;

import org.optaplanner.core.api.score.buildin.hardmediumsoft.HardMediumSoftScore;
import org.optaplanner.core.api.solver.SolverFactory;
import org.optaplanner.core.config.solver.SolverConfig;
import org.optaplanner.core.config.solver.termination.TerminationConfig;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.smartschedule.planner.PlannerShiftAssignment;
import com.smartschedule.planner.ScheduleConstraintProvider;
import com.smartschedule.planner.ScheduleSolution;

@Configuration
public class OptaPlannerConfig {

    @Bean
    public SolverFactory<ScheduleSolution> solverFactory() {
        SolverConfig solverConfig = new SolverConfig()
                .withSolutionClass(ScheduleSolution.class)
                .withEntityClasses(PlannerShiftAssignment.class)
                .withConstraintProviderClass(ScheduleConstraintProvider.class)
                .withTerminationConfig(new TerminationConfig()
                        .withSecondsSpentLimit(30L)
                        .withScoreCalculationCountLimit(100000L)
                        .withBestScoreLimit(HardMediumSoftScore.of(0, 0, 0)));

        return SolverFactory.create(solverConfig);
    }
}
