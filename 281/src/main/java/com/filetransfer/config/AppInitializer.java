package com.filetransfer.config;

import com.filetransfer.service.MinIOService;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class AppInitializer implements CommandLineRunner {
    private final MinIOService minIOService;

    @Override
    public void run(String... args) {
        minIOService.createBucketIfNotExists();
    }
}
