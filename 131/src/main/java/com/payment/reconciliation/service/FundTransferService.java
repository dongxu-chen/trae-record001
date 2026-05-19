package com.payment.reconciliation.service;

import com.payment.reconciliation.dto.FundTransferDTO;
import com.payment.reconciliation.entity.FundTransfer;

import java.util.List;

public interface FundTransferService {

    FundTransfer createFundTransfer(FundTransferDTO dto);

    List<FundTransfer> listFundTransfers(String channelCode, Integer status);

    FundTransfer getFundTransferById(Long id);
}
