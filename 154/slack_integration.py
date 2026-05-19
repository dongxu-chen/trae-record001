import logging
import json
import time
import threading
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError


class SlackIntegration:
    def __init__(self, bot_token, signing_secret, channel_id, bot_name="K8s Event Bot", bot_icon=":kubernetes:", button_timeout=30):
        self.app = App(token=bot_token, signing_secret=signing_secret, request_verification_enabled=True)
        self.channel_id = channel_id
        self.bot_name = bot_name
        self.bot_icon = bot_icon
        self.button_timeout = button_timeout
        self.logger = logging.getLogger(__name__)
        self.k8s_watcher = None
        self.config = None
        self.active_messages = {}
        self.timeout_thread = None
        
        self._register_actions()
        self._start_timeout_worker()

    def set_k8s_watcher(self, k8s_watcher):
        self.k8s_watcher = k8s_watcher

    def set_config(self, config):
        self.config = config

    def _start_timeout_worker(self):
        if self.timeout_thread is None:
            self.timeout_thread = threading.Thread(target=self._timeout_worker, daemon=True)
            self.timeout_thread.start()

    def _timeout_worker(self):
        while True:
            time.sleep(5)
            self._check_timeouts()

    def _check_timeouts(self):
        current_time = time.time()
        messages_to_expire = []
        
        for ts, data in self.active_messages.items():
            if current_time - data['timestamp'] >= self.button_timeout:
                messages_to_expire.append(ts)
        
        for ts in messages_to_expire:
            del self.active_messages[ts]
            self._disable_buttons(ts)

    def _disable_buttons(self, ts):
        try:
            result = self.app.client.conversations_history(
                channel=self.channel_id,
                latest=ts,
                limit=1,
                inclusive=True
            )
            
            if result['messages'] and len(result['messages']) > 0:
                original_msg = result['messages'][0]
                blocks = original_msg.get('blocks', [])
                
                new_blocks = []
                for block in blocks:
                    if block.get('type') == 'actions':
                        new_blocks.append({
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": ":lock: 按钮已超时（30秒）"
                                }
                            ]
                        })
                    else:
                        new_blocks.append(block)
                
                self.app.client.chat_update(
                    channel=self.channel_id,
                    ts=ts,
                    blocks=new_blocks,
                    text="Buttons have timed out"
                )
                self.logger.info(f"Disabled buttons for message {ts}")
        except Exception as e:
            self.logger.error(f"Error disabling buttons: {e}")

    def _register_actions(self):
        @self.app.action("restart_pod")
        def handle_restart(ack, body, say):
            ack()
            try:
                action_value = json.loads(body['actions'][0]['value'])
                namespace = action_value['namespace']
                pod_name = action_value['pod_name']
                
                message_ts = body['container']['message_ts']
                
                if message_ts in self.active_messages:
                    del self.active_messages[message_ts]
                
                say(
                    text=f"Restarting pod: {pod_name}...",
                    thread_ts=message_ts
                )
                
                success, result = self.k8s_watcher.restart_pod(namespace, pod_name)
                
                if success:
                    say(
                        text=f":white_check_mark: Successfully restarted pod *{pod_name}*",
                        thread_ts=message_ts
                    )
                else:
                    say(
                        text=f":x: Failed to restart pod *{pod_name}*: {result}",
                        thread_ts=message_ts
                    )
            except Exception as e:
                self.logger.error(f"Error handling restart: {e}")
                say(text=f":x: Error processing restart: {str(e)}")

        @self.app.action("get_logs")
        def handle_logs(ack, body, say):
            ack()
            try:
                action_value = json.loads(body['actions'][0]['value'])
                namespace = action_value['namespace']
                pod_name = action_value['pod_name']
                tail_lines = self.config.get('actions', {}).get('logs', {}).get('tail_lines', 100)
                
                message_ts = body['container']['message_ts']
                
                if message_ts in self.active_messages:
                    del self.active_messages[message_ts]
                
                say(
                    text=f"Fetching logs for pod: {pod_name}...",
                    thread_ts=message_ts
                )
                
                success, logs = self.k8s_watcher.get_pod_logs(namespace, pod_name, tail_lines)
                
                if success:
                    if logs:
                        log_chunks = self._chunk_logs(logs)
                        for i, chunk in enumerate(log_chunks):
                            say(
                                text=f"*Logs for {pod_name} (Part {i+1}/{len(log_chunks)})*:\n```\n{chunk}\n```",
                                thread_ts=message_ts
                            )
                    else:
                        say(
                            text=f":information_source: No logs found for pod *{pod_name}*",
                            thread_ts=message_ts
                        )
                else:
                    say(
                        text=f":x: Failed to get logs for *{pod_name}*: {logs}",
                        thread_ts=message_ts
                    )
            except Exception as e:
                self.logger.error(f"Error handling logs: {e}")
                say(text=f":x: Error processing logs: {str(e)}")

        @self.app.action("get_status")
        def handle_status(ack, body, say):
            ack()
            try:
                action_value = json.loads(body['actions'][0]['value'])
                namespace = action_value['namespace']
                pod_name = action_value['pod_name']
                
                message_ts = body['container']['message_ts']
                
                if message_ts in self.active_messages:
                    del self.active_messages[message_ts]
                
                success, status = self.k8s_watcher.get_pod_status(namespace, pod_name)
                
                if success:
                    status_text = f"*Pod Status: {pod_name}*\n"
                    status_text += f"• Phase: {status.get('phase', 'Unknown')}\n"
                    status_text += f"• Pod IP: {status.get('pod_ip', 'N/A')}\n"
                    status_text += f"• Host IP: {status.get('host_ip', 'N/A')}\n"
                    status_text += f"• Conditions: {', '.join(status.get('conditions', []))}"
                    
                    say(
                        text=status_text,
                        thread_ts=message_ts
                    )
                else:
                    say(
                        text=f":x: Failed to get status for *{pod_name}*: {status}",
                        thread_ts=message_ts
                    )
            except Exception as e:
                self.logger.error(f"Error handling status: {e}")

    def _chunk_logs(self, logs, max_length=3000):
        chunks = []
        current_chunk = ""
        lines = logs.split('\n')
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += '\n' + line
                else:
                    current_chunk = line
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def send_event(self, event, count=1):
        event_type = event.get('type', 'UNKNOWN')
        obj = event.get('object', {})
        metadata = obj.get('metadata', {})
        namespace = metadata.get('namespace', 'default')
        name = obj.get('involvedObject', {}).get('name', '')
        if not name:
            name = metadata.get('name', 'unknown')
        
        reason = obj.get('reason', 'Unknown')
        message = obj.get('message', 'No message')
        event_time = obj.get('lastTimestamp', obj.get('firstTimestamp', 'Unknown time'))
        
        color = self._get_color_for_event(event_type, reason)
        
        blocks = self._build_event_blocks(event_type, namespace, name, reason, message, event_time, obj, count)
        
        try:
            result = self.app.client.chat_postMessage(
                channel=self.channel_id,
                text=f"K8s Event: {reason} - {name}",
                blocks=blocks,
                username=self.bot_name,
                icon_emoji=self.bot_icon
            )
            
            if result['ok']:
                ts = result['ts']
                self.active_messages[ts] = {
                    'timestamp': time.time(),
                    'namespace': namespace,
                    'pod_name': name
                }
            
            return result
        except SlackApiError as e:
            self.logger.error(f"Error sending message to Slack: {e}")
            return None

    def _get_color_for_event(self, event_type, reason):
        if event_type == 'ERROR' or 'Failed' in reason or 'Error' in reason:
            return '#ff0000'
        elif event_type == 'WARNING' or 'Warning' in reason:
            return '#ffaa00'
        elif event_type == 'NORMAL' or 'Started' in reason or 'Created' in reason:
            return '#00ff00'
        return '#888888'

    def _build_event_blocks(self, event_type, namespace, name, reason, message, event_time, obj, count=1):
        action_value = json.dumps({
            'namespace': namespace,
            'pod_name': name
        })
        
        header_text = f":rotating_light: Kubernetes Event: {reason}"
        if count > 1:
            header_text = f":rotating_light: Kubernetes Event: {reason} (Aggregated {count} times)"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text,
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{event_type}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Namespace:*\n{namespace}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Pod:*\n{name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{event_time}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Message:*\n```{message[:500]}```"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":alarm_clock: *Buttons will expire in 30 seconds"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":repeat: Restart Pod",
                            "emoji": True
                        },
                        "style": "danger",
                        "action_id": "restart_pod",
                        "value": action_value
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":page_facing_up: Get Logs",
                            "emoji": True
                        },
                        "action_id": "get_logs",
                        "value": action_value
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":information_source: Status",
                            "emoji": True
                        },
                        "action_id": "get_status",
                        "value": action_value
                    }
                ]
            }
        ]
        
        return blocks

    def start(self, app_token=None):
        if app_token:
            handler = SocketModeHandler(self.app, app_token)
            handler.start()
        else:
            self.app.start(port=3000)
