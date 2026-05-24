package com.wolfkill;

import com.wolfkill.service.RankService;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class WolfKillApplication {
    public static void main(String[] args) {
        SpringApplication.run(WolfKillApplication.class, args);
    }

    @Bean
    public ApplicationRunner initRankSeason(RankService rankService) {
        return args -> {
            rankService.initDefaultSeason();
        };
    }
}
