package com.logplatform.config;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.json.jackson.JacksonJsonpMapper;
import co.elastic.clients.transport.ElasticsearchTransport;
import co.elastic.clients.transport.rest_client.RestClientTransport;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import lombok.Data;
import org.apache.http.HttpHost;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

@Data
@Configuration
@ConfigurationProperties(prefix = "elasticsearch")
public class ElasticsearchConfig {

    private String uris;
    private String username;
    private String password;
    private Duration connectTimeout = Duration.ofSeconds(5);
    private Duration socketTimeout = Duration.ofSeconds(30);
    private int maxConnections = 100;
    private int maxConnectionsPerRoute = 50;

    @Bean
    public ElasticsearchClient elasticsearchClient() {
        HttpHost[] httpHosts = parseUris();

        final CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
        credentialsProvider.setCredentials(AuthScope.ANY,
                new UsernamePasswordCredentials(username, password));

        RestClientBuilder builder = RestClient.builder(httpHosts)
                .setHttpClientConfigCallback(httpClientBuilder -> httpClientBuilder
                        .setDefaultCredentialsProvider(credentialsProvider)
                        .setMaxConnTotal(maxConnections)
                        .setMaxConnPerRoute(maxConnectionsPerRoute)
                        .setConnectTimeout((int) connectTimeout.toMillis())
                        .setSocketTimeout((int) socketTimeout.toMillis()));

        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());

        ElasticsearchTransport transport = new RestClientTransport(
                builder.build(), new JacksonJsonpMapper(mapper));

        return new ElasticsearchClient(transport);
    }

    private HttpHost[] parseUris() {
        String[] uriArray = uris.split(",");
        HttpHost[] hosts = new HttpHost[uriArray.length];
        for (int i = 0; i < uriArray.length; i++) {
            String uri = uriArray[i].trim();
            hosts[i] = HttpHost.create(uri);
        }
        return hosts;
    }
}
