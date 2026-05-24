package com.homestay.service;

import co.elastic.clients.elasticsearch._types.GeoDistanceType;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.query_dsl.*;
import com.homestay.dto.HouseSearchDTO;
import com.homestay.dto.MapHouseDTO;
import com.homestay.entity.HouseCalendar;
import com.homestay.vo.HouseMapVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.elasticsearch.client.elc.NativeQuery;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.SearchHit;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.data.elasticsearch.core.query.HighlightQuery;
import org.springframework.data.elasticsearch.core.query.highlight.Highlight;
import org.springframework.data.elasticsearch.core.query.highlight.HighlightParameters;
import org.springframework.data.elasticsearch.core.query.highlight.HighlightField;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class HouseSearchService {

    @Autowired
    private ElasticsearchOperations elasticsearchOperations;

    @Autowired
    private HouseService houseService;

    public Map<String, Object> search(HouseSearchDTO dto) {
        List<Query> queries = new ArrayList<>();

        queries.add(Query.of(q -> q.term(t -> t.field("status").value(1))));

        if (StringUtils.hasText(dto.getKeyword())) {
            List<Query> keywordQueries = new ArrayList<>();
            keywordQueries.add(Query.of(q -> q.match(m -> m.field("title").query(dto.getKeyword()))));
            keywordQueries.add(Query.of(q -> q.match(m -> m.field("description").query(dto.getKeyword()))));
            keywordQueries.add(Query.of(q -> q.match(m -> m.field("address").query(dto.getKeyword()))));
            queries.add(Query.of(q -> q.bool(b -> b.should(keywordQueries))));
        }

        if (StringUtils.hasText(dto.getProvince())) {
            queries.add(Query.of(q -> q.term(t -> t.field("province").value(dto.getProvince()))));
        }
        if (StringUtils.hasText(dto.getCity())) {
            queries.add(Query.of(q -> q.term(t -> t.field("city").value(dto.getCity()))));
        }
        if (StringUtils.hasText(dto.getDistrict())) {
            queries.add(Query.of(q -> q.term(t -> t.field("district").value(dto.getDistrict()))));
        }

        if (dto.getMinPrice() != null || dto.getMaxPrice() != null) {
            RangeQuery.Builder rangeBuilder = new RangeQuery.Builder().field("basePrice");
            if (dto.getMinPrice() != null) {
                rangeBuilder.gte(dto.getMinPrice().doubleValue());
            }
            if (dto.getMaxPrice() != null) {
                rangeBuilder.lte(dto.getMaxPrice().doubleValue());
            }
            queries.add(Query.of(q -> q.range(rangeBuilder.build())));
        }

        if (dto.getRoomCount() != null) {
            queries.add(Query.of(q -> q.term(t -> t.field("roomCount").value(dto.getRoomCount()))));
        }
        if (dto.getBedCount() != null) {
            queries.add(Query.of(q -> q.term(t -> t.field("bedCount").value(dto.getBedCount()))));
        }
        if (dto.getBathCount() != null) {
            queries.add(Query.of(q -> q.term(t -> t.field("bathCount").value(dto.getBathCount()))));
        }
        if (dto.getMinGuests() != null) {
            queries.add(Query.of(q -> q.range(r -> r.field("maxGuests").gte(dto.getMinGuests()))));
        }

        if (!CollectionUtils.isEmpty(dto.getFacilities())) {
            for (String facility : dto.getFacilities()) {
                queries.add(Query.of(q -> q.term(t -> t.field("facilities").value(facility))));
            }
        }

        if (dto.getMinRating() != null) {
            queries.add(Query.of(q -> q.range(r -> r.field("rating").gte(dto.getMinRating().doubleValue()))));
        }

        BoolQuery.Builder boolBuilder = new BoolQuery.Builder().must(queries);

        NativeQuery.Builder queryBuilder = NativeQuery.builder()
                .withQuery(q -> q.bool(boolBuilder.build()));

        if ("geo_distance".equalsIgnoreCase(dto.getSortBy())
                && dto.getUserLatitude() != null && dto.getUserLongitude() != null) {
            SortOrder order = "desc".equalsIgnoreCase(dto.getSortOrder()) ? SortOrder.Desc : SortOrder.Asc;
            queryBuilder.withSort(s -> s.geoDistance(g -> g
                    .field("location")
                    .location(l -> l.latlon(latLon -> latLon
                            .lat(dto.getUserLatitude().doubleValue())
                            .lon(dto.getUserLongitude().doubleValue())))
                    .order(order)
                    .unit(co.elastic.clients.elasticsearch._types.DistanceUnit.Kilometers)
                    .distanceType(GeoDistanceType.Arc)));
        } else if (StringUtils.hasText(dto.getSortBy())) {
            SortOrder order = "desc".equalsIgnoreCase(dto.getSortOrder()) ? SortOrder.Desc : SortOrder.Asc;
            queryBuilder.withSort(s -> s.field(f -> f.field(dto.getSortBy()).order(order)));
        } else {
            queryBuilder.withSort(s -> s.score(sc -> sc.order(SortOrder.Desc)));
        }

        List<HighlightField> highlightFields = new ArrayList<>();
        highlightFields.add(new HighlightField("title"));
        highlightFields.add(new HighlightField("description"));
        Highlight highlight = new Highlight(HighlightParameters.builder().build(), highlightFields);
        queryBuilder.withHighlightQuery(new HighlightQuery(highlight, null));

        int pageNum = Math.max(dto.getPageNum() - 1, 0);
        queryBuilder.withPageable(PageRequest.of(pageNum, dto.getPageSize()));

        SearchHits<com.homestay.document.HouseDocument> searchHits =
                elasticsearchOperations.search(queryBuilder.build(), com.homestay.document.HouseDocument.class);

        List<Long> houseIds = searchHits.getSearchHits().stream()
                .map(hit -> hit.getContent().getId())
                .collect(Collectors.toList());

        Map<Long, BigDecimal> totalPriceMap = new HashMap<>();
        if (dto.getCheckInDate() != null && dto.getCheckOutDate() != null && !houseIds.isEmpty()) {
            for (Long houseId : houseIds) {
                List<HouseCalendar> calendars = houseService.getHouseCalendar(
                        houseId, dto.getCheckInDate(), dto.getCheckOutDate().minusDays(1));
                boolean available = calendars.size() == ChronoUnit.DAYS.between(dto.getCheckInDate(), dto.getCheckOutDate());
                if (available) {
                    available = calendars.stream().allMatch(c -> c.getStock() > 0 && c.getStatus() == 1);
                }
                if (available) {
                    BigDecimal total = calendars.stream()
                            .map(HouseCalendar::getPrice)
                            .reduce(BigDecimal.ZERO, BigDecimal::add);
                    totalPriceMap.put(houseId, total);
                }
            }
        }

        List<Map<String, Object>> resultList = new ArrayList<>();
        for (SearchHit<com.homestay.document.HouseDocument> hit : searchHits.getSearchHits()) {
            com.homestay.document.HouseDocument doc = hit.getContent();
            Map<String, Object> map = new HashMap<>();
            map.put("id", doc.getId());
            map.put("title", doc.getTitle());
            map.put("description", doc.getDescription());
            map.put("province", doc.getProvince());
            map.put("city", doc.getCity());
            map.put("district", doc.getDistrict());
            map.put("address", doc.getAddress());
            map.put("longitude", doc.getLocation() != null ? doc.getLocation().getLon() : null);
            map.put("latitude", doc.getLocation() != null ? doc.getLocation().getLat() : null);
            map.put("type", doc.getType());
            map.put("roomCount", doc.getRoomCount());
            map.put("bedCount", doc.getBedCount());
            map.put("bathCount", doc.getBathCount());
            map.put("maxGuests", doc.getMaxGuests());
            map.put("basePrice", doc.getBasePrice());
            map.put("coverImage", doc.getCoverImage());
            map.put("rating", doc.getRating());
            map.put("reviewCount", doc.getReviewCount());
            map.put("facilities", doc.getFacilities());
            if (totalPriceMap.containsKey(doc.getId())) {
                map.put("totalPrice", totalPriceMap.get(doc.getId()));
                map.put("available", true);
            } else if (dto.getCheckInDate() != null && dto.getCheckOutDate() != null) {
                map.put("available", false);
            }
            if (!CollectionUtils.isEmpty(hit.getSortValues())) {
                for (Object sortValue : hit.getSortValues()) {
                    if (sortValue instanceof Double) {
                        map.put("distance", sortValue);
                        break;
                    }
                }
            }
            if (!CollectionUtils.isEmpty(hit.getHighlightFields())) {
                if (hit.getHighlightField("title") != null && !hit.getHighlightField("title").isEmpty()) {
                    map.put("highlightTitle", hit.getHighlightField("title").get(0));
                }
                if (hit.getHighlightField("description") != null && !hit.getHighlightField("description").isEmpty()) {
                    map.put("highlightDescription", hit.getHighlightField("description").get(0));
                }
            }
            resultList.add(map);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("list", resultList);
        result.put("total", searchHits.getTotalHits());
        result.put("pageNum", dto.getPageNum());
        result.put("pageSize", dto.getPageSize());
        result.put("pages", (searchHits.getTotalHits() + dto.getPageSize() - 1) / dto.getPageSize());

        return result;
    }

    public List<HouseMapVO> getMapHouses(MapHouseDTO dto) {
        List<Query> queries = new ArrayList<>();
        queries.add(Query.of(q -> q.term(t -> t.field("status").value(1))));

        if (dto.getMinLat() != null && dto.getMaxLat() != null && dto.getMinLng() != null && dto.getMaxLng() != null) {
            List<GeoBounds> bounds = new ArrayList<>();
            bounds.add(new GeoBounds.Builder()
                    .topRight(tr -> tr.latlon(latLon -> latLon.lat(dto.getMaxLat().doubleValue()).lon(dto.getMaxLng().doubleValue())))
                    .bottomLeft(bl -> bl.latlon(latLon -> latLon.lat(dto.getMinLat().doubleValue()).lon(dto.getMinLng().doubleValue())))
                    .build());
            queries.add(Query.of(q -> q.geoBoundingBox(g -> g.field("location").bounds(bounds.get(0)))));
        }

        BoolQuery boolQuery = new BoolQuery.Builder().must(queries).build();

        NativeQuery query = NativeQuery.builder()
                .withQuery(q -> q.bool(boolQuery))
                .withMaxResults(200)
                .build();

        SearchHits<com.homestay.document.HouseDocument> searchHits =
                elasticsearchOperations.search(query, com.homestay.document.HouseDocument.class);

        return searchHits.getSearchHits().stream().map(hit -> {
            com.homestay.document.HouseDocument doc = hit.getContent();
            HouseMapVO vo = new HouseMapVO();
            vo.setId(doc.getId());
            vo.setTitle(doc.getTitle());
            if (doc.getLocation() != null) {
                vo.setLongitude(BigDecimal.valueOf(doc.getLocation().getLon()));
                vo.setLatitude(BigDecimal.valueOf(doc.getLocation().getLat()));
            }
            vo.setBasePrice(doc.getBasePrice());
            vo.setCoverImage(doc.getCoverImage());
            vo.setRating(doc.getRating());
            vo.setReviewCount(doc.getReviewCount());
            return vo;
        }).collect(Collectors.toList());
    }
}
