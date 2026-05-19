package com.payment.reconciliation.parser;

import com.payment.reconciliation.entity.ChannelTransaction;

import java.io.InputStream;
import java.util.List;

public interface ReconciliationParser {

    List<ChannelTransaction> parse(InputStream inputStream, String channelCode) throws Exception;

    boolean support(String fileType);
}
