package com.survey.service;

import com.google.zxing.BarcodeFormat;
import com.google.zxing.client.j2se.MatrixToImageWriter;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.qrcode.QRCodeWriter;
import com.survey.entity.Survey;
import com.survey.exception.BusinessException;
import com.survey.repository.SurveyRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.util.Base64;

@Service
@RequiredArgsConstructor
public class DistributionService {

    private final SurveyRepository surveyRepository;

    @Value("${survey.base-url}")
    private String baseUrl;

    @Value("${survey.qrcode.width}")
    private int qrCodeWidth;

    @Value("${survey.qrcode.height}")
    private int qrCodeHeight;

    public String getSurveyLink(String shareCode) {
        return baseUrl + "/survey/" + shareCode;
    }

    public String generateQRCode(String surveyId) {
        Survey survey = surveyRepository.findById(surveyId)
                .orElseThrow(() -> new BusinessException("问卷不存在"));

        if (survey.getShareCode() == null) {
            throw new BusinessException("问卷未发布");
        }

        String surveyUrl = getSurveyLink(survey.getShareCode());

        try {
            QRCodeWriter qrCodeWriter = new QRCodeWriter();
            BitMatrix bitMatrix = qrCodeWriter.encode(surveyUrl, BarcodeFormat.QR_CODE, qrCodeWidth, qrCodeHeight);

            ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
            MatrixToImageWriter.writeToStream(bitMatrix, "PNG", outputStream);

            byte[] qrCodeBytes = outputStream.toByteArray();
            return Base64.getEncoder().encodeToString(qrCodeBytes);
        } catch (Exception e) {
            throw new BusinessException("生成二维码失败: " + e.getMessage());
        }
    }
}
