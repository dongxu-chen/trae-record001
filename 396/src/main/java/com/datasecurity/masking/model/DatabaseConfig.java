package com.datasecurity.masking.model;

import com.datasecurity.masking.enums.DatabaseType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DatabaseConfig {

    private String id;

    private String name;

    private DatabaseType type;

    private String host;

    private Integer port;

    private String database;

    private String username;

    private String password;

    private String connectionUrl;
}
