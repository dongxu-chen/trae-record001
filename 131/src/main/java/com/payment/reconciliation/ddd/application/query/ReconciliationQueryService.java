package com.payment.reconciliation.ddd.application.query;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.elasticsearch.core.ElasticsearchRestTemplate;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ReconciliationQueryService {

    @Autowired
    private ElasticsearchRestTemplate elasticsearchTemplate;

    public ReconciliationDoc getByReconciliationNo(String reconciliationNo) {
        return elasticsearchTemplate.get(reconciliationNo, ReconciliationDoc.class);
    }

    public List<ReconciliationDoc> search(String channelCode, String startDate, String endDate) {
        return null;
    }

    public ReconciliationSummary getSummary(String channelCode, String date) {
        return null;
    }
}
