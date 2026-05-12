package com.stock.chart;

import com.stock.model.CandleData;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.scene.canvas.Canvas;
import javafx.scene.canvas.GraphicsContext;
import javafx.scene.layout.Background;
import javafx.scene.layout.BackgroundFill;
import javafx.scene.layout.CornerRadii;
import javafx.scene.layout.Pane;
import javafx.scene.paint.Color;
import javafx.scene.text.Font;

import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

public class ChartView extends Pane {

    private final Canvas canvas;
    private List<CandleData> candleDataList;

    private final AtomicBoolean redrawPending = new AtomicBoolean(false);
    private static final double MIN_CHART_WIDTH = 200;
    private static final double MIN_CHART_HEIGHT = 150;

    public ChartView() {
        setBackground(new Background(new BackgroundFill(Color.WHITE, CornerRadii.EMPTY, Insets.EMPTY)));
        canvas = new Canvas();
        getChildren().add(canvas);

        widthProperty().addListener((obs, oldVal, newVal) -> {
            canvas.setWidth(newVal.doubleValue());
            scheduleRedraw();
        });

        heightProperty().addListener((obs, oldVal, newVal) -> {
            canvas.setHeight(newVal.doubleValue());
            scheduleRedraw();
        });
    }

    public void setCandleData(List<CandleData> candleDataList) {
        this.candleDataList = candleDataList;
        scheduleRedraw();
    }

    private void scheduleRedraw() {
        if (redrawPending.compareAndSet(false, true)) {
            Platform.runLater(() -> {
                redrawPending.set(false);
                draw();
            });
        }
    }

    private void draw() {
        double width = canvas.getWidth();
        double height = canvas.getHeight();

        if (width <= 0 || height <= 0 ||
            width < MIN_CHART_WIDTH || height < MIN_CHART_HEIGHT) {
            return;
        }

        GraphicsContext gc = canvas.getGraphicsContext2D();
        gc.clearRect(0, 0, width, height);

        if (candleDataList == null || candleDataList.isEmpty()) {
            gc.setFill(Color.LIGHTGRAY);
            gc.setFont(Font.font(16));
            double textX = Math.max(5, width / 2 - 50);
            double textY = Math.max(20, height / 2);
            gc.fillText("暂无K线数据", textX, textY);
            return;
        }

        double topMargin = 40;
        double bottomMargin = 50;
        double leftMargin = 65;
        double rightMargin = 20;
        double chartWidth = width - leftMargin - rightMargin;
        double chartHeight = height - topMargin - bottomMargin;

        if (chartWidth <= 50 || chartHeight <= 50) {
            gc.setFill(Color.LIGHTGRAY);
            gc.setFont(Font.font(12));
            gc.fillText("区域过小", width / 2 - 30, height / 2);
            return;
        }

        double minPrice = Double.MAX_VALUE;
        double maxPrice = Double.MIN_VALUE;

        for (CandleData candle : candleDataList) {
            minPrice = Math.min(minPrice, candle.getLow());
            maxPrice = Math.max(maxPrice, candle.getHigh());
        }

        double priceRange = maxPrice - minPrice;
        if (priceRange <= 0) {
            priceRange = Math.max(0.01, minPrice * 0.01);
            maxPrice = minPrice + priceRange;
        }

        int count = candleDataList.size();
        double candleWidth = Math.max(2, (chartWidth / count) * 0.7);
        double candleGap = (chartWidth / count) * 0.3;

        drawGrid(gc, leftMargin, topMargin, chartWidth, chartHeight);
        drawPriceLabels(gc, minPrice, maxPrice, leftMargin, topMargin, chartHeight);

        for (int i = 0; i < count; i++) {
            CandleData candle = candleDataList.get(i);
            double x = leftMargin + i * (candleWidth + candleGap);
            if (x + candleWidth < leftMargin || x > leftMargin + chartWidth) {
                continue;
            }
            drawCandle(gc, candle, x, candleWidth, topMargin, chartHeight, minPrice, maxPrice);
        }

        drawXAxisLabels(gc, candleDataList, leftMargin, chartWidth, topMargin + chartHeight);
    }

    private void drawGrid(GraphicsContext gc, double x, double y, double width, double height) {
        gc.setStroke(Color.LIGHTGRAY);
        gc.setLineWidth(0.5);

        int gridLines = 5;
        for (int i = 0; i <= gridLines; i++) {
            double gridY = y + (height / gridLines) * i;
            if (gridY >= y && gridY <= y + height) {
                gc.strokeLine(x, gridY, x + width, gridY);
            }
        }
    }

    private void drawPriceLabels(GraphicsContext gc, double min, double max,
                                  double x, double y, double height) {
        gc.setFill(Color.DARKGRAY);
        gc.setFont(Font.font(11));

        int labels = 5;
        for (int i = 0; i <= labels; i++) {
            double ratio = 1.0 - (double) i / labels;
            double price = min + (max - min) * ratio;
            double labelY = y + (height / labels) * i;

            if (Double.isNaN(price) || Double.isInfinite(price)) {
                continue;
            }

            String text;
            if (Math.abs(price) >= 10000) {
                text = String.format("%.0f", price);
            } else {
                text = String.format("%.2f", price);
            }

            gc.fillText(text, 5, labelY + 4);
        }
    }

    private void drawCandle(GraphicsContext gc, CandleData candle, double x, double width,
                            double chartTop, double chartHeight, double min, double max) {
        double priceRange = max - min;
        if (priceRange <= 0) {
            return;
        }

        double openY = chartTop + chartHeight * (1.0 - (candle.getOpen() - min) / priceRange);
        double closeY = chartTop + chartHeight * (1.0 - (candle.getClose() - min) / priceRange);
        double highY = chartTop + chartHeight * (1.0 - (candle.getHigh() - min) / priceRange);
        double lowY = chartTop + chartHeight * (1.0 - (candle.getLow() - min) / priceRange);

        double chartBottom = chartTop + chartHeight;
        openY = clamp(openY, chartTop, chartBottom);
        closeY = clamp(closeY, chartTop, chartBottom);
        highY = clamp(highY, chartTop, chartBottom);
        lowY = clamp(lowY, chartTop, chartBottom);

        Color color = candle.isUp() ? Color.RED : Color.GREEN;

        gc.setStroke(color);
        gc.setLineWidth(1);
        gc.strokeLine(x + width / 2, highY, x + width / 2, lowY);

        gc.setFill(color);
        double bodyTop = Math.min(openY, closeY);
        double bodyHeight = Math.max(Math.abs(closeY - openY), 1);
        gc.fillRect(x, bodyTop, width, bodyHeight);
    }

    private void drawXAxisLabels(GraphicsContext gc, List<CandleData> data,
                                  double left, double width, double y) {
        gc.setFill(Color.DARKGRAY);
        gc.setFont(Font.font(10));

        int count = data.size();
        int step = Math.max(1, count / 5);

        for (int i = 0; i < count; i += step) {
            double labelX = left + (width / count) * (i + 0.5);
            String date = data.get(i).getDate();
            if (labelX >= left && labelX <= left + width) {
                gc.fillText(date, labelX - 25, y + 15);
            }
        }
    }

    private double clamp(double value, double min, double max) {
        if (value < min) return min;
        if (value > max) return max;
        if (Double.isNaN(value)) return (min + max) / 2;
        return value;
    }
}
