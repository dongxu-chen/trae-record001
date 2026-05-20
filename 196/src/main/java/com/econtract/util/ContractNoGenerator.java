package com.econtract.util;

import cn.hutool.core.date.DateUtil;
import cn.hutool.core.util.RandomUtil;

import java.util.Date;

public class ContractNoGenerator {

    public static String generate() {
        String datePart = DateUtil.format(new Date(), "yyyyMMddHHmmss");
        String randomPart = RandomUtil.randomNumbers(6);
        return "HT" + datePart + randomPart;
    }

    public static String generateEvidenceNo() {
        String datePart = DateUtil.format(new Date(), "yyyyMMddHHmmss");
        String randomPart = RandomUtil.randomNumbers(8);
        return "CZ" + datePart + randomPart;
    }
}
