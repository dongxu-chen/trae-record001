'use strict';

const axios = require('axios');

class EventHandler {
    constructor() {
        this.slackWebhook = process.env.SLACK_WEBHOOK_URL;
        this.teamsWebhook = process.env.TEAMS_WEBHOOK_URL;
        this.dingtalkWebhook = process.env.DINGTALK_WEBHOOK_URL;
    }

    async handle(event) {
        console.log(`Processing event: ${event.object?.reason || 'Unknown'}`);

        const result = {
            status: 'processed',
            event_type: event.type || 'Unknown',
            notifications: []
        };

        try {
            const eventObj = event.object;
            if (!eventObj) {
                throw new Error("Invalid event format: missing 'object'");
            }

            const eventData = this.extractEventData(eventObj);
            
            if (this.slackWebhook) {
                const slackResult = await this.sendSlackNotification(eventData);
                result.notifications.push({ channel: 'slack', status: slackResult });
            }
            
            if (this.teamsWebhook) {
                const teamsResult = await this.sendTeamsNotification(eventData);
                result.notifications.push({ channel: 'teams', status: teamsResult });
            }
            
            if (this.dingtalkWebhook) {
                const dingtalkResult = await this.sendDingtalkNotification(eventData);
                result.notifications.push({ channel: 'dingtalk', status: dingtalkResult });
            }

        } catch (e) {
            console.error(`Error processing event: ${e.message}`);
            result.status = 'error';
            result.error = e.message;
        }

        return result;
    }

    extractEventData(eventObj) {
        const metadata = eventObj.metadata || {};
        const involved = eventObj.involvedObject || {};
        
        return {
            name: involved.name || metadata.name || 'Unknown',
            namespace: involved.namespace || metadata.namespace || 'default',
            kind: involved.kind || 'Unknown',
            reason: eventObj.reason || 'Unknown',
            message: eventObj.message || 'No message',
            type: eventObj.type || 'Normal',
            first_timestamp: eventObj.firstTimestamp || '',
            last_timestamp: eventObj.lastTimestamp || '',
            count: eventObj.count || 1,
            source: eventObj.source?.component || 'Unknown'
        };
    }

    async sendSlackNotification(eventData) {
        try {
            const color = eventData.type === 'Normal' ? '#36a64f' : '#ff0000';
            
            const blocks = [
                {
                    type: 'header',
                    text: {
                        type: 'plain_text',
                        text: `Kubernetes Event: ${eventData.reason}`
                    }
                },
                {
                    type: 'section',
                    fields: [
                        { type: 'mrkdwn', text: `*Type:*\n${eventData.type}` },
                        { type: 'mrkdwn', text: `*Namespace:*\n${eventData.namespace}` },
                        { type: 'mrkdwn', text: `*Name:*\n${eventData.name}` },
                        { type: 'mrkdwn', text: `*Count:*\n${eventData.count}` }
                    ]
                },
                {
                    type: 'section',
                    text: {
                        type: 'mrkdwn',
                        text: `*Message:*\n\`\`\`${eventData.message.substring(0, 500)}\`\`\``
                    }
                }
            ];

            const payload = {
                text: `K8s Event: ${eventData.reason} - ${eventData.name}`,
                blocks: blocks
            };

            await axios.post(this.slackWebhook, payload, { timeout: 10000 });
            return 'sent';
        } catch (e) {
            console.error(`Slack notification failed: ${e.message}`);
            return `failed: ${e.message}`;
        }
    }

    async sendTeamsNotification(eventData) {
        try {
            const themeColor = eventData.type === 'Normal' ? '00FF00' : 'FF0000';
            
            const card = {
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: {
                        type: 'AdaptiveCard',
                        version: '1.2',
                        themeColor: themeColor,
                        body: [
                            {
                                type: 'TextBlock',
                                size: 'Large',
                                weight: 'Bolder',
                                text: `Kubernetes Event: ${eventData.reason}`
                            },
                            {
                                type: 'FactSet',
                                facts: [
                                    { title: 'Type', value: eventData.type },
                                    { title: 'Namespace', value: eventData.namespace },
                                    { title: 'Name', value: eventData.name },
                                    { title: 'Count', value: `${eventData.count}` }
                                ]
                            },
                            {
                                type: 'TextBlock',
                                text: eventData.message.substring(0, 500),
                                wrap: true
                            }
                        ]
                    }
                }]
            };

            await axios.post(this.teamsWebhook, card, { timeout: 10000 });
            return 'sent';
        } catch (e) {
            console.error(`Teams notification failed: ${e.message}`);
            return `failed: ${e.message}`;
        }
    }

    async sendDingtalkNotification(eventData) {
        try {
            const markdownText = `### Kubernetes Event: ${eventData.reason}

**Type**: ${eventData.type}
**Namespace**: ${eventData.namespace}
**Name**: ${eventData.name}
**Count**: ${eventData.count}

**Message**:
${eventData.message.substring(0, 500)}`;

            const payload = {
                msgtype: 'markdown',
                markdown: {
                    title: `K8s Event: ${eventData.reason}`,
                    text: markdownText
                }
            };

            await axios.post(this.dingtalkWebhook, payload, { timeout: 10000 });
            return 'sent';
        } catch (e) {
            console.error(`DingTalk notification failed: ${e.message}`);
            return `failed: ${e.message}`;
        }
    }
}

const handler = new EventHandler();

module.exports = async (event, context) => {
    try {
        let eventData;
        if (typeof event === 'string') {
            eventData = JSON.parse(event);
        } else if (typeof event === 'object' && event.body) {
            eventData = JSON.parse(event.body.toString());
        } else {
            eventData = event;
        }
        
        const result = await handler.handle(eventData);
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(result)
        };
    } catch (e) {
        console.error(`Handler error: ${e.message}`);
        return {
            statusCode: 500,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'error', error: e.message })
        };
    }
};
