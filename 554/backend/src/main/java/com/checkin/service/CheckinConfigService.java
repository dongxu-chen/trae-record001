package com.checkin.service;

import com.checkin.entity.CheckinConfig;
import com.checkin.entity.CheckinTreasure;
import com.checkin.repository.CheckinConfigRepository;
import com.checkin.repository.CheckinTreasureRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.List;

@Service
public class CheckinConfigService {

    @Autowired
    private CheckinConfigRepository checkinConfigRepository;

    @Autowired
    private CheckinTreasureRepository checkinTreasureRepository;

    @PostConstruct
    public void initDefaultConfig() {
        initDailyConfig();
        initWeeklyConfig();
        initMonthlyConfig();
        initTreasureConfig();
    }

    private void initDailyConfig() {
        List<CheckinConfig> existing = checkinConfigRepository
                .findByPeriodTypeAndEnabledTrueOrderByDayIndexAsc("DAILY");
        
        if (existing.isEmpty()) {
            List<CheckinConfig> configs = new ArrayList<>();
            
            int[] days = {1, 2, 3, 4, 5, 6, 7, 14, 21, 30};
            String[] types = {"POINTS", "POINTS", "POINTS", "POINTS", "POINTS", 
                              "POINTS", "RECHECK_CARD", "POINTS", "POINTS", "RECHECK_CARD"};
            int[] values = {10, 15, 20, 25, 30, 35, 1, 100, 200, 3};
            String[] names = {"10积分", "15积分", "20积分", "25积分", "30积分", 
                              "35积分", "1张补签卡", "100积分", "200积分", "3张补签卡"};

            for (int i = 0; i < days.length; i++) {
                CheckinConfig config = new CheckinConfig();
                config.setPeriodType("DAILY");
                config.setDayIndex(days[i]);
                config.setRewardType(types[i]);
                config.setRewardValue(values[i]);
                config.setRewardName(names[i]);
                config.setEnabled(true);
                configs.add(config);
            }
            
            checkinConfigRepository.saveAll(configs);
        }
    }

    private void initWeeklyConfig() {
        List<CheckinConfig> existing = checkinConfigRepository
                .findByPeriodTypeAndEnabledTrueOrderByDayIndexAsc("WEEKLY");
        
        if (existing.isEmpty()) {
            List<CheckinConfig> configs = new ArrayList<>();
            
            String[] weekDays = {"周一", "周二", "周三", "周四", "周五", "周六", "周日"};
            int[] values = {20, 20, 20, 20, 20, 50, 50};

            for (int i = 1; i <= 7; i++) {
                CheckinConfig config = new CheckinConfig();
                config.setPeriodType("WEEKLY");
                config.setDayIndex(i);
                config.setRewardType("POINTS");
                config.setRewardValue(values[i-1]);
                config.setRewardName(weekDays[i-1] + "奖励" + values[i-1] + "积分");
                config.setEnabled(true);
                configs.add(config);
            }
            
            checkinConfigRepository.saveAll(configs);
        }
    }

    private void initMonthlyConfig() {
        List<CheckinConfig> existing = checkinConfigRepository
                .findByPeriodTypeAndEnabledTrueOrderByDayIndexAsc("MONTHLY");
        
        if (existing.isEmpty()) {
            List<CheckinConfig> configs = new ArrayList<>();
            
            int[] days = {1, 5, 10, 15, 20, 25, 30};
            int[] values = {30, 50, 100, 150, 200, 300, 500};

            for (int i = 0; i < days.length; i++) {
                CheckinConfig config = new CheckinConfig();
                config.setPeriodType("MONTHLY");
                config.setDayIndex(days[i]);
                config.setRewardType("POINTS");
                config.setRewardValue(values[i]);
                config.setRewardName("第" + days[i] + "天奖励" + values[i] + "积分");
                config.setEnabled(true);
                configs.add(config);
            }
            
            checkinConfigRepository.saveAll(configs);
        }
    }

    private void initTreasureConfig() {
        List<CheckinTreasure> existing = checkinTreasureRepository
                .findByPeriodTypeAndEnabledTrueOrderByTotalDaysAsc("DAILY");
        
        if (existing.isEmpty()) {
            List<CheckinTreasure> treasures = new ArrayList<>();
            
            int[] days = {7, 14, 21, 28};
            String[] types = {"POINTS", "POINTS", "RECHECK_CARD", "POINTS"};
            int[] values = {100, 200, 2, 500};
            String[] names = {"周签到宝箱", "双周签到宝箱", "三周签到宝箱", "月签到大宝箱"};
            String[] icons = {"📦", "🎁", "💎", "👑"};

            for (int i = 0; i < days.length; i++) {
                CheckinTreasure treasure = new CheckinTreasure();
                treasure.setPeriodType("DAILY");
                treasure.setTotalDays(days[i]);
                treasure.setRewardType(types[i]);
                treasure.setRewardValue(values[i]);
                treasure.setRewardName(names[i]);
                treasure.setIcon(icons[i]);
                treasure.setEnabled(true);
                treasures.add(treasure);
            }
            
            checkinTreasureRepository.saveAll(treasures);
        }
    }

    public List<CheckinConfig> getConfigs(String periodType) {
        return checkinConfigRepository
                .findByPeriodTypeAndEnabledTrueOrderByDayIndexAsc(periodType);
    }

    public CheckinConfig saveConfig(CheckinConfig config) {
        return checkinConfigRepository.save(config);
    }

    public void deleteConfig(Long id) {
        checkinConfigRepository.deleteById(id);
    }

    public List<CheckinTreasure> getTreasures(String periodType) {
        return checkinTreasureRepository
                .findByPeriodTypeAndEnabledTrueOrderByTotalDaysAsc(periodType);
    }

    public CheckinTreasure saveTreasure(CheckinTreasure treasure) {
        return checkinTreasureRepository.save(treasure);
    }

    public void deleteTreasure(Long id) {
        checkinTreasureRepository.deleteById(id);
    }
}
