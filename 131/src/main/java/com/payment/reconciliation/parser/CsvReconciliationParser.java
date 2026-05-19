package com.payment.reconciliation.parser;

import cn.hutool.core.date.DateUtil;
import cn.hutool.core.util.StrUtil;
import com.payment.reconciliation.entity.ChannelTransaction;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Component
public class CsvReconciliationParser implements ReconciliationParser {

    @Override
    public List<ChannelTransaction> parse(InputStream inputStream, String channelCode) throws Exception {
        List<ChannelTransaction> resultList = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8))) {
            String line;
            int lineNum = 0;
            while ((line = reader.readLine()) != null) {
                lineNum++;
                if (lineNum == 1) {
                    continue;
                }
                if (StrUtil.isBlank(line)) {
                    continue;
                }
                try {
                    String[] parts = line.split(",");
                    ChannelTransaction transaction = parseLine(parts, channelCode);
                    if (transaction != null) {
                        resultList.add(transaction);
                    }
                } catch (Exception e) {
                    log.error("解析CSV行失败, 行号: {}, 数据: {}", lineNum, line, e);
                }
            }
        }

        log.info("CSV解析完成, 共解析 {} 条记录", resultList.size());
        return resultList;
    }

    private ChannelTransaction parseLine(String[] parts, String channelCode) {
        if (parts.length < 7) {
            return null;
        }
        ChannelTransaction transaction = new ChannelTransaction();
        transaction.setChannelCode(channelCode);
        transaction.setChannelTransNo(parts[0].trim());
        transaction.setMerchantNo(parts[1].trim());
        transaction.setOrderNo(parts[2].trim());
        transaction.setAmount(new BigDecimal(parts[3].trim()));
        transaction.setFee(new BigDecimal(parts[4].trim()));
        transaction.setStatus(Integer.parseInt(parts[5].trim()));
        transaction.setTransTime(LocalDateTime.ofInstant(
                DateUtil.parse(parts[6].trim()).toInstant(),
                ZoneId.systemDefault()
        ));
        transaction.setMatched(0);
        return transaction;
    }

    @Override
    public boolean support(String fileType) {
        return "csv".equalsIgnoreCase(fileType);
    }
}
