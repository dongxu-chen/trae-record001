package com.dlq.platform.es.config;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.json.jackson.JacksonJsonpMapper;
import co.elastic.clients.transport.ElasticsearchTransport;
import co.elastic.clients.transport.TransportUtils;
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
import org.springframework.util.StringUtils;

import javax.net.ssl.SSLContext;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.List;

@Data
@Configuration
@ConfigurationProperties(prefix = "elasticsearch")
public class ElasticsearchConfig {

    private List<String> hosts;

    private String username;

    private String password;

    private String apiKey;

    private boolean sslEnabled = false;

    private String caCertificate;

    private boolean sslVerificationEnabled = true;

    private int connectTimeout = 5000;

    private int socketTimeout = 60000;

    private int connectionRequestTimeout = 5000;

    private String deadLetterIndex = "dlq_dead_letter";

    private String alertRuleIndex = "dlq_alert_rule";

    private String alertHistoryIndex = "dlq_alert_history";

    private String replayRecordIndex = "dlq_replay_record";

    @Bean
    public RestClient restClient() throws Exception {
        HttpHost[] httpHosts = hosts.stream()
                .map(this::parseHost)
                .toArray(HttpHost[]::new);

        RestClientBuilder builder = RestClient.builder(httpHosts);

        builder.setRequestConfigCallback(requestConfigBuilder -> requestConfigBuilder
                .setConnectTimeout(connectTimeout)
                .setSocketTimeout(socketTimeout)
                .setConnectionRequestTimeout(connectionRequestTimeout));

        if (StringUtils.hasText(username) && StringUtils.hasText(password)) {
            final CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
            credentialsProvider.setCredentials(
                    AuthScope.ANY,
                    new UsernamePasswordCredentials(username, password)
            );
            builder.setHttpClientConfigCallback(httpClientBuilder -> {
                httpClientBuilder.setDefaultCredentialsProvider(credentialsProvider);
                if (sslEnabled) {
                    try {
                        SSLContext sslContext = buildSSLContext();
                        httpClientBuilder.setSSLContext(sslContext);
                        if (!sslVerificationEnabled) {
                            httpClientBuilder.setSSLHostnameVerifier((hostname, session) -> true);
                        }
                    } catch (Exception e) {
                        throw new RuntimeException("Failed to configure SSL", e);
                    }
                }
                return httpClientBuilder;
            });
        } else if (StringUtils.hasText(apiKey)) {
            builder.setDefaultHeaders(
                    new org.apache.http.Header[]{
                            new org.apache.http.message.BasicHeader("Authorization", "ApiKey " + apiKey)
                    }
            );
            if (sslEnabled) {
                builder.setHttpClientConfigCallback(httpClientBuilder -> {
                    try {
                        SSLContext sslContext = buildSSLContext();
                        httpClientBuilder.setSSLContext(sslContext);
                        if (!sslVerificationEnabled) {
                            httpClientBuilder.setSSLHostnameVerifier((hostname, session) -> true);
                        }
                    } catch (Exception e) {
                        throw new RuntimeException("Failed to configure SSL", e);
                    }
                    return httpClientBuilder;
                });
            }
        } else if (sslEnabled) {
            builder.setHttpClientConfigCallback(httpClientBuilder -> {
                try {
                    SSLContext sslContext = buildSSLContext();
                    httpClientBuilder.setSSLContext(sslContext);
                    if (!sslVerificationEnabled) {
                        httpClientBuilder.setSSLHostnameVerifier((hostname, session) -> true);
                    }
                } catch (Exception e) {
                    throw new RuntimeException("Failed to configure SSL", e);
                }
                return httpClientBuilder;
            });
        }

        return builder.build();
    }

    @Bean
    public ElasticsearchTransport elasticsearchTransport(RestClient restClient) {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
        return new RestClientTransport(
                restClient,
                new JacksonJsonpMapper(objectMapper)
        );
    }

    @Bean
    public ElasticsearchClient elasticsearchClient(ElasticsearchTransport transport) {
        return new ElasticsearchClient(transport);
    }

    private HttpHost parseHost(String host) {
        String[] parts = host.split(":");
        if (parts.length == 2) {
            return new HttpHost(parts[0], Integer.parseInt(parts[1]), sslEnabled ? "https" : "http");
        } else if (parts.length == 3) {
            return new HttpHost(parts[1].substring(2), Integer.parseInt(parts[2]), parts[0]);
        }
        throw new IllegalArgumentException("Invalid Elasticsearch host format: " + host);
    }

    private SSLContext buildSSLContext() throws Exception {
        if (StringUtils.hasText(caCertificate)) {
            CertificateFactory cf = CertificateFactory.getInstance("X.509");
            ByteArrayInputStream is = new ByteArrayInputStream(caCertificate.getBytes(StandardCharsets.UTF_8));
            Certificate ca = cf.generateCertificate(is);

            return TransportUtils.sslContextFromHttpCaCerts(List.of((X509Certificate) ca));
        }
        return TransportUtils.sslContextFromCaCert(null);
    }
}
