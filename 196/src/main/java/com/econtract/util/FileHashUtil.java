package com.econtract.util;

import cn.hutool.crypto.digest.DigestUtil;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;

public class FileHashUtil {

    public static String sha256(File file) {
        try (FileInputStream fis = new FileInputStream(file)) {
            return DigestUtil.sha256Hex(fis);
        } catch (IOException e) {
            throw new RuntimeException("计算文件哈希失败", e);
        }
    }

    public static String sha256(byte[] data) {
        return DigestUtil.sha256Hex(data);
    }

    public static String md5(File file) {
        try (FileInputStream fis = new FileInputStream(file)) {
            return DigestUtil.md5Hex(fis);
        } catch (IOException e) {
            throw new RuntimeException("计算文件哈希失败", e);
        }
    }

    public static String sha256Quietly(File file) {
        try {
            return sha256(file);
        } catch (Exception e) {
            return null;
        }
    }
}
