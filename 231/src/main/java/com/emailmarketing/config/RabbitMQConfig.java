package com.emailmarketing.config;

import org.springframework.amqp.core.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    public static final String EMAIL_EXCHANGE = "email.exchange";
    public static final String EMAIL_QUEUE = "email.queue";
    public static final String EMAIL_ROUTING_KEY = "email.send";

    public static final String EMAIL_DLX_EXCHANGE = "email.dlx.exchange";
    public static final String EMAIL_DLX_QUEUE = "email.dlx.queue";
    public static final String EMAIL_DLX_ROUTING_KEY = "email.dlx";

    @Bean
    public DirectExchange emailExchange() {
        return new DirectExchange(EMAIL_EXCHANGE, true, false);
    }

    @Bean
    public DirectExchange emailDlxExchange() {
        return new DirectExchange(EMAIL_DLX_EXCHANGE, true, false);
    }

    @Bean
    public Queue emailQueue() {
        return QueueBuilder.durable(EMAIL_QUEUE)
                .withArgument("x-dead-letter-exchange", EMAIL_DLX_EXCHANGE)
                .withArgument("x-dead-letter-routing-key", EMAIL_DLX_ROUTING_KEY)
                .build();
    }

    @Bean
    public Queue emailDlxQueue() {
        return QueueBuilder.durable(EMAIL_DLX_QUEUE).build();
    }

    @Bean
    public Binding emailBinding() {
        return BindingBuilder.bind(emailQueue()).to(emailExchange()).with(EMAIL_ROUTING_KEY);
    }

    @Bean
    public Binding emailDlxBinding() {
        return BindingBuilder.bind(emailDlxQueue()).to(emailDlxExchange()).with(EMAIL_DLX_ROUTING_KEY);
    }
}
