package com.homestay.service;

import co.elastic.clients.elasticsearch._types.query_dsl.BoolQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import com.homestay.common.BusinessException;
import com.homestay.common.UserContext;
import com.homestay.document.HouseDocument;
import com.homestay.entity.House;
import com.homestay.entity.HouseCalendar;
import com.homestay.entity.HouseDailyStats;
import com.homestay.entity.HouseFacility;
import com.homestay.mapper.HouseCalendarMapper;
import com.homestay.mapper.HouseDailyStatsMapper;
import com.homestay.mapper.HouseFacilityMapper;
import com.homestay.mapper.HouseMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.elasticsearch.client.elc.NativeQuery;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.SearchHit;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class PricingService {

    @Autowired
    private HouseMapper houseMapper;

    @Autowired
    private HouseCalendarMapper houseCalendarMapper;

    @Autowired
    private HouseDailyStatsMapper houseDailyStatsMapper;

    @Autowired
    private HouseFacilityMapper houseFacilityMapper;

    @Autowired
    private ElasticsearchOperations elasticsearchOperations;

    public Map<String, Object> getPricingSuggestion(Long houseId) {
        Long userId = UserContext.getUserId();
        House house = houseMapper.selectById(houseId);
        if (house == null) {
            throw new BusinessException("房源不存在");
        }
        if (!house.getHostId().equals(userId)) {
            throw new BusinessException("无权限查看该房源的定价建议");
        }

        Map<String, Object> result = new HashMap<>();
        result.put("houseId", houseId);
        result.put("currentBasePrice", house.getBasePrice());

        List<HouseDocument> nearbyHouses = findNearbyHouses(house);
        if (!nearbyHouses.isEmpty()) {
            BigDecimal avgPrice = nearbyHouses.stream()
                    .map(HouseDocument::getBasePrice)
                    .filter(Objects::nonNull)
                    .reduce(BigDecimal.ZERO, BigDecimal::add)
                    .divide(BigDecimal.valueOf(nearbyHouses.size()), 2, RoundingMode.HALF_UP);

            BigDecimal minPrice = nearbyHouses.stream()
                    .map(HouseDocument::getBasePrice)
                    .filter(Objects::nonNull)
                    .min(BigDecimal::compareTo)
                    .orElse(BigDecimal.ZERO);

            BigDecimal maxPrice = nearbyHouses.stream()
                    .map(HouseDocument::getBasePrice)
                    .filter(Objects::nonNull)
                    .max(BigDecimal::compareTo)
                    .orElse(BigDecimal.ZERO);

            Map<String, Object> competitorAnalysis = new HashMap<>();
            competitorAnalysis.put("count", nearbyHouses.size());
            competitorAnalysis.put("avgPrice", avgPrice);
            competitorAnalysis.put("minPrice", minPrice);
            competitorAnalysis.put("maxPrice", maxPrice);
            competitorAnalysis.put("houses", nearbyHouses.stream()
                    .limit(10)
                    .map(h -> {
                        Map<String, Object> map = new HashMap<>();
                        map.put("id", h.getId());
                        map.put("title", h.getTitle());
                        map.put("basePrice", h.getBasePrice());
                        map.put("rating", h.getRating());
                        map.put("reviewCount", h.getReviewCount());
                        return map;
                    })
                    .collect(Collectors.toList()));
            result.put("competitorAnalysis", competitorAnalysis);

            BigDecimal suggestedPrice = calculateSuggestedPrice(house, avgPrice, nearbyHouses);
            result.put("suggestedPrice", suggestedPrice);

            String pricingStrategy = generatePricingStrategy(house, avgPrice, suggestedPrice);
            result.put("pricingStrategy", pricingStrategy);
        }

        Map<String, Object> occupancyAnalysis = getOccupancyAnalysis(houseId);
        result.put("occupancyAnalysis", occupancyAnalysis);

        List<Map<String, Object>> dateSuggestions = generateDatePricingSuggestions(houseId);
        result.put("dateSuggestions", dateSuggestions);

        return result;
    }

    private List<HouseDocument> findNearbyHouses(House house) {
        if (house.getLongitude() == null || house.getLatitude() == null) {
            return Collections.emptyList();
        }

        List<Query> queries = new ArrayList<>();
        queries.add(Query.of(q -> q.term(t -> t.field("status").value(1))));
        queries.add(Query.of(q -> q.term(t -> t.field("city").value(house.getCity()))));
        queries.add(Query.of(q -> q.term(t -> t.field("roomCount").value(house.getRoomCount()))));
        queries.add(Query.of(q -> q.term(t -> t.field("maxGuests").value(house.getMaxGuests())));
        queries.add(Query.of(q -> q.bool(b -> b.mustNot(m -> m.term(t -> t.field("id").value(house.getId())))));

        BoolQuery boolQuery = new BoolQuery.Builder().must(queries).build();

        NativeQuery query = NativeQuery.builder()
                .withQuery(q -> q.bool(boolQuery))
                .withMaxResults(50)
                .build();

        SearchHits<HouseDocument> searchHits = elasticsearchOperations.search(query, HouseDocument.class);
        return searchHits.getSearchHits().stream()
                .map(SearchHit::getContent)
                .collect(Collectors.toList());
    }

    private BigDecimal calculateSuggestedPrice(House house, BigDecimal avgPrice, List<HouseDocument> nearbyHouses) {
        BigDecimal basePrice = house.getBasePrice();
        BigDecimal rating = house.getRating() != null ? house.getRating() : new BigDecimal("5.0");

        double priceAdjustment = 1.0;

        if (rating.compareTo(new BigDecimal("4.5")) >= 0) {
            priceAdjustment += 0.1;
        } else if (rating.compareTo(new BigDecimal("4.0")) >= 0) {
            priceAdjustment += 0.05;
        } else if (rating.compareTo(new BigDecimal("3.5")) < 0) {
            priceAdjustment -= 0.1;
        }

        Integer reviewCount = house.getReviewCount() != null ? house.getReviewCount() : 0;
        if (reviewCount > 100) {
            priceAdjustment += 0.05;
        }

        Long houseFacilityCount = houseFacilityMapper.selectCount(
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<HouseFacility>()
                        .eq(HouseFacility::getHouseId, house.getId()));
        if (houseFacilityCount != null && nearbyHouses.size() > 0) {
            int avgFacilityCount = nearbyHouses.stream()
                    .mapToInt(h -> h.getFacilities() != null ? h.getFacilities().size() : 0)
                    .sum() / nearbyHouses.size();
            if (houseFacilityCount > avgFacilityCount) {
                priceAdjustment += 0.05;
            }
        }

        return avgPrice.multiply(BigDecimal.valueOf(priceAdjustment)).setScale(2, RoundingMode.HALF_UP);
    }

    private String generatePricingStrategy(House house, BigDecimal avgPrice, BigDecimal suggestedPrice) {
        StringBuilder strategy = new StringBuilder();
        BigDecimal basePrice = house.getBasePrice();

        if (basePrice.compareTo(suggestedPrice) > 0) {
            strategy.append("建议调低价格至 ").append(suggestedPrice)
                    .append(" 元（当前价格高于市场均价").append(basePrice.subtract(suggestedPrice)).append("元）。");
            strategy.append("当前价格比周边均价高").append(basePrice.subtract(avgPrice).divide(avgPrice, 2, RoundingMode.HALF_UP).multiply(new BigDecimal("100"))).append("%，");
            strategy.append("可能会影响预订率。");
        } else if (basePrice.compareTo(suggestedPrice) < 0) {
            strategy.append("建议调高价格至 ").append(suggestedPrice)
                    .append(" 元（当前价格低于建议价").append(suggestedPrice.subtract(basePrice)).append("元）。");
            strategy.append("您的房源评分和设施有优势，可适当提高价格增加收益。");
        } else {
            strategy.append("当前价格合理，建议维持现状。");
        }

        strategy.append("周边 ").append(avgPrice).append(" 元的均价可作为参考。");
        return strategy.toString();
    }

    private Map<String, Object> getOccupancyAnalysis(Long houseId) {
        Map<String, Object> result = new HashMap<>();

        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusDays(30);

        Map<String, Object> stats = houseDailyStatsMapper.getHouseSummary(houseId, startDate, endDate);
        if (stats != null) {
            BigDecimal occupancyRate = (BigDecimal) stats.get("avg_occupancy");
            result.put("last30DaysOccupancy", occupancyRate);
            result.put("last30DaysOrders", stats.get("total_orders"));
            result.put("last30DaysIncome", stats.get("total_income"));

            if (occupancyRate != null) {
                if (occupancyRate.compareTo(new BigDecimal("0.7")) >= 0) {
                    result.put("demandLevel", "HIGH");
                    result.put("demandSuggestion", "需求旺盛，建议适当提高价格");
                } else if (occupancyRate.compareTo(new BigDecimal("0.5")) >= 0) {
                    result.put("demandLevel", "MEDIUM");
                    result.put("demandSuggestion", "需求平稳，建议保持价格稳定");
                } else {
                    result.put("demandLevel", "LOW");
                    result.put("demandSuggestion", "需求较低，建议考虑降价促销");
                }
            }
        }

        return result;
    }

    private List<Map<String, Object>> generateDatePricingSuggestions(Long houseId) {
        List<Map<String, Object>> suggestions = new ArrayList<>();
        LocalDate today = LocalDate.now();

        for (int i = 0; i < 30; i++) {
            LocalDate date = today.plusDays(i);
            HouseCalendar calendar = houseCalendarMapper.selectOne(
                    new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<HouseCalendar>()
                            .eq(HouseCalendar::getHouseId, houseId)
                            .eq(HouseCalendar::getDate, date));

            if (calendar != null) {
                Map<String, Object> suggestion = new HashMap<>();
                suggestion.put("date", date);
                suggestion.put("currentPrice", calendar.getPrice());
                suggestion.put("stock", calendar.getStock());

                boolean isWeekend = date.getDayOfWeek().getValue() >= 6;
                boolean isHoliday = isHoliday(date);

                BigDecimal suggestedPrice = calendar.getPrice();
                String tip = "";

                if (isWeekend) {
                    suggestedPrice = calendar.getPrice().multiply(new BigDecimal("1.2")).setScale(0, RoundingMode.HALF_UP);
                    tip = "周末建议加价20%";
                }
                if (isHoliday) {
                    suggestedPrice = calendar.getPrice().multiply(new BigDecimal("1.5")).setScale(0, RoundingMode.HALF_UP);
                    tip = "节假日建议加价50%";
                }

                suggestion.put("suggestedPrice", suggestedPrice);
                suggestion.put("isWeekend", isWeekend);
                suggestion.put("isHoliday", isHoliday);
                suggestion.put("tip", tip);
                suggestions.add(suggestion);
            }
        }

        return suggestions;
    }

    private boolean isHoliday(LocalDate date) {
        List<LocalDate> holidays = Arrays.asList(
                LocalDate.of(date.getYear(), 1, 1),
                LocalDate.of(date.getYear(), 5, 1),
                LocalDate.of(date.getYear(), 10, 1),
                LocalDate.of(date.getYear(), 10, 2),
                LocalDate.of(date.getYear(), 10, 3),
                LocalDate.of(date.getYear(), 10, 4),
                LocalDate.of(date.getYear(), 10, 5),
                LocalDate.of(date.getYear(), 10, 6),
                LocalDate.of(date.getYear(), 10, 7)
        );
        return holidays.contains(date);
    }
}
