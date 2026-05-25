package com.survey.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    public static final String SURVEY_EXCHANGE = "survey.exchange";
    public static final String VOTE_QUEUE = "survey.vote.queue";
    public static final String STATS_QUEUE = "survey.stats.queue";
    public static final String VOTE_ROUTING_KEY = "survey.vote";
    public static final String STATS_ROUTING_KEY = "survey.stats";

    @Bean
    public DirectExchange surveyExchange() {
        return new DirectExchange(SURVEY_EXCHANGE);
    }

    @Bean
    public Queue voteQueue() {
        return QueueBuilder.durable(VOTE_QUEUE)
                .deadLetterExchange(SURVEY_EXCHANGE)
                .deadLetterRoutingKey("survey.deadletter")
                .build();
    }

    @Bean
    public Queue statsQueue() {
        return QueueBuilder.durable(STATS_QUEUE).build();
    }

    @Bean
    public Binding voteBinding(Queue voteQueue, DirectExchange surveyExchange) {
        return BindingBuilder.bind(voteQueue).to(surveyExchange).with(VOTE_ROUTING_KEY);
    }

    @Bean
    public Binding statsBinding(Queue statsQueue, DirectExchange surveyExchange) {
        return BindingBuilder.bind(statsQueue).to(surveyExchange).with(STATS_ROUTING_KEY);
    }

    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory, MessageConverter jsonMessageConverter) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(jsonMessageConverter);
        factory.setAcknowledgeMode(AcknowledgeMode.MANUAL);
        factory.setPrefetchCount(1);
        return factory;
    }
}
