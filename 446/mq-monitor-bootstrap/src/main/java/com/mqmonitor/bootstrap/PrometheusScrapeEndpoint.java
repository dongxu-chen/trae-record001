package com.mqmonitor.bootstrap;

import com.mqmonitor.exporter.PrometheusExporter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class PrometheusScrapeEndpoint {

    private final PrometheusExporter prometheusExporter;

    @Autowired
    public PrometheusScrapeEndpoint(PrometheusExporter prometheusExporter) {
        this.prometheusExporter = prometheusExporter;
    }

    @GetMapping(value = "/actuator/prometheus", produces = "text/plain; version=0.0.4; charset=utf-8")
    public String prometheus() {
        return prometheusExporter.scrape();
    }

    @GetMapping(value = "/metrics", produces = "text/plain; version=0.0.4; charset=utf-8")
    public String metrics() {
        return prometheusExporter.scrape();
    }
}
