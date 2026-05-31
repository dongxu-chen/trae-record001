package com.datacheck.config;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.json.jackson.JacksonJsonpMapper;
import co.elastic.clients.transport.ElasticsearchTransport;
import co.elastic.clients.transport.rest_client.RestClientTransport;
import com.datacheck.model.enums.DataSourceType;
import org.apache.http.HttpHost;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;

@Configuration
public class ElasticsearchConfig {

    @Value("${elasticsearch.source.hosts:http://localhost:9200}")
    private String sourceHosts;

    @Value("${elasticsearch.source.username:}")
    private String sourceUsername;

    @Value("${elasticsearch.source.password:}")
    private String sourcePassword;

    @Value("${elasticsearch.source.connect-timeout:5000}")
    private int sourceConnectTimeout;

    @Value("${elasticsearch.source.socket-timeout:30000}")
    private int sourceSocketTimeout;

    @Value("${elasticsearch.target.hosts:http://localhost:9201}")
    private String targetHosts;

    @Value("${elasticsearch.target.username:}")
    private String targetUsername;

    @Value("${elasticsearch.target.password:}")
    private String targetPassword;

    @Value("${elasticsearch.target.connect-timeout:5000}")
    private int targetConnectTimeout;

    @Value("${elasticsearch.target.socket-timeout:30000}")
    private int targetSocketTimeout;

    @Bean(name = "sourceElasticsearchClient")
    public ElasticsearchClient sourceElasticsearchClient() {
        return createClient(sourceHosts, sourceUsername, sourcePassword,
                sourceConnectTimeout, sourceSocketTimeout);
    }

    @Bean(name = "targetElasticsearchClient")
    public ElasticsearchClient targetElasticsearchClient() {
        return createClient(targetHosts, targetUsername, targetPassword,
                targetConnectTimeout, targetSocketTimeout);
    }

    private ElasticsearchClient createClient(String hostsStr, String username, String password,
                                             int connectTimeout, int socketTimeout) {
        String[] hostArr = hostsStr.split(",");
        HttpHost[] httpHosts = new HttpHost[hostArr.length];
        for (int i = 0; i < hostArr.length; i++) {
            String hostUrl = hostArr[i].trim();
            if (hostUrl.startsWith("http://")) {
                hostUrl = hostUrl.substring(7);
            } else if (hostUrl.startsWith("https://")) {
                hostUrl = hostUrl.substring(8);
            }
            String[] parts = hostUrl.split(":");
            httpHosts[i] = new HttpHost(parts[0], Integer.parseInt(parts[1]));
        }

        RestClientBuilder builder = RestClient.builder(httpHosts);

        if (StringUtils.hasText(username) && StringUtils.hasText(password)) {
            CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
            credentialsProvider.setCredentials(AuthScope.ANY,
                    new UsernamePasswordCredentials(username, password));
            builder.setHttpClientConfigCallback(httpClientBuilder ->
                    httpClientBuilder.setDefaultCredentialsProvider(credentialsProvider));
        }

        builder.setRequestConfigCallback(requestConfigBuilder ->
                requestConfigBuilder
                        .setConnectTimeout(connectTimeout)
                        .setSocketTimeout(socketTimeout));

        ElasticsearchTransport transport = new RestClientTransport(
                builder.build(), new JacksonJsonpMapper());

        return new ElasticsearchClient(transport);
    }
}
