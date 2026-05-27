# -*- coding: utf-8 -*-
import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

results = []

def log(msg):
    results.append(msg)
    print(msg)

log("=" * 60)
log("Test 1: New Module Imports")
try:
    from src.models.sleep_prescription import SleepPrescriptionGenerator, CircadianRhythmAnalyzer, AgeGroupComparator
    log("OK: SleepPrescriptionGenerator + CircadianRhythmAnalyzer + AgeGroupComparator")
except Exception as e:
    log(f"FAIL: {e}")
    import traceback
    log(traceback.format_exc())

try:
    from src.visualization import (
        create_circadian_schedule_plot, create_circadian_alignment_gauge,
        create_age_percentile_chart, create_age_group_comparison_radar,
        create_prescription_timeline, create_weekly_plan_timeline
    )
    log("OK: All new visualization functions")
except Exception as e:
    log(f"FAIL: {e}")

log("\n" + "=" * 60)
log("Test 2: SleepPrescriptionGenerator")
try:
    sp = SleepPrescriptionGenerator()
    sample_stages = ['清醒']*5 + ['浅睡']*10 + ['深睡']*15 + ['REM']*10 + ['浅睡']*20 + ['深睡']*10 + ['REM']*5 + ['浅睡']*5

    from src.models.sleep_quality_analyzer import SleepQualityAnalyzer
    qa = SleepQualityAnalyzer()
    stage_analysis = qa.analyze_sleep_stages(sample_stages)
    sleep_score = qa.calculate_sleep_score(stage_analysis)
    regularity = qa.analyze_sleep_regularity(sample_stages)

    lifestyle = {'exercise_minutes': 30, 'exercise_intensity': 'moderate',
                 'caffeine_intake': 2, 'alcohol_intake': 1, 'stress_level': 6,
                 'bedtime_consistency': 5, 'bedtime_hour': 23.5}
    history = {'exercise_minutes_1d': 40, 'exercise_minutes_2d': 20, 'exercise_minutes_3d': 60}

    prescription = sp.generate_prescription(sleep_score, stage_analysis, regularity, lifestyle, history)

    log(f"Summary: score={prescription['summary']['current_score']:.1f}, issues={prescription['summary']['primary_issues']}")
    log(f"Schedule: bedtime={prescription['schedule_adjustment']['recommended_bedtime']:.1f}, wakeup={prescription['schedule_adjustment']['recommended_wakeup']:.1f}")
    log(f"Schedule grade: {prescription['schedule_adjustment']['schedule_grade']}")
    log(f"Pre-sleep routine: {prescription['pre_sleep_routine']['prep_duration']}min, {len(prescription['pre_sleep_routine']['routine_steps'])} steps")
    log(f"Lifestyle prescriptions: {len(prescription['lifestyle_prescription'])}")
    log(f"Exercise prescriptions: {len(prescription['exercise_prescription'])}")
    log(f"Environment prescriptions: {len(prescription['environment_prescription'])}")
    log(f"Weekly plan: {prescription['weekly_plan']['phase']}, {len(prescription['weekly_plan']['weekly_goals'])} goals")
    log(f"Expected improvement: +{prescription['expected_improvement']['potential_gain']:.1f} points")
    log("OK: SleepPrescriptionGenerator works")
except Exception as e:
    log(f"FAIL: {e}")
    import traceback
    log(traceback.format_exc())

log("\n" + "=" * 60)
log("Test 3: CircadianRhythmAnalyzer")
try:
    cr = CircadianRhythmAnalyzer()
    circadian = cr.predict_circadian_type(
        sample_stages, bedtime_hour=23.5, wakeup_hour=7.0, history_factors=None
    )
    log(f"Chronotype: {circadian['chronotype_label']}")
    log(f"Optimal bedtime: {circadian['optimal_bedtime']:.1f}")
    log(f"Optimal wakeup: {circadian['optimal_wakeup']:.1f}")
    log(f"Optimal sleep duration: {circadian['optimal_sleep_duration']:.1f}h")
    log(f"Alignment score: {circadian['alignment_score']:.1f}")
    log(f"Melatonin start: {circadian['biological_markers']['melatonin_start']:.1f}")
    log(f"Cortisol rise: {circadian['biological_markers']['cortisol_rise']:.1f}")
    log(f"Adjustment: {circadian['adjustment_recommendation']['status']}")
    log(f"Schedule entries: {len(circadian['optimal_schedule'])}")

    phase = cr.get_current_phase(14.0)
    log(f"Current phase at 14:00: {phase['phase']} - {phase['description']}")
    log("OK: CircadianRhythmAnalyzer works")
except Exception as e:
    log(f"FAIL: {e}")
    import traceback
    log(traceback.format_exc())

log("\n" + "=" * 60)
log("Test 4: AgeGroupComparator")
try:
    ac = AgeGroupComparator()
    percentile = ac.calculate_percentile_rank(75.0, age=30, gender='male')
    log(f"Age group: {percentile['age_group_label']}")
    log(f"Percentile: {percentile['percentile']:.1f}")
    log(f"Rank: {percentile['rank']}")
    log(f"Description: {percentile['description']}")
    log(f"Group mean: {percentile['group_norm']['mean_score']}")

    comparison = ac.compare_to_group(stage_analysis, age=30, gender='male')
    log(f"Comparisons: {len(comparison['comparisons'])}")
    for c in comparison['comparisons']:
        log(f"  {c['metric']}: yours={c['your_value']}, group={c['group_mean']}, status={c['status']}")

    chart_data = ac.generate_comparison_chart_data(75.0, age=30)
    log(f"Chart data: {len(chart_data['percentile_labels'])} percentiles, position={chart_data['your_position']}")

    percentile_65 = ac.calculate_percentile_rank(70.0, age=65, gender='female')
    log(f"Age 65 female: {percentile_65['age_group_label']}, P{percentile_65['percentile']:.1f}, rank={percentile_65['rank']}")
    log("OK: AgeGroupComparator works")
except Exception as e:
    log(f"FAIL: {e}")
    import traceback
    log(traceback.format_exc())

log("\n" + "=" * 60)
log("Test 5: Visualization Functions")
try:
    import plotly.graph_objects as go

    fig = create_circadian_alignment_gauge(85.0, "中间型")
    log(f"OK: create_circadian_alignment_gauge -> {type(fig).__name__}")

    chart_data = ac.generate_comparison_chart_data(75.0, age=30)
    fig = create_age_percentile_chart(chart_data, "青年(26-35岁)")
    log(f"OK: create_age_percentile_chart -> {type(fig).__name__}")

    fig = create_age_group_comparison_radar(stage_analysis, percentile['group_norm'])
    log(f"OK: create_age_group_comparison_radar -> {type(fig).__name__}")

    fig = create_prescription_timeline(prescription)
    log(f"OK: create_prescription_timeline -> {type(fig).__name__}")

    fig = create_weekly_plan_timeline(prescription['weekly_plan'])
    log(f"OK: create_weekly_plan_timeline -> {type(fig).__name__}")

    schedule_data = circadian['optimal_schedule']
    fig = create_circadian_schedule_plot(schedule_data, circadian['chronotype_label'])
    log(f"OK: create_circadian_schedule_plot -> {type(fig).__name__}")
    log("OK: All visualization functions work")
except Exception as e:
    log(f"FAIL: {e}")
    import traceback
    log(traceback.format_exc())

log("\n" + "=" * 60)
log("ALL TESTS COMPLETED")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_result.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))