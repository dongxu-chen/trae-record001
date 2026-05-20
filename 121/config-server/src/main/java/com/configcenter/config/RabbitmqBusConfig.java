package com.configcenter.config;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.bus.BusProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitmqBusConfig {

    public static final String CONFIG_BUS_EXCHANGE = "springCloudBus";
    public static final String REFRESH_ROUTING_KEY_PREFIX = "refresh.";

    @Value("${spring.cloud.bus.id:config-server}")
    private String serviceId;

    @Bean
    public TopicExchange configBusExchange() {
        return new TopicExchange(CONFIG_BUS_EXCHANGE, true, false);
    }

    @Bean
    public Queue configServerQueue() {
        return new Queue("config.server.queue." + serviceId, true);
    }

    @Bean
    public Binding configServerBinding(Queue configServerQueue, TopicExchange configBusExchange) {
        return BindingBuilder.bind(configServerQueue)
                .to(configBusExchange)
                .with(REFRESH_ROUTING_KEY_PREFIX + "#");
    }

    @Bean
    public Jackson2JsonMessageConverter messageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory,
                                         Jackson2JsonMessageConverter messageConverter) {
        RabbitTemplate rabbitTemplate = new RabbitTemplate(connectionFactory);
        rabbitTemplate.setMessageConverter(messageConverter);
        return rabbitTemplate;
    }
}
