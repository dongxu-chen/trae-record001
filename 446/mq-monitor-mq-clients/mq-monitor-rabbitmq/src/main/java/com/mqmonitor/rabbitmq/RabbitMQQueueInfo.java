package com.mqmonitor.rabbitmq;

public class RabbitMQQueueInfo {
    private String queueName;
    private String vhost;
    private boolean durable;
    private boolean exclusive;
    private boolean autoDelete;
    private int messageCount;
    private int consumerCount;

    public String getQueueName() { return queueName; }
    public void setQueueName(String queueName) { this.queueName = queueName; }
    public String getVhost() { return vhost; }
    public void setVhost(String vhost) { this.vhost = vhost; }
    public boolean isDurable() { return durable; }
    public void setDurable(boolean durable) { this.durable = durable; }
    public boolean isExclusive() { return exclusive; }
    public void setExclusive(boolean exclusive) { this.exclusive = exclusive; }
    public boolean isAutoDelete() { return autoDelete; }
    public void setAutoDelete(boolean autoDelete) { this.autoDelete = autoDelete; }
    public int getMessageCount() { return messageCount; }
    public void setMessageCount(int messageCount) { this.messageCount = messageCount; }
    public int getConsumerCount() { return consumerCount; }
    public void setConsumerCount(int consumerCount) { this.consumerCount = consumerCount; }
}
