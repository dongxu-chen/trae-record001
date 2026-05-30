package com.dtmonitor.storage.config;

import org.apache.http.HttpHost;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.elasticsearch.client.RestHighLevelClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ElasticsearchConfig {

    @Value("${elasticsearch.host:localhost}")
    private String host;

    @Value("${elasticsearch.port:9200}")
    private int port;

    @Value("${elasticsearch.scheme:http}")
    private String scheme;

    @Value("${elasticsearch.username:}")
    private String username;

    @Value("${elasticsearch.password:}")
    private String password;

    @Bean(destroyMethod = "close")
    public RestHighLevelClient restHighLevelClient() {
        RestClientBuilder builder = RestClient.builder(new HttpHost(host, port, scheme));

        if (username != null && !username.isEmpty()) {
            builder.setHttpClientConfigCallback(httpClientBuilder ->
                    httpClientBuilder.setDefaultCredentialsProvider(
                            new org.elasticsearch.client.RestClientBuilder.BasicCredentialsProvider() {{
                                setCredentials(
                                        new org.apache.http.auth.AuthScope(HttpHost.create(host)),
                                        new org.apache.http.auth.UsernamePasswordCredentials(username, password)
                                );
                            }}
                    )
            );
        }

        return new RestHighLevelClient(builder);
    }
}
