package com.stock.controller;

import com.stock.chart.ChartView;
import com.stock.model.*;
import com.stock.service.*;
import com.stock.view.SettingsPane;
import javafx.application.Platform;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.fxml.FXML;
import javafx.scene.control.*;
import javafx.scene.layout.Pane;
import javafx.stage.DirectoryChooser;
import javafx.stage.FileChooser;
import javafx.stage.Modality;

import java.io.File;
import java.io.IOException;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

public class MainController {

    @FXML
    private TextField codeInput;
    @FXML
    private ComboBox<String> intervalCombo;
    @FXML
    private Button startButton;
    @FXML
    private Button wsButton;
    @FXML
    private Button alertButton;
    @FXML
    private ComboBox<String> klineDaysCombo;
    @FXML
    private TableView<Stock> stockTable;
    @FXML
    private TreeView<TreeItemWrapper> watchlistTree;
    @FXML
    private Label groupLabel;
    @FXML
    private Label selectedStockLabel;
    @FXML
    private Label statusLabel;
    @FXML
    private Label wsStatusLabel;
    @FXML
    private Label clockLabel;
    @FXML
    private Pane chartPane;

    private final StockDataFetcher dataFetcher = new StockDataFetcher();
    private final AlertManager alertManager = new AlertManager();
    private final WebSocketStockService wsService = new WebSocketStockService();
    private final AppSettings settings = new AppSettings();

    private final ObservableList<Stock> stockList = FXCollections.observableArrayList();
    private final ObservableList<WatchlistGroup> groups = FXCollections.observableArrayList();

    private ScheduledExecutorService scheduler;
    private ScheduledFuture<?> refreshTask;
    private ScheduledFuture<?> clockTask;
    private boolean isRefreshing = false;

    private ChartView chartView;
    private final Map<String, Stock> stockMap = new HashMap<>();
    private WatchlistGroup currentFilterGroup = null;
    private final WatchlistGroup ALL_GROUP = new WatchlistGroup("全部分组", new ArrayList<>());

    @FXML
    public void initialize() {
        setupTable();
        setupTreeView();
        setupChart();
        setupWebSocketListener();
        setupAlertListener();
        initDefaultGroups();
        loadDefaultStocks();
        startClock();
    }

