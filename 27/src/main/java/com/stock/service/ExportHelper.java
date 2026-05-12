package com.stock.service;

import com.stock.model.CandleData;
import com.stock.model.Stock;
import com.stock.model.WatchlistGroup;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

public class ExportHelper {

    private static final DateTimeFormatter TIMESTAMP_FORMAT = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");

    public enum ExportFormat {
        CSV,
        EXCEL_XLSX
    }

    public static String exportStocksToCSV(List<Stock> stocks, File file) throws IOException {
        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(new FileOutputStream(file), StandardCharsets.UTF_8))) {

            writer.write('\ufeff');

            writer.write("股票代码,股票名称,当前价格,涨跌额,涨跌幅(%),开盘价,最高价,最低价,成交量");
            writer.newLine();

            for (Stock stock : stocks) {
                String line = String.format("%s,%s,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%d",
                        stock.getCode(),
                        escapeCsv(stock.getName()),
                        stock.getPrice(),
                        stock.getChange(),
                        stock.getChangePercent(),
                        stock.getOpen(),
                        stock.getHigh(),
                        stock.getLow(),
                        stock.getVolume());
                writer.write(line);
                writer.newLine();
            }
        }
        return file.getAbsolutePath();
    }

    public static String exportStocksToCSV(List<Stock> stocks, String directory) throws IOException {
        String filename = "stock_data_" + LocalDateTime.now().format(TIMESTAMP_FORMAT) + ".csv";
        File file = new File(directory, filename);
        return exportStocksToCSV(stocks, file);
    }

    public static String exportKLineToCSV(List<CandleData> candles, String stockCode, String stockName, File file) throws IOException {
        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(new FileOutputStream(file), StandardCharsets.UTF_8))) {

            writer.write('\ufeff');

            writer.write("股票代码:" + stockCode + ",股票名称:" + escapeCsv(stockName));
            writer.newLine();
            writer.write("日期,开盘价,收盘价,最高价,最低价,成交量");
            writer.newLine();

            for (CandleData candle : candles) {
                String line = String.format("%s,%.2f,%.2f,%.2f,%.2f,%d",
                        candle.getDate(),
                        candle.getOpen(),
                        candle.getClose(),
                        candle.getHigh(),
                        candle.getLow(),
                        candle.getVolume());
                writer.write(line);
                writer.newLine();
            }
        }
        return file.getAbsolutePath();
    }

    public static String exportWatchlistToCSV(List<WatchlistGroup> groups, File file) throws IOException {
        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(new FileOutputStream(file), StandardCharsets.UTF_8))) {

            writer.write('\ufeff');

            writer.write("分组ID,分组名称,分组股票数量,股票代码列表");
            writer.newLine();

            for (WatchlistGroup group : groups) {
                String codes = String.join(";", group.getStockCodes());
                String line = String.format("%s,%s,%d,%s",
                        group.getId(),
                        escapeCsv(group.getName()),
                        group.getStockCount(),
                        codes);
                writer.write(line);
                writer.newLine();
            }
        }
        return file.getAbsolutePath();
    }

    public static String exportStocksToExcel(List<Stock> stocks, File file) throws IOException {
        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
        sb.append("<?mso-application progid=\"Excel.Sheet\"?>\n");
        sb.append("<Workbook xmlns=\"urn:schemas-microsoft-com:office:spreadsheet\"\n");
        sb.append("    xmlns:o=\"urn:schemas-microsoft-com:office:office\"\n");
        sb.append("    xmlns:x=\"urn:schemas-microsoft-com:office:excel\"\n");
        sb.append("    xmlns:ss=\"urn:schemas-microsoft-com:office:spreadsheet\">\n");
        sb.append("  <Worksheet ss:Name=\"StockData\">\n");
        sb.append("    <Table>\n");

        sb.append("      <Row>\n");
        sb.append("        <Cell><Data ss:Type=\"String\">股票代码</Data></Cell>\n");
        sb.append("        <Cell><Data ss:Type=\"String\">股票名称</Data></Cell>\n");
        sb.append("        <Cell><Data ss:Type=\"String\">当前价格</Data></Cell>\n");
        sb.append("        <Cell><Data ss:Type=\"String\">涨跌额</Data></Cell>\n");
        sb.append("        <Cell><Data ss:Type=\"String\">涨跌幅(%)</Data></Cell>\n");
        sb.append("        <Cell><Data ss:Type=\"String\">开盘价</Data></Cell>\n");
        sb.append("        <Cell><Data ss:Type=\"String\">最高价</Data></Cell>\n");
        sb.append("        <Cell><Data ss:Type=\"String\">最低价</Data></Cell>\n");
        sb.append("        <Cell><Data ss:Type=\"String\">成交量</Data></Cell>\n");
        sb.append("      </Row>\n");

        for (Stock stock : stocks) {
            sb.append("      <Row>\n");
            sb.append("        <Cell><Data ss:Type=\"String\">").append(stock.getCode()).append("</Data></Cell>\n");
            sb.append("        <Cell><Data ss:Type=\"String\">").append(escapeXml(stock.getName())).append("</Data></Cell>\n");
            sb.append("        <Cell><Data ss:Type=\"Number\">").append(stock.getPrice()).append("</Data></Cell>\n");
            sb.append("        <Cell><Data ss:Type=\"Number\">").append(stock.getChange()).append("</Data></Cell>\n");
            sb.append("        <Cell><Data ss:Type=\"Number\">").append(stock.getChangePercent()).append("</Data></Cell>\n");
            sb.append("        <Cell><Data ss:Type=\"Number\">").append(stock.getOpen()).append("</Data></Cell>\n");
            sb.append("        <Cell><Data ss:Type=\"Number\">").append(stock.getHigh()).append("</Data></Cell>\n");
            sb.append("        <Cell><Data ss:Type=\"Number\">").append(stock.getLow()).append("</Data></Cell>\n");
            sb.append("        <Cell><Data ss:Type=\"Number\">").append(stock.getVolume()).append("</Data></Cell>\n");
            sb.append("      </Row>\n");
        }

        sb.append("    </Table>\n");
        sb.append("  </Worksheet>\n");
        sb.append("</Workbook>\n");

        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(new FileOutputStream(file), StandardCharsets.UTF_8))) {
            writer.write(sb.toString());
        }

        return file.getAbsolutePath();
    }

    public static String exportStocksToExcel(List<Stock> stocks, String directory) throws IOException {
        String filename = "stock_data_" + LocalDateTime.now().format(TIMESTAMP_FORMAT) + ".xml";
        File file = new File(directory, filename);
        return exportStocksToExcel(stocks, file);
    }

    private static String escapeCsv(String value) {
        if (value == null) {
            return "";
        }
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    private static String escapeXml(String value) {
        if (value == null) {
            return "";
        }
        return value.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\"", "&quot;");
    }
}
