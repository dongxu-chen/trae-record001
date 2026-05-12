package com.stock.service;

import com.stock.model.CandleData;
import com.stock.model.Stock;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.SocketTimeoutException;
import java.net.URL;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.*;

public class StockDataFetcher {

    private static final String TENCENT_STOCK_API = "http://qt.gtimg.cn/q=";
    private static final String TENCENT_KLINE_API = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get";
    private static final int TOTAL_TIMEOUT_MS = 8000;

    private final Random random = new Random();
    private final ExecutorService executor = Executors.newFixedThreadPool(2, r -> {
        Thread t = new Thread(r, "stock-fetcher");
        t.setDaemon(true);
        return t;
    });

    public Stock fetchStockData(String code) {
        FutureTask<Stock> task = new FutureTask<>(() -> fetchStockDataInternal(code));
        executor.execute(task);

        try {
            return task.get(TOTAL_TIMEOUT_MS, TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            System.err.println("获取股票数据超时: " + code);
            task.cancel(true);
            return generateMockStock(code);
        } catch (InterruptedException | ExecutionException e) {
            System.err.println("获取股票数据异常: " + code + ", " + e.getMessage());
            return generateMockStock(code);
        }
    }

    private Stock fetchStockDataInternal(String code) throws IOException {
        HttpURLConnection conn = null;
        try {
            String marketPrefix = code.startsWith("6") ? "sh" : "sz";
            String fullCode = marketPrefix + code;
            String urlString = TENCENT_STOCK_API + fullCode;

            URL url = new URL(urlString);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(3000);
            conn.setReadTimeout(3000);
            conn.setRequestProperty("User-Agent", "Mozilla/5.0");
            conn.setInstanceFollowRedirects(true);

            int responseCode = conn.getResponseCode();
            if (responseCode != 200) {
                return generateMockStock(code);
            }

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream(), "GBK"))) {
                String line = reader.readLine();

                if (line != null && line.length() > 0) {
                    String[] parts = line.split("~");
                    if (parts.length >= 33) {
                        Stock stock = new Stock();
                        stock.setCode(code);
                        stock.setName(parts[1]);
                        stock.setOpen(parseDouble(parts[5]));
                        stock.setClose(parseDouble(parts[4]));
                        stock.setHigh(parseDouble(parts[33]));
                        stock.setLow(parseDouble(parts[34]));
                        stock.setPrice(parseDouble(parts[3]));
                        stock.setChange(parseDouble(parts[31]));
                        stock.setChangePercent(parseDouble(parts[32]));
                        stock.setVolume(parseLong(parts[6]));
                        return stock;
                    }
                }
            }
        } catch (SocketTimeoutException | UnknownHostException e) {
            System.err.println("网络异常: " + e.getMessage());
            return generateMockStock(code);
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
        return generateMockStock(code);
    }

    public List<CandleData> fetchKLineData(String code, int days) {
        List<CandleData> candleList = new ArrayList<>();
        double basePrice = 100.0 + random.nextDouble() * 50;
        double currentPrice = basePrice;

        for (int i = 0; i < days; i++) {
            double open = currentPrice;
            double change = (random.nextDouble() - 0.48) * 5;
            double close = open + change;
            double high = Math.max(open, close) + random.nextDouble() * 2;
            double low = Math.min(open, close) - random.nextDouble() * 2;
            long volume = (long) (random.nextDouble() * 10000000);

            int month = (i % 12) + 1;
            int day = (i % 28) + 1;
            String dateStr = String.format("2024-%02d-%02d", month, day);

            CandleData candle = new CandleData(open, close, high, low, volume, dateStr);
            candleList.add(candle);
            currentPrice = close;
        }

        return candleList;
    }

    private double parseDouble(String value) {
        if (value == null || value.isEmpty()) {
            return 0.0;
        }
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }

    private long parseLong(String value) {
        if (value == null || value.isEmpty()) {
            return 0L;
        }
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    private Stock generateMockStock(String code) {
        Stock stock = new Stock();
        stock.setCode(code);
        stock.setName("股票" + code);
        double basePrice = 50 + random.nextDouble() * 100;
        double change = (random.nextDouble() - 0.5) * 5;
        double price = basePrice + change;
        stock.setPrice(price);
        stock.setChange(change);
        stock.setChangePercent((change / basePrice) * 100);
        stock.setOpen(basePrice);
        stock.setHigh(price + random.nextDouble() * 2);
        stock.setLow(price - random.nextDouble() * 2);
        stock.setClose(basePrice);
        stock.setVolume((long) (random.nextDouble() * 10000000));
        return stock;
    }

    public List<String> getDefaultStockCodes() {
        List<String> codes = new ArrayList<>();
        codes.add("600519");
        codes.add("000001");
        codes.add("000858");
        codes.add("601318");
        codes.add("600036");
        return codes;
    }

    public void shutdown() {
        executor.shutdownNow();
    }
}
