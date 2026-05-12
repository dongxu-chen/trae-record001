module com.stock {
    requires javafx.controls;
    requires javafx.fxml;
    requires javafx.graphics;
    requires java.net.http;

    opens com.stock to javafx.fxml;
    opens com.stock.controller to javafx.fxml;

    exports com.stock;
    exports com.stock.model;
    exports com.stock.controller;
    exports com.stock.view;
    exports com.stock.service;
    exports com.stock.chart;
}
