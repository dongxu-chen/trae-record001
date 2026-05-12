package com.stock.view;

import com.stock.model.AppSettings;
import javafx.geometry.Insets;
import javafx.scene.control.*;
import javafx.scene.layout.*;

public class SettingsPane extends VBox {

    private final AppSettings settings;

    private CheckBox autoRefreshCheckBox;
    private ComboBox<Integer> intervalComboBox;
    private CheckBox enableWsCheckBox;
    private ComboBox<Integer> klineDaysComboBox;
    private ComboBox<String> themeComboBox;
    private CheckBox showAlertDialogCheckBox;

    public SettingsPane(AppSettings settings) {
        this.settings = settings;
        setSpacing(20);
        setPadding(new Insets(20));
        setPrefWidth(400);
        buildUI();
        bindValues();
    }

    private void buildUI() {
        Label title = new Label("应用设置");
        title.setStyle("-fx-font-size: 18; -fx-font-weight: bold;");
        getChildren().add(title);

        getChildren().add(createGeneralSection());
        getChildren().add(createNetworkSection());
        getChildren().add(createDisplaySection());
        getChildren().add(createAlertSection());

        getChildren().add(createButtonBox());
    }

    private TitledPane createGeneralSection() {
        VBox content = new VBox(15);
        content.setPadding(new Insets(10));

        autoRefreshCheckBox = new CheckBox("启动时自动刷新");
        autoRefreshCheckBox.setSelected(true);

        HBox intervalBox = new HBox(10);
        intervalBox.getChildren().add(new Label("刷新间隔(秒):"));
        intervalComboBox = new ComboBox<>();
        intervalComboBox.getItems().addAll(5, 10, 15, 30, 60, 120);
        intervalComboBox.setValue(10);
        intervalBox.getChildren().add(intervalComboBox);

        content.getChildren().addAll(autoRefreshCheckBox, intervalBox);

        TitledPane pane = new TitledPane("常规设置", content);
        pane.setExpanded(true);
        pane.setAnimated(false);
        return pane;
    }

    private TitledPane createNetworkSection() {
        VBox content = new VBox(15);
        content.setPadding(new Insets(10));

        enableWsCheckBox = new CheckBox("启用 WebSocket 实时推送");
        enableWsCheckBox.setSelected(false);
        enableWsCheckBox.setTooltip(new Tooltip("启用后将使用 WebSocket 获取实时行情（需要网络支持）"));

        Label note = new Label("注意：WebSocket 实时推送功能需要连接到股票数据服务。\n如果无法连接，系统将自动降级为定时轮询模式。");
        note.setStyle("-fx-font-size: 11; -fx-text-fill: gray;");
        note.setWrapText(true);

        content.getChildren().addAll(enableWsCheckBox, note);

        TitledPane pane = new TitledPane("网络设置", content);
        pane.setExpanded(true);
        pane.setAnimated(false);
        return pane;
    }

    private TitledPane createDisplaySection() {
        VBox content = new VBox(15);
        content.setPadding(new Insets(10));

        HBox klineBox = new HBox(10);
        klineBox.getChildren().add(new Label("默认 K 线天数:"));
        klineDaysComboBox = new ComboBox<>();
        klineDaysComboBox.getItems().addAll(20, 30, 60, 90, 120, 180);
        klineDaysComboBox.setValue(60);
        klineBox.getChildren().add(klineDaysComboBox);

        HBox themeBox = new HBox(10);
        themeBox.getChildren().add(new Label("界面主题:"));
        themeComboBox = new ComboBox<>();
        themeComboBox.getItems().addAll("默认", "深色");
        themeComboBox.setValue("默认");
        themeBox.getChildren().add(themeComboBox);

        content.getChildren().addAll(klineBox, themeBox);

        TitledPane pane = new TitledPane("显示设置", content);
        pane.setExpanded(true);
        pane.setAnimated(false);
        return pane;
    }

    private TitledPane createAlertSection() {
        VBox content = new VBox(15);
        content.setPadding(new Insets(10));

        showAlertDialogCheckBox = new CheckBox("价格提醒弹出对话框");
        showAlertDialogCheckBox.setSelected(true);
        showAlertDialogCheckBox.setTooltip(new Tooltip("取消选中后仅在状态栏显示提醒，不弹窗"));

        content.getChildren().addAll(showAlertDialogCheckBox);

        TitledPane pane = new TitledPane("提醒设置", content);
        pane.setExpanded(true);
        pane.setAnimated(false);
        return pane;
    }

    private HBox createButtonBox() {
        HBox buttonBox = new HBox(10);

        Button applyBtn = new Button("应用");
        applyBtn.setOnAction(e -> saveSettings());

        Button resetBtn = new Button("重置为默认");
        resetBtn.setOnAction(e -> resetToDefault());

        buttonBox.getChildren().addAll(applyBtn, resetBtn);
        return buttonBox;
    }

    private void bindValues() {
        autoRefreshCheckBox.selectedProperty().bindBidirectional(settings.autoRefreshOnStartupProperty());
        intervalComboBox.valueProperty().addListener((obs, old, newVal) -> {
            if (newVal != null) {
                settings.setRefreshIntervalSeconds(newVal);
            }
        });
        enableWsCheckBox.selectedProperty().bindBidirectional(settings.enableWebSocketProperty());
        klineDaysComboBox.valueProperty().addListener((obs, old, newVal) -> {
            if (newVal != null) {
                settings.setDefaultKlineDays(newVal);
            }
        });
        themeComboBox.valueProperty().addListener((obs, old, newVal) -> {
            if (newVal != null) {
                settings.setTheme(newVal);
            }
        });
        showAlertDialogCheckBox.selectedProperty().bindBidirectional(settings.showPriceAlertDialogProperty());

        intervalComboBox.setValue(settings.getRefreshIntervalSeconds());
        klineDaysComboBox.setValue(settings.getDefaultKlineDays());
        themeComboBox.setValue(settings.getTheme());
    }

    private void saveSettings() {
        Alert alert = new Alert(Alert.AlertType.INFORMATION);
        alert.setTitle("设置已保存");
        alert.setHeaderText(null);
        alert.setContentText("设置已应用！\n部分设置（如 WebSocket）可能需要重启应用才能生效。");
        alert.showAndWait();
    }

    private void resetToDefault() {
        settings.setAutoRefreshOnStartup(true);
        settings.setRefreshIntervalSeconds(10);
        settings.setEnableWebSocket(false);
        settings.setDefaultKlineDays(60);
        settings.setTheme("默认");
        settings.setShowPriceAlertDialog(true);

        intervalComboBox.setValue(10);
        klineDaysComboBox.setValue(60);
        themeComboBox.setValue("默认");

        Alert alert = new Alert(Alert.AlertType.INFORMATION);
        alert.setTitle("已重置");
        alert.setHeaderText(null);
        alert.setContentText("设置已恢复为默认值。");
        alert.showAndWait();
    }

    public AppSettings getSettings() {
        return settings;
    }
}
