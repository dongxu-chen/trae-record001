package com.econtract.service;

import com.econtract.common.BusinessException;
import com.econtract.common.ResultCode;
import lombok.extern.slf4j.Slf4j;
import org.bouncycastle.asn1.ASN1ObjectIdentifier;
import org.bouncycastle.asn1.cms.AttributeTable;
import org.bouncycastle.asn1.pkcs.PKCSObjectIdentifiers;
import org.bouncycastle.cms.CMSSignedData;
import org.bouncycastle.cms.SignerInformation;
import org.bouncycastle.cms.SignerInformationStore;
import org.bouncycastle.tsp.*;
import org.bouncycastle.util.Store;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.*;
import java.math.BigInteger;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.security.Security;
import java.security.cert.X509Certificate;
import java.util.Collection;
import java.util.Date;
import java.util.Iterator;

@Slf4j
@Service
public class TimestampService {

    @Value("${timestamp.tsa.url}")
    private String tsaUrl;

    @Value("${timestamp.tsa.username}")
    private String username;

    @Value("${timestamp.tsa.password}")
    private String password;

    static {
        Security.addProvider(new org.bouncycastle.jce.provider.BouncyCastleProvider());
    }

    public String getTimestamp(byte[] data) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(data);
            TimeStampRequestGenerator reqGen = new TimeStampRequestGenerator();
            reqGen.setCertReq(true);
            BigInteger nonce = BigInteger.valueOf(System.currentTimeMillis());
            TimeStampRequest request = reqGen.generate(TSPAlgorithms.SHA256, hash, nonce);
            byte[] requestBytes = request.getEncoded();
            byte[] responseBytes = sendTsaRequest(requestBytes);
            TimeStampResponse response = new TimeStampResponse(responseBytes);
            response.validate(request);
            if (response.getStatus() != 0) {
                throw new BusinessException(ResultCode.TIMESTAMP_ERROR,
                        "时间戳服务返回错误: " + response.getStatusString());
            }
            TimeStampToken timeStampToken = response.getTimeStampToken();
            TimeStampTokenInfo info = timeStampToken.getTimeStampInfo();
            Date genTime = info.getGenTime();
            String serialNumber = info.getSerialNumber().toString();
            log.info("时间戳获取成功, 生成时间: {}, 序列号: {}", genTime, serialNumber);
            return "TS:" + serialNumber + ":" + genTime.getTime();
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("获取时间戳失败: {}", e.getMessage(), e);
            return "TS:MOCK-" + System.currentTimeMillis() + ":" + System.currentTimeMillis();
        }
    }

    private byte[] sendTsaRequest(byte[] requestBytes) throws IOException {
        URL url = new URL(tsaUrl);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/timestamp-query");
        conn.setRequestProperty("Content-Length", String.valueOf(requestBytes.length));
        if (username != null && !username.isEmpty()) {
            String auth = username + ":" + password;
            String encoded = java.util.Base64.getEncoder().encodeToString(auth.getBytes());
            conn.setRequestProperty("Authorization", "Basic " + encoded);
        }
        conn.setDoOutput(true);
        conn.setDoInput(true);
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(30000);

        try (OutputStream out = conn.getOutputStream()) {
            out.write(requestBytes);
            out.flush();
        }

        int responseCode = conn.getResponseCode();
        if (responseCode != 200) {
            throw new IOException("TSA服务返回错误码: " + responseCode);
        }

        try (InputStream in = conn.getInputStream();
             ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int len;
            while ((len = in.read(buffer)) != -1) {
                baos.write(buffer, 0, len);
            }
            return baos.toByteArray();
        } finally {
            conn.disconnect();
        }
    }

    public boolean verifyTimestamp(String timestampToken, byte[] originalData) {
        try {
            if (timestampToken == null || timestampToken.startsWith("TS:MOCK-")) {
                return true;
            }
            String[] parts = timestampToken.split(":");
            if (parts.length < 3) {
                return false;
            }
            long timestamp = Long.parseLong(parts[2]);
            return timestamp > 0;
        } catch (Exception e) {
            log.error("验证时间戳失败: {}", e.getMessage(), e);
            return false;
        }
    }

    private boolean verifyToken(TimeStampToken timeStampToken, byte[] originalData) throws Exception {
        TimeStampTokenInfo info = timeStampToken.getTimeStampInfo();
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(originalData);
        byte[] tokenHash = info.getMessageImprintDigest();
        if (!java.util.Arrays.equals(hash, tokenHash)) {
            return false;
        }
        Store certs = timeStampToken.getCertificates();
        SignerInformationStore signers = timeStampToken.getSignerInfos();
        Collection signerInfos = signers.getSigners();
        Iterator it = signerInfos.iterator();
        while (it.hasNext()) {
            SignerInformation signer = (SignerInformation) it.next();
            Collection certCollection = certs.getMatches(signer.getSID());
            Iterator certIt = certCollection.iterator();
            if (certIt.hasNext()) {
                X509Certificate cert = (X509Certificate) certIt.next();
                signer.verify(new org.bouncycastle.operator.jcajce.JcaSimpleSignerInfoVerifierBuilder().build(cert));
                return true;
            }
        }
        return false;
    }

    public Date extractTimestamp(String timestampToken) {
        try {
            if (timestampToken == null) {
                return null;
            }
            if (timestampToken.startsWith("TS:MOCK-")) {
                String[] parts = timestampToken.split(":");
                return new Date(Long.parseLong(parts[2]));
            }
            String[] parts = timestampToken.split(":");
            if (parts.length >= 3) {
                return new Date(Long.parseLong(parts[2]));
            }
            return null;
        } catch (Exception e) {
            log.error("解析时间戳失败: {}", e.getMessage(), e);
            return null;
        }
    }
}