    private void setupTable() {
        stockTable.setItems(stockList);
        stockTable.getSelectionModel().setSelectionMode(SelectionMode.SINGLE);

        setupPriceColumns();

        stockTable.getSelectionModel().selectedItemProperty().addListener((obs, old, newSelection) -> {
            if (newSelection != null) {
                selectedStockLabel.setText(newSelection.getName() + " (" + newSelection.getCode() + ")");
                updateKLineChart(newSelection);
            } else {
                selectedStockLabel.setText("未选择股票");
                chartView.setCandleData(Collections.emptyList());
            }
        };
    }

    private void setupPriceColumns() {
        TableColumn<Stock, ?> codeCol = stockTable.getColumns().get(0);
        codeCol.setSortable(true);

        TableColumn<Stock, ?> nameCol = stockTable.getColumns().get(1);
        nameCol.setSortable(true);

        TableColumn<Stock, Double> priceCol = (TableColumn<Stock, Double>) stockTable.getColumns().get(2);
        priceCol.setCellFactory(col -> createPriceCell());

        TableColumn<Stock, Double> changeCol = (TableColumn<Stock, Double>) stockTable.getColumns().get(3);
        changeCol.setCellFactory(col -> createChangeCell());

        TableColumn<Stock, Double> changePercentCol = (TableColumn<Stock, Double>) stockTable.getColumns().get(4);
        changePercentCol.setCellFactory(col -> createChangePercentCell());

        TableColumn<Stock, Double> openCol = (TableColumn<Stock, Double>) stockTable.getColumns().get(5);
        openCol.setCellFactory(col -> createSimplePriceCell());

        TableColumn<Stock, Double> highCol = (TableColumn<Stock, Double>) stockTable.getColumns().get(6);
        highCol.setCellFactory(col -> createSimplePriceCell());

        TableColumn<Stock, Double> lowCol = (TableColumn<Stock, Double>) stockTable.getColumns().get(7);
        lowCol.setCellFactory(col -> createSimplePriceCell());
    }

    private TableCell<Stock, Double> createPriceCell() {
        return new TableCell<Stock, Double>() {
            @Override
            protected void updateItem(Double item, boolean empty) {
                super.updateItem(item, empty);
                if (empty || item == null) {
                    setText(null);
                } else {
                    setText(String.format("%.2f", item));
                }
            }
        };
    }

    private TableCell<Stock, Double> createChangeCell() {
        return new TableCell<Stock, Double>() {
            @Override
            protected void updateItem(Double item, boolean empty) {
                super.updateItem(item, empty);
                if (empty || item == null) {
                    setText(null);
                    setStyle("");
                } else {
                    setText(String.format("%.2f", item));
                    setStyle(item >= 0 ? "-fx-text-fill: red; -fx-font-weight: bold;" : "-fx-text-fill: green; -fx-font-weight: bold;");
                }
            }
        };
    }

    private TableCell<Stock, Double> createChangePercentCell() {
        return new TableCell<Stock, Double>() {
            @Override
            protected void updateItem(Double item, boolean empty) {
                super.updateItem(item, empty);
                if (empty || item == null) {
                    setText(null);
                    setStyle("");
                } else {
                    String prefix = item >= 0 ? "+" : "";
                    setText(prefix + String.format("%.2f%%", item));
                    setStyle(item >= 0 ? "-fx-text-fill: red; -fx-font-weight: bold;" : "-fx-text-fill: green; -fx-font-weight: bold;");
                }
            }
        };
    }

    private TableCell<Stock, Double> createSimplePriceCell() {
        return new TableCell<Stock, Double>() {
            @Override
            protected void updateItem(Double item, boolean empty) {
                super.updateItem(item, empty);
                if (empty || item == null) {
                    setText(null);
                } else {
                    setText(String.format("%.2f", item));
                }
            }
        };
    }

    private void setupTreeView() {
        TreeItem<TreeItemWrapper> root = new TreeItem<>(new TreeItemWrapper(ALL_GROUP));
        watchlistTree.setRoot(root);
        watchlistTree.setShowRoot(true);

        watchlistTree.getSelectionModel().selectedItemProperty().addListener((obs, old, selected) -> {
            if (selected != null && selected.getValue() != null) {
                handleTreeSelection(selected);
            }
        });
    }

    private void handleTreeSelection(TreeItem<TreeItemWrapper> selected) {
        TreeItemWrapper wrapper = selected.getValue();
        if (wrapper.isGroup()) {
            filterStocksByGroup(wrapper.getGroup());
        } else if (wrapper.isStock()) {
            Stock s = wrapper.getStock();
            stockTable.getSelectionModel().select(s);
            stockTable.scrollTo(s);
        }
    }

    private void filterStocksByGroup(WatchlistGroup group) {
        currentFilterGroup = group;
        groupLabel.setText("(" + group.getName() + ")");

        if (group == ALL_GROUP) {
            stockTable.setItems(stockList);
        } else {
            List<Stock> filtered = stockList.stream()
                    .filter(s -> group.containsStock(s.getCode()))
                    .collect(Collectors.toList());
            stockTable.setItems(FXCollections.observableArrayList(filtered));
        }
    }

    private void setupChart() {
        chartView = new ChartView();
        chartView.prefWidthProperty().bind(chartPane.widthProperty());
        chartView.prefHeightProperty().bind(chartPane.heightProperty());
        chartPane.getChildren().add(chartView);

        klineDaysCombo.valueProperty().addListener((obs, oldVal, newVal) -> {
            Stock selected = stockTable.getSelectionModel().getSelectedItem();
            if (selected != null) {
                updateKLineChart(selected);
            }
        });
    }

    private void updateKLineChart(Stock stock) {
        int days = Integer.parseInt(klineDaysCombo.getValue());
        new Thread(() -> {
            var candleData = dataFetcher.fetchKLineData(stock.getCode(), days);
            Platform.runLater(() -> {
                chartView.setCandleData(candleData);
                statusLabel.setText("K线数据已加载: " + stock.getCode());
            });
        }).start();
    }

    private void initDefaultGroups() {
        WatchlistGroup defaultGroup = new WatchlistGroup("默认分组");
        WatchlistGroup techGroup = new WatchlistGroup("科技股");
        WatchlistGroup financeGroup = new WatchlistGroup("金融股");
        groups.addAll(defaultGroup, techGroup, financeGroup);
        refreshTreeView();
    }

    private void refreshTreeView() {
        TreeItem<TreeItemWrapper> root = watchlistTree.getRoot();
        if (root == null) {
            root = new TreeItem<>(new TreeItemWrapper(ALL_GROUP));
            watchlistTree.setRoot(root);
        }
        root.getChildren().clear();

        for (WatchlistGroup group : groups) {
            TreeItem<TreeItemWrapper> groupItem = new TreeItem<>(new TreeItemWrapper(group));
            groupItem.setExpanded(true);

            for (String code : group.getStockCodes()) {
                Stock stock = stockMap.get(code);
                if (stock != null) {
                    TreeItem<TreeItemWrapper> stockItem = new TreeItem<>(new TreeItemWrapper(stock));
                    groupItem.getChildren().add(stockItem);
                }
            }

            root.getChildren().add(groupItem);
        }
    }

    private void loadDefaultStocks() {
        WatchlistGroup defaultGroup = groups.isEmpty() ? new WatchlistGroup("默认分组") : groups.get(0);
        List<String> defaultCodes = dataFetcher.getDefaultStockCodes();
        for (String code : defaultCodes) {
            addStockToGroup(code, defaultGroup);
        }
        refreshAll();
    }

    private void addStockToGroup(String code, WatchlistGroup group) {
        new Thread(() -> {
            Stock stock = dataFetcher.fetchStockData(code);
            if (stock != null) {
                Platform.runLater(() -> {
                    if (stockMap.containsKey(code)) {
                        group.addStock(code);
                        refreshTreeView();
                        statusLabel.setText("已添加到分组: " + stock.getName());
                    } else {
                        stockMap.put(code, stock);
                        stockList.add(stock);
                        group.addStock(code);
                        refreshTreeView();
                        statusLabel.setText("已添加: " + stock.getName() + " (" + code + ")");
                    }
                });
            }
        }).start();
    }

    @FXML
    private void addStock() {
        String code = codeInput.getText().trim();
        if (code.isEmpty()) {
            showAlert("请输入股票代码", Alert.AlertType.WARNING);
            return;
        } else if (!code.matches("\\d{6}")) {
            showAlert("股票代码必须是6位数字", Alert.AlertType.WARNING);
            return;
        } else {
            TreeItem<TreeItemWrapper> selected = watchlistTree.getSelectionModel().getSelectedItem();
            WatchlistGroup targetGroup = ALL_GROUP;
            if (selected != null && selected.getValue() != null) {
                TreeItemWrapper wrapper = selected.getValue();
                if (wrapper.isGroup()) {
                    targetGroup = wrapper.getGroup();
                } else if (wrapper.isStock() && selected.getParent() != null) {
                    TreeItemWrapper parentWrapper = selected.getParent().getValue();
                    if (parentWrapper != null && parentWrapper.isGroup()) {
                        targetGroup = parentWrapper.getGroup();
                    }
                }
            }
            if (targetGroup == ALL_GROUP && !groups.isEmpty()) {
                targetGroup = groups.get(0);
            }
            if (targetGroup.containsStock(code) || stockMap.containsKey(code)) {
                showAlert("该股票已存在", Alert.AlertType.WARNING);
                return;
            }
            addStockToGroup(code, targetGroup);
            codeInput.clear();
        }
    }

    @FXML
    private void deleteSelected() {
        Stock selected = stockTable.getSelectionModel().getSelectedItem();
        if (selected == null) {
            showAlert("请先选择要删除的股票", Alert.AlertType.WARNING);
            return;
        }
        String code = selected.getCode();
        for (WatchlistGroup group : groups) {
            group.removeStock(code);
        }
        stockMap.remove(code);
        stockList.remove(selected);
        refreshTreeView();
        filterStocksByGroup(currentFilterGroup == null ? ALL_GROUP : currentFilterGroup);
        statusLabel.setText("已删除: " + selected.getName());
    }

    @FXML
    private void deleteSelectedFromTree() {
        TreeItem<TreeItemWrapper> selected = watchlistTree.getSelectionModel().getSelectedItem();
        if (selected == null || selected.getValue() == null) {
            return;
        }
        TreeItemWrapper wrapper = selected.getValue();
        if (wrapper.isStock()) {
            String code = wrapper.getStock().getCode();
            for (WatchlistGroup g : groups) {
                g.removeStock(code);
            }
            stockMap.remove(code);
            stockList.removeIf(s -> s.getCode().equals(code));
            refreshTreeView();
            statusLabel.setText("已删除");
        } else if (wrapper.isGroup() && wrapper.getGroup() != ALL_GROUP) {
            if (groups.remove(wrapper.getGroup()));
            refreshTreeView();
            statusLabel.setText("已删除分组: " + wrapper.getGroup().getName());
        }
    }

    @FXML
    private void createNewGroup() {
        TextInputDialog dialog = new TextInputDialog();
        dialog.setTitle("新建分组");
        dialog.setHeaderText("请输入分组名称");
        dialog.setContentText("名称:");

        Optional<String> result = dialog.showAndWait();
        result.ifPresent(name -> {
            if (!name.trim().isEmpty()) {
                showAlert("分组名称不能为空", Alert.AlertType.WARNING);
            } else {
                WatchlistGroup newGroup = new WatchlistGroup(name.trim());
                groups.add(newGroup);
                refreshTreeView();
                statusLabel.setText("已创建分组: " + name);
            }
        });
    }

    @FXML
    private void renameGroup() {
        renameSelected();
    }

    @FXML
    private void renameSelected() {
        TreeItem<TreeItemWrapper> selected = watchlistTree.getSelectionModel().getSelectedItem();
        if (selected == null || selected.getValue() == null) {
            return;
        }
        TreeItemWrapper wrapper = selected.getValue();
        if (!wrapper.isGroup() || wrapper.getGroup() == ALL_GROUP) {
            showAlert("请选择一个分组进行重命名", Alert.AlertType.WARNING);
            return;
        }
        WatchlistGroup group = wrapper.getGroup();
        TextInputDialog dialog = new TextInputDialog(group.getName());
        dialog.setTitle("重命名分组");
        dialog.setHeaderText("请输入新名称");
        dialog.setContentText("名称:");
        Optional<String> result = dialog.showAndWait();
        result.ifPresent(name -> {
            if (!name.trim().isEmpty()) {
                showAlert("分组名称不能为空", Alert.AlertType.WARNING);
            } else {
                group.setName(name.trim());
                refreshTreeView();
                statusLabel.setText("已重命名为: " + name);
            }
        });
    }

    @FXML
    private void toggleRefresh() {
        if (isRefreshing) {
            stopRefresh();
        } else {
            startRefresh();
        }
    }

    private void startRefresh() {
        try {
            int interval = Integer.parseInt(intervalCombo.getValue());
            if (scheduler == null || scheduler.isShutdown()) {
                scheduler = Executors.newScheduledThreadPool(2);
            }
            if (refreshTask != null) {
                refreshTask.cancel(false);
            }
            refreshTask = scheduler.scheduleAtFixedRate(this::refreshAll, 0, interval, TimeUnit.SECONDS);
            isRefreshing = true;
            startButton.setText("停止刷新");
            statusLabel.setText("自动刷新已启动 (间隔 " + interval + " 秒)");
        } catch (NumberFormatException e) {
            showAlert("请选择有效的刷新间隔", Alert.AlertType.WARNING);
        }
    }

    private void stopRefresh() {
        if (refreshTask != null) {
            refreshTask.cancel(false);
            refreshTask = null;
        }
        if (scheduler != null) {
            scheduler.shutdown();
            scheduler = null;
        }
        isRefreshing = false;
        startButton.setText("开始刷新");
        statusLabel.setText("自动刷新已停止");
    }

    @FXML
    private void refreshAll() {
        statusLabel.setText("正在刷新数据...");
        new Thread(() -> {
            for (Stock stock : stockList) {
                Stock updated = dataFetcher.fetchStockData(stock.getCode());
                if (updated != null) {
                    Platform.runLater(() -> {
                        stock.setPrice(updated.getPrice());
                        stock.setChange(updated.getChange());
                        stock.setChangePercent(updated.getChangePercent());
                        stock.setOpen(updated.getOpen());
                        stock.setHigh(updated.getHigh());
                        stock.setLow(updated.getLow());
                        stock.setClose(updated.getClose());
                        stock.setVolume(updated.getVolume());
                        if (!stock.getName().equals(updated.getName())) {
                            stock.setName(updated.getName());
                        }
                        alertManager.checkAlerts(stock);
                    });
                }
            }
            Platform.runLater(() -> {
                statusLabel.setText("数据已刷新 (" + LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss")) + ")");
            });
        }).start();
    }

    private void setupWebSocketListener() {
        wsService.addWsListener(new WebSocketStockService.WebSocketListener() {
            @Override
            public void onPriceUpdate(Stock stock) {
                Platform.runLater(() -> {
                    Stock existing = stockMap.get(stock.getCode());
                    if (existing != null) {
                        existing.setPrice(stock.getPrice());
                        existing.setChange(stock.getChange());
                        existing.setChangePercent(stock.getChangePercent());
                        alertManager.checkAlerts(existing);
                    }
                });
            }

            @Override
            public void onConnected() {
                Platform.runLater(() -> {
                    wsStatusLabel.setText("WS: 已连接");
                    wsStatusLabel.setStyle("-fx-text-fill: green;");
                    wsButton.setText("断开 WS");
                    statusLabel.setText("WebSocket 已连接");
                });
            }

            @Override
            public void onDisconnected() {
                Platform.runLater(() -> {
                    wsStatusLabel.setText("WS: 已断开");
                    wsStatusLabel.setStyle("-fx-text-fill: red;");
                    wsButton.setText("连接 WS");
                    statusLabel.setText("WebSocket 已断开");
                });
            }

            @Override
            public void onError(String message) {
                Platform.runLater(() -> {
                    statusLabel.setText("WS 错误: " + message);
                });
            }
        });
    }

    @FXML
    private void toggleWebSocket() {
        if (wsService.isConnected()) {
            wsService.disconnect();
        } else {
            statusLabel.setText("正在连接 WebSocket...");
            for (Stock stock : stockList) {
                wsService.addListener(stock.getCode(), s -> {
                    Platform.runLater(() -> {
                        Stock existing = stockMap.get(s.getCode());
                        if (existing != null) {
                            existing.setPrice(s.getPrice());
                            existing.setChange(s.getChange());
                            existing.setChangePercent(s.getChangePercent());
                        }
                    });
                });
            }
            wsService.connect();
        }
    }

    private void setupAlertListener() {
        alertManager.addAlertListener((stock, message) -> {
            statusLabel.setText("价格提醒: " + stock.getName());
        });
    }

    @FXML
    private void showAlertDialog() {
        Stock selected = stockTable.getSelectionModel().getSelectedItem();
        if (selected == null) {
            showAlert("请先选择一只股票", Alert.AlertType.WARNING);
            return;
        }
        Dialog<ButtonType> dialog = new Dialog<>();
        dialog.setTitle("设置价格提醒 - " + selected.getName());
        dialog.setHeaderText("当前价格: " + String.format("%.2f", selected.getPrice()));
        VBox content = new VBox(10);
        content.setPrefWidth(300);
        TextField priceField = new TextField();
        priceField.setPromptText("请输入目标价格");
        priceField.setText(String.format("%.2f", selected.getPrice()));
        ToggleGroup group = new ToggleGroup();
        RadioButton aboveRadio = new RadioButton("价格达到或超过目标价格时提醒");
        RadioButton belowRadio = new RadioButton("价格达到或低于目标价格时提醒");
        aboveRadio.setToggleGroup(group);
        belowRadio.setToggleGroup(group);
        aboveRadio.setSelected(true);
        if (alertManager.hasAlert(selected.getCode())) {
            aboveRadio.setText(aboveRadio.getText() + " (已有提醒)");
        }
        content.getChildren().addAll(
            new Label("目标价格:"),
            priceField,
            new Separator(),
            aboveRadio,
            belowRadio
        );
        dialog.getDialogPane().setContent(content);
        dialog.getDialogPane().getButtonTypes().addAll(ButtonType.OK, ButtonType.CANCEL);
        Optional<ButtonType> result = dialog.showAndWait();
        if (result.isPresent() && result.get() == ButtonType.OK) {
            try {
                double targetPrice = Double.parseDouble(priceField.getText().trim());
                boolean isAbove = aboveRadio.isSelected();
                alertManager.addPriceAlert(selected.getCode(), targetPrice, isAbove);
                statusLabel.setText("已设置价格提醒: " + selected.getName() + " -> " + targetPrice);
            } catch (NumberFormatException e) {
                showAlert("请输入有效的价格", Alert.AlertType.ERROR);
            }
        }
    }

    @FXML
    private void showExportDialog() {
        if (stockList.isEmpty()) {
            showAlert("没有可导出的数据", Alert.AlertType.WARNING);
            return;
        }
        ChoiceDialog<String> dialog = new ChoiceDialog<>("CSV", "CSV", "Excel (XML)");
        dialog.setTitle("导出数据");
        dialog.setHeaderText("选择导出格式");
        dialog.setContentText("格式:");
        Optional<String> result = dialog.showAndWait();
        result.ifPresent(format -> {
            if (format.equals("CSV")) {
                exportCsv();
            } else {
                exportExcel();
            }
        });
    }

    @FXML
    private void exportCsv() {
        DirectoryChooser chooser = new DirectoryChooser();
        chooser.setTitle("选择导出目录");
        chooser.setInitialDirectory(new File(settings.getLastExportPath()));
        File dir = chooser.showDialog(chartPane.getScene().getWindow());
        if (dir == null) {
            return;
        }
        try {
            String path = ExportHelper.exportStocksToCSV(new ArrayList<>(stockList), dir.getAbsolutePath());
            settings.setLastExportPath(dir.getAbsolutePath());
            showAlert("导出成功: " + path, Alert.AlertType.INFORMATION);
            statusLabel.setText("已导出到: " + path);
        } catch (IOException e) {
            showAlert("导出失败: " + e.getMessage(), Alert.AlertType.ERROR);
        }
    }

    @FXML
    private void exportExcel() {
        DirectoryChooser chooser = new DirectoryChooser();
        chooser.setTitle("选择导出目录");
        chooser.setInitialDirectory(new File(settings.getLastExportPath()));
        File dir = chooser.showDialog(chartPane.getScene().getWindow());
        if (dir == null) {
            return;
        }
        try {
            String path = ExportHelper.exportStocksToExcel(new ArrayList<>(stockList), dir.getAbsolutePath());
            settings.setLastExportPath(dir.getAbsolutePath());
            showAlert("导出成功: " + path, Alert.AlertType.INFORMATION);
            statusLabel.setText("已导出到: " + path);
        } catch (IOException e) {
            showAlert("导出失败: " + e.getMessage(), Alert.AlertType.ERROR);
        }
    }

    @FXML
    private void exportKlineData() {
        Stock selected = stockTable.getSelectionModel().getSelectedItem();
        if (selected == null) {
            showAlert("请先选择一只股票", Alert.AlertType.WARNING);
            return;
        }
        FileChooser chooser = new FileChooser();
        chooser.setTitle("导出K线数据");
        chooser.setInitialDirectory(new File(settings.getLastExportPath()));
        chooser.setInitialFileName(selected.getCode() + "_kline.csv");
        chooser.getExtensionFilters().add(new FileChooser.ExtensionFilter("CSV 文件", "*.csv"));
        File file = chooser.showSaveDialog(chartPane.getScene().getWindow());
        if (file == null) {
            return;
        }
        int days = Integer.parseInt(klineDaysCombo.getValue());
        new Thread(() -> {
            var candleData = dataFetcher.fetchKLineData(selected.getCode(), days);
            Platform.runLater(() -> {
                try {
                    String path = ExportHelper.exportKLineToCSV(candleData, selected.getCode(), selected.getName(), file);
                    settings.setLastExportPath(file.getParent());
                    showAlert("K线导出成功: " + path, Alert.AlertType.INFORMATION);
                    statusLabel.setText("已导出K线到: " + path);
                } catch (IOException e) {
                    showAlert("导出失败: " + e.getMessage(), Alert.AlertType.ERROR);
                }
            });
        }).start();
    }

    @FXML
    private void openSettings() {
        Dialog<ButtonType> dialog = new Dialog<>();
        dialog.setTitle("设置");
        dialog.initModality(Modality.APPLICATION_MODAL);
        SettingsPane settingsPane = new SettingsPane(settings);
        dialog.getDialogPane().setContent(settingsPane);
        dialog.getDialogPane().getButtonTypes().add(ButtonType.CLOSE);
        dialog.showAndWait();
    }

    @FXML
    private void clearCache() {
        statusLabel.setText("缓存已清理");
    }

    @FXML
    private void exitApp() {
        shutdown();
        Platform.exit();
    }

    private void startClock() {
        ScheduledExecutorService clockScheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "clock-thread");
            t.setDaemon(true);
            return t;
        });
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("HH:mm:ss");
        clockTask = clockScheduler.scheduleAtFixedRate(() -> {
            Platform.runLater(() -> {
                clockLabel.setText(LocalTime.now().format(formatter));
            });
        }, 0, 1, TimeUnit.SECONDS);
    }

    private void showAlert(String message, Alert.AlertType type) {
        Alert alert = new Alert(type);
        alert.setTitle("提示");
        alert.setHeaderText(null);
        alert.setContentText(message);
        alert.showAndWait();
    }

    public void shutdown() {
        stopRefresh();
        wsService.disconnect();
        if (dataFetcher != null) {
            dataFetcher.shutdown();
        }
        if (clockTask != null) {
            clockTask.cancel(false);
        }
    }
}
