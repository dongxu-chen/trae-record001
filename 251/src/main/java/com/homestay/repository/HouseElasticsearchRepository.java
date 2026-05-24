package com.homestay.repository;

import com.homestay.document.HouseDocument;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface HouseElasticsearchRepository extends ElasticsearchRepository<HouseDocument, Long> {

    List<HouseDocument> findByCityAndStatus(String city, Integer status);
}
