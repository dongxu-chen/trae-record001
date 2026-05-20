#!/usr/bin/env python3
import boto3
import argparse
import datetime
import csv
import re
import json
import requests
from dateutil.relativedelta import relativedelta
from collections import defaultdict


INSTANCE_FAMILY_COMPATIBILITY = {
    't2': ['t2', 't3', 't3a'],
    't3': ['t2', 't3', 't3a'],
    't3a': ['t2', 't3', 't3a'],
    'm4': ['m4', 'm5', 'm5a', 'm5n'],
    'm5': ['m4', 'm5', 'm5a', 'm5n'],
    'm5a': ['m4', 'm5', 'm5a', 'm5n'],
    'c4': ['c4', 'c5', 'c5a', 'c5n'],
    'c5': ['c4', 'c5', 'c5a', 'c5n'],
    'c5a': ['c4', 'c5', 'c5a', 'c5n'],
    'r4': ['r4', 'r5', 'r5a', 'r5n'],
    'r5': ['r4', 'r5', 'r5a', 'r5n'],
    'r5a': ['r4', 'r5', 'r5a', 'r5n'],
}


class AlertSender:
    def __init__(self, slack_webhook=None, dingtalk_webhook=None):
        self.slack_webhook = slack_webhook
        self.dingtalk_webhook = dingtalk_webhook

    def send_slack_alert(self, title, message, color='warning'):
        if not self.slack_webhook:
            return False
        
        color_map = {
            'danger': '#ff0000',
            'warning': '#ff9900',
            'good': '#00cc00',
            'info': '#0099ff'
        }
        
        payload = {
            'attachments': [{
                'title': title,
                'text': message,
                'color': color_map.get(color, color),
                'ts': int(datetime.datetime.now().timestamp())
            }]
        }
        
        try:
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Warning: Failed to send Slack alert: {e}")
            return False

    def send_dingtalk_alert(self, title, message, level='warning'):
        if not self.dingtalk_webhook:
            return False
        
        level_emoji = {
            'danger': '🔴',
            'warning': '⚠️',
            'good': '✅',
            'info': 'ℹ️'
        }
        
        emoji = level_emoji.get(level, '')
        
        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'title': title,
                'text': f"{emoji} **{title}**\n\n{message}"
            }
        }
        
        try:
            response = requests.post(self.dingtalk_webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Warning: Failed to send DingTalk alert: {e}")
            return False

    def send_alert(self, title, message, level='warning'):
        results = []
        if self.slack_webhook:
            results.append(('Slack', self.send_slack_alert(title, message, level)))
        if self.dingtalk_webhook:
            results.append(('DingTalk', self.send_dingtalk_alert(title, message, level)))
        return results


class CloudCostOptimizer:
    def __init__(self, region='us-east-1', role_name='OrganizationAccountAccessRole', 
                 monthly_budget=None, required_tags=None, 
                 slack_webhook=None, dingtalk_webhook=None):
        self.region = region
        self.role_name = role_name
        self.monthly_budget = monthly_budget
        self.required_tags = required_tags or ['Environment', 'Project', 'Owner']
        self.alert_sender = AlertSender(slack_webhook, dingtalk_webhook)
        
        self.session = boto3.Session(region_name=region)
        self.ce_client = self.session.client('ce', region_name=region)
        self.ec2_client = self.session.client('ec2', region_name=region)
        self.rds_client = self.session.client('rds', region_name=region)
        self.pricing_client = self.session.client('pricing', region_name='us-east-1')
        self.org_client = self.session.client('organizations', region_name='us-east-1')

    def assume_role(self, account_id, role_name=None):
        role_arn = f'arn:aws:iam::{account_id}:role/{role_name or self.role_name}'
        try:
            sts_client = self.session.client('sts')
            response = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=f'CostOptimizer-{account_id}'
            )
            credentials = response['Credentials']
            return boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=self.region
            )
        except Exception as e:
            print(f"Warning: Could not assume role for account {account_id}: {e}")
            return None

    def get_all_accounts(self):
        accounts = []
        try:
            paginator = self.org_client.get_paginator('list_accounts')
            for page in paginator.paginate():
                for account in page['Accounts']:
                    if account['Status'] == 'ACTIVE':
                        accounts.append({
                            'Id': account['Id'],
                            'Name': account['Name'],
                            'Email': account['Email']
                        })
        except Exception as e:
            print(f"Warning: Could not list organization accounts: {e}")
            print("Falling back to current account only")
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            accounts.append({
                'Id': identity['Account'],
                'Name': 'Current Account',
                'Email': identity['Arn']
            })
        return accounts

    def get_instance_family(self, instance_type):
        match = re.match(r'^([a-z]+[0-9]+[a-z]*)', instance_type.lower())
        return match.group(1) if match else None

    def get_compatible_instance_families(self, instance_type):
        family = self.get_instance_family(instance_type)
        if family and family in INSTANCE_FAMILY_COMPATIBILITY:
            return INSTANCE_FAMILY_COMPATIBILITY[family]
        return [family] if family else []

    def get_monthly_cost(self, start_date, end_date, session=None):
        ce_client = session.client('ce', region_name=self.region) if session else self.ce_client
        try:
            response = ce_client.get_cost_and_usage(
                TimePeriod={'Start': start_date.strftime('%Y-%m-%d'), 'End': end_date.strftime('%Y-%m-%d')},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )
            total_cost = 0.0
            for result in response.get('ResultsByTime', []):
                total_cost += float(result['Total']['UnblendedCost']['Amount'])
            return total_cost
        except Exception as e:
            print(f"Warning: Could not fetch monthly cost: {e}")
            return 0.0

    def check_budget_threshold(self, current_cost, monthly_budget):
        alerts = []
        if not monthly_budget or monthly_budget <= 0:
            return alerts
        
        usage_percent = (current_cost / monthly_budget) * 100
        
        if usage_percent >= 100:
            alerts.append({
                'level': 'danger',
                'title': '预算超额告警',
                'message': f'月度预算已超额！\n预算: ${monthly_budget:.2f}\n当前花费: ${current_cost:.2f}\n使用率: {usage_percent:.1f}%'
            })
        elif usage_percent >= 80:
            alerts.append({
                'level': 'warning',
                'title': '预算预警',
                'message': f'月度预算已使用超过80%！\n预算: ${monthly_budget:.2f}\n当前花费: ${current_cost:.2f}\n使用率: {usage_percent:.1f}%'
            })
        
        return alerts

    def detect_cost_spikes(self, current_month_cost, previous_month_cost, threshold_percent=50):
        alerts = []
        if previous_month_cost <= 0:
            return alerts
        
        increase_percent = ((current_month_cost - previous_month_cost) / previous_month_cost) * 100
        
        if increase_percent >= threshold_percent:
            alerts.append({
                'level': 'danger',
                'title': '费用突增告警',
                'message': f'检测到费用异常增长！\n上月花费: ${previous_month_cost:.2f}\n本月花费: ${current_month_cost:.2f}\n环比增长: {increase_percent:.1f}%'
            })
        
        return alerts

    def get_cost_and_usage(self, start_date=None, end_date=None, tags=None, session=None):
        ce_client = session.client('ce', region_name=self.region) if session else self.ce_client
        if not start_date:
            end_date = datetime.date.today()
            start_date = end_date - relativedelta(months=1)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        group_by = [
            {'Type': 'DIMENSION', 'Key': 'SERVICE'},
            {'Type': 'DIMENSION', 'Key': 'INSTANCE_TYPE'}
        ]
        
        if tags:
            for tag in tags:
                group_by.append({'Type': 'TAG', 'Key': tag})

        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date_str, 'End': end_date_str},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=group_by
        )
        return response

    def aggregate_cost_by_tags(self, cost_data, tags):
        aggregated = defaultdict(lambda: defaultdict(float))
        
        for result in cost_data.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                keys = group['Keys']
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                
                tag_values = {}
                for i, tag in enumerate(tags):
                    tag_key = f'Tag-{tag}$'
                    for key in keys:
                        if key.startswith(tag_key):
                            tag_values[tag] = key[len(tag_key):] or 'untagged'
                
                key_tuple = tuple(tag_values.get(tag, 'untagged') for tag in tags)
                service = keys[0] if keys else 'unknown'
                aggregated[key_tuple][service] += cost
        
        return aggregated

    def check_resource_tags(self, instances):
        untagged_resources = []
        for instance in instances:
            tags = instance.get('Tags', {})
            missing_tags = [tag for tag in self.required_tags if tag not in tags]
            
            if missing_tags:
                untagged_resources.append({
                    'ResourceId': instance['InstanceId'],
                    'ResourceType': 'EC2',
                    'InstanceType': instance['InstanceType'],
                    'Region': instance['Region'],
                    'AccountId': instance.get('AccountId', 'N/A'),
                    'MissingTags': ', '.join(missing_tags),
                    'ExistingTags': ', '.join([f"{k}={v}" for k, v in tags.items()])
                })
        
        return untagged_resources

    def get_running_ec2_instances(self, session=None):
        ec2_client = session.client('ec2', region_name=self.region) if session else self.ec2_client
        instances = []
        account_id = None
        
        try:
            if session:
                sts = session.client('sts')
                account_id = sts.get_caller_identity()['Account']
            
            paginator = ec2_client.get_paginator('describe_instances')
            for page in paginator.paginate(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]):
                for reservation in page['Reservations']:
                    for instance in reservation['Instances']:
                        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                        instances.append({
                            'InstanceId': instance['InstanceId'],
                            'InstanceType': instance['InstanceType'],
                            'Region': self.region,
                            'Platform': instance.get('Platform', 'Linux/UNIX'),
                            'Tags': tags,
                            'AccountId': account_id
                        })
        except Exception as e:
            print(f"Warning: Error fetching EC2 instances: {e}")
        return instances

    def get_running_rds_instances(self, session=None):
        rds_client = session.client('rds', region_name=self.region) if session else self.rds_client
        instances = []
        try:
            paginator = rds_client.get_paginator('describe_db_instances')
            for page in paginator.paginate():
                for db_instance in page['DBInstances']:
                    if db_instance['DBInstanceStatus'] == 'available':
                        instances.append({
                            'DBInstanceIdentifier': db_instance['DBInstanceIdentifier'],
                            'DBInstanceClass': db_instance['DBInstanceClass'],
                            'Engine': db_instance['Engine'],
                            'Region': self.region
                        })
        except Exception as e:
            print(f"Warning: Error fetching RDS instances: {e}")
        return instances

    def get_ec2_ondemand_price(self, instance_type, platform='Linux/UNIX'):
        try:
            region_mapping = {
                'us-east-1': 'US East (N. Virginia)',
                'us-west-2': 'US West (Oregon)',
                'eu-west-1': 'EU (Ireland)',
                'ap-southeast-1': 'Asia Pacific (Singapore)'
            }
            location = region_mapping.get(self.region, 'US East (N. Virginia)')
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
                ],
                MaxResults=1
            )
            if response['PriceList']:
                price_item = json.loads(response['PriceList'][0])
                for term in price_item['terms']['OnDemand'].values():
                    for price_dimension in term['priceDimensions'].values():
                        return float(price_dimension['pricePerUnit']['USD'])
        except Exception as e:
            print(f"Warning: Error getting EC2 price for {instance_type}: {e}")
        return 0.0

    def get_ec2_reserved_price(self, instance_type, offering_type='All Upfront', duration=36):
        try:
            response = self.ec2_client.describe_reserved_instances_offerings(
                InstanceType=instance_type,
                OfferingType=offering_type,
                ProductDescription='Linux/UNIX',
                Duration=duration*30*24*3600
            )
            if response['ReservedInstancesOfferings']:
                offering = response['ReservedInstancesOfferings'][0]
                upfront_cost = float(offering['FixedPrice'])
                hourly_cost = float(offering['UsagePrice'])
                return upfront_cost, hourly_cost
        except Exception as e:
            print(f"Warning: Error getting RI price for {instance_type}: {e}")
        return 0.0, 0.0

    def find_best_ri_match(self, instance_type):
        compatible_families = self.get_compatible_instance_families(instance_type)
        size = instance_type.split('.')[-1] if '.' in instance_type else 'large'
        
        best_price = None
        best_type = None
        best_upfront = None
        best_hourly = None
        
        for family in compatible_families:
            test_type = f'{family}.{size}'
            upfront, hourly = self.get_ec2_reserved_price(test_type)
            if hourly > 0:
                total_monthly = upfront / 36 + hourly * 730
                if best_price is None or total_monthly < best_price:
                    best_price = total_monthly
                    best_type = test_type
                    best_upfront = upfront
                    best_hourly = hourly
        
        if best_type:
            return best_type, best_upfront, best_hourly
        return instance_type, 0.0, 0.0

    def calculate_cost_comparison(self, instances):
        comparison_data = []
        instance_counts = defaultdict(lambda: {'count': 0, 'instances': []})
        
        for instance in instances:
            instance_type = instance['InstanceType']
            instance_counts[instance_type]['count'] += 1
            instance_counts[instance_type]['instances'].append(instance)

        for instance_type, data in instance_counts.items():
            count = data['count']
            ondemand_hourly = self.get_ec2_ondemand_price(instance_type)
            best_ri_type, ri_upfront, ri_hourly = self.find_best_ri_match(instance_type)
            
            if ondemand_hourly > 0:
                monthly_ondemand = ondemand_hourly * 730 * count
                monthly_ri = (ri_upfront / 36 + ri_hourly * 730) * count
                monthly_savings = monthly_ondemand - monthly_ri
                savings_percent = (monthly_savings / monthly_ondemand) * 100 if monthly_ondemand > 0 else 0

                comparison_data.append({
                    'InstanceType': instance_type,
                    'InstanceCount': count,
                    'BestRIType': best_ri_type,
                    'OnDemandHourly': ondemand_hourly,
                    'OnDemandMonthly': monthly_ondemand,
                    'RIUpfront': ri_upfront,
                    'RIHourly': ri_hourly,
                    'RIMonthly': monthly_ri,
                    'MonthlySavings': monthly_savings,
                    'SavingsPercent': savings_percent
                })

        return comparison_data

    def recommend_ri_purchases(self, comparison_data):
        recommendations = []
        for item in comparison_data:
            if item['SavingsPercent'] > 20 and item['MonthlySavings'] > 10:
                payback_months = item['RIUpfront'] / item['MonthlySavings'] if item['MonthlySavings'] > 0 else float('inf')
                recommendations.append({
                    'InstanceType': item['InstanceType'],
                    'BestRIType': item['BestRIType'],
                    'RecommendedCount': item['InstanceCount'],
                    'MonthlySavings': item['MonthlySavings'],
                    'SavingsPercent': item['SavingsPercent'],
                    'PaybackMonths': payback_months,
                    'Priority': 'High' if payback_months < 6 else 'Medium' if payback_months < 12 else 'Low'
                })
        
        recommendations.sort(key=lambda x: x['MonthlySavings'], reverse=True)
        return recommendations

    def generate_csv_report(self, cost_data, recommendations, tag_aggregated=None, tags=None, 
                           untagged_resources=None, budget_alerts=None, spike_alerts=None, 
                           filename='cloud_cost_report.csv'):
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            if budget_alerts or spike_alerts:
                writer.writerow(['=== 告警信息 ==='])
                writer.writerow(['告警级别', '告警标题', '告警内容'])
                for alert in budget_alerts + spike_alerts:
                    writer.writerow([alert['level'].upper(), alert['title'], alert['message'].replace('\n', '; ')])
                writer.writerow([])
            
            if untagged_resources:
                writer.writerow(['=== 资源标签治理报告 ==='])
                writer.writerow(['资源ID', '资源类型', '实例类型', '区域', '账号ID', '缺失标签', '现有标签'])
                for resource in untagged_resources:
                    writer.writerow([
                        resource['ResourceId'],
                        resource['ResourceType'],
                        resource['InstanceType'],
                        resource['Region'],
                        resource['AccountId'],
                        resource['MissingTags'],
                        resource['ExistingTags']
                    ])
                writer.writerow(['未打标资源总数', len(untagged_resources)])
                writer.writerow([])
            
            writer.writerow(['=== EC2 Cost Comparison (On-Demand vs Reserved) ==='])
            writer.writerow(['InstanceType', 'Count', 'Best RI Type', 'OnDemand Hourly', 'OnDemand Monthly', 
                           'RI Upfront', 'RI Hourly', 'RI Monthly', 'Monthly Savings', 'Savings %'])
            
            for item in cost_data:
                writer.writerow([
                    item['InstanceType'],
                    item['InstanceCount'],
                    item['BestRIType'],
                    f"${item['OnDemandHourly']:.4f}",
                    f"${item['OnDemandMonthly']:.2f}",
                    f"${item['RIUpfront']:.2f}",
                    f"${item['RIHourly']:.4f}",
                    f"${item['RIMonthly']:.2f}",
                    f"${item['MonthlySavings']:.2f}",
                    f"{item['SavingsPercent']:.1f}%"
                ])
            
            writer.writerow([])
            writer.writerow(['=== Recommended Reserved Instance Purchases ==='])
            writer.writerow(['InstanceType', 'Best RI Type', 'Recommended Count', 'Monthly Savings', 'Savings %', 'Payback Months', 'Priority'])
            
            total_savings = 0
            for rec in recommendations:
                writer.writerow([
                    rec['InstanceType'],
                    rec['BestRIType'],
                    rec['RecommendedCount'],
                    f"${rec['MonthlySavings']:.2f}",
                    f"{rec['SavingsPercent']:.1f}%",
                    f"{rec['PaybackMonths']:.1f}",
                    rec['Priority']
                ])
                total_savings += rec['MonthlySavings']
            
            writer.writerow([])
            writer.writerow(['Total Estimated Monthly Savings', f"${total_savings:.2f}"])
            
            if tag_aggregated and tags:
                writer.writerow([])
                writer.writerow([f'=== Cost Aggregation by Tags: {", ".join(tags)} ==='])
                header = list(tags) + ['Service', 'Cost']
                writer.writerow(header)
                
                for tag_values, services in tag_aggregated.items():
                    for service, cost in services.items():
                        row = list(tag_values) + [service, f"${cost:.2f}"]
                        writer.writerow(row)
        
        return filename

    def run_analysis(self, start_date=None, end_date=None, tags=None, cross_account=False):
        print("=== Cloud Cost Optimizer ===")
        print(f"Region: {self.region}")
        print()

        all_instances = []
        tag_aggregated = defaultdict(lambda: defaultdict(float))
        all_alerts = []
        total_current_cost = 0.0
        total_previous_cost = 0.0

        if cross_account:
            print("Fetching organization accounts...")
            accounts = self.get_all_accounts()
            print(f"Found {len(accounts)} active accounts")
            print()

            for account in accounts:
                account_id = account['Id']
                account_name = account['Name']
                print(f"Processing account: {account_name} ({account_id})")
                
                session = self.assume_role(account_id)
                if session:
                    instances = self.get_running_ec2_instances(session)
                    all_instances.extend(instances)
                    print(f"  Found {len(instances)} running EC2 instances")
                    
                    end = end_date or datetime.date.today()
                    start = start_date or end - relativedelta(months=1)
                    prev_start = start - relativedelta(months=1)
                    prev_end = start
                    
                    current_cost = self.get_monthly_cost(start, end, session)
                    previous_cost = self.get_monthly_cost(prev_start, prev_end, session)
                    total_current_cost += current_cost
                    total_previous_cost += previous_cost
                    
                    print(f"  Current month cost: ${current_cost:.2f}, Previous month cost: ${previous_cost:.2f}")
                    
                    if tags:
                        try:
                            cost_data = self.get_cost_and_usage(start_date, end_date, tags, session)
                            aggregated = self.aggregate_cost_by_tags(cost_data, tags)
                            for tag_values, services in aggregated.items():
                                for service, cost in services.items():
                                    tag_aggregated[tag_values][service] += cost
                        except Exception as e:
                            print(f"  Warning: Could not fetch cost data for account {account_id}: {e}")
                else:
                    print(f"  Skipping account {account_id} - could not assume role")
                print()
        else:
            print("Fetching running EC2 instances (current account only)...")
            all_instances = self.get_running_ec2_instances()
            print(f"Found {len(all_instances)} running EC2 instances")
            
            end = end_date or datetime.date.today()
            start = start_date or end - relativedelta(months=1)
            prev_start = start - relativedelta(months=1)
            prev_end = start
            
            total_current_cost = self.get_monthly_cost(start, end)
            total_previous_cost = self.get_monthly_cost(prev_start, prev_end)
            print(f"Current month cost: ${total_current_cost:.2f}")
            print(f"Previous month cost: ${total_previous_cost:.2f}")
            
            if tags:
                print(f"Aggregating costs by tags: {tags}")
                cost_data = self.get_cost_and_usage(start_date, end_date, tags)
                tag_aggregated = self.aggregate_cost_by_tags(cost_data, tags)

        print()
        print("=== 预算与异常检测 ===")
        budget_alerts = []
        spike_alerts = []
        
        if self.monthly_budget:
            print(f"Monthly budget set to: ${self.monthly_budget:.2f}")
            budget_alerts = self.check_budget_threshold(total_current_cost, self.monthly_budget)
            for alert in budget_alerts:
                print(f"  [{alert['level'].upper()}] {alert['title']}")
        
        spike_alerts = self.detect_cost_spikes(total_current_cost, total_previous_cost)
        for alert in spike_alerts:
            print(f"  [{alert['level'].upper()}] {alert['title']}")
        
        all_alerts = budget_alerts + spike_alerts
        
        if all_alerts and (self.alert_sender.slack_webhook or self.alert_sender.dingtalk_webhook):
            print()
            print("Sending alerts...")
            for alert in all_alerts:
                results = self.alert_sender.send_alert(alert['title'], alert['message'], alert['level'])
                for channel, success in results:
                    print(f"  {channel} alert sent: {'Success' if success else 'Failed'}")

        print()
        print("=== 资源标签治理 ===")
        print(f"Required tags: {self.required_tags}")
        untagged_resources = self.check_resource_tags(all_instances)
        print(f"Found {len(untagged_resources)} untagged resources")

        print()
        print("Calculating cost comparison...")
        cost_comparison = self.calculate_cost_comparison(all_instances)

        print("Generating RI purchase recommendations (with family compatibility)...")
        recommendations = self.recommend_ri_purchases(cost_comparison)

        print("Generating CSV report...")
        report_file = self.generate_csv_report(
            cost_comparison, 
            recommendations, 
            tag_aggregated if tags else None, 
            tags,
            untagged_resources,
            budget_alerts,
            spike_alerts
        )

        print()
        print("=== Analysis Complete ===")
        print(f"Report saved to: {report_file}")
        print()
        print("Cost Summary:")
        total_ondemand = sum(item['OnDemandMonthly'] for item in cost_comparison)
        total_ri = sum(item['RIMonthly'] for item in cost_comparison)
        total_savings = sum(rec['MonthlySavings'] for rec in recommendations)
        
        print(f"Total Current Month Cost: ${total_current_cost:.2f}")
        print(f"Total Previous Month Cost: ${total_previous_cost:.2f}")
        print(f"Total On-Demand Monthly Cost (EC2 only): ${total_ondemand:.2f}")
        print(f"Total RI Monthly Cost (EC2 only): ${total_ri:.2f}")
        print(f"Potential Monthly Savings: ${total_savings:.2f}")
        print(f"Savings Percentage: {(total_savings/total_ondemand*100):.1f}%" if total_ondemand > 0 else "0%")

        return cost_comparison, recommendations, tag_aggregated, all_alerts, untagged_resources


def parse_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def main():
    parser = argparse.ArgumentParser(description='AWS Cloud Cost Optimizer with Budget Alerts')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--start-date', type=parse_date, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=parse_date, help='End date (YYYY-MM-DD)')
    parser.add_argument('--tags', nargs='+', default=['Environment', 'Project', 'Owner'], 
                        help='Tags to aggregate costs by (default: Environment Project Owner)')
    parser.add_argument('--cross-account', action='store_true', 
                        help='Enable cross-account scanning (requires organization access)')
    parser.add_argument('--role-name', default='OrganizationAccountAccessRole',
                        help='Role name to assume for cross-account access (default: OrganizationAccountAccessRole)')
    parser.add_argument('--output', default='cloud_cost_report.csv',
                        help='Output CSV file name (default: cloud_cost_report.csv)')
    parser.add_argument('--monthly-budget', type=float, default=None,
                        help='Monthly budget threshold in USD (enables budget alerts)')
    parser.add_argument('--required-tags', nargs='+', default=['Environment', 'Project', 'Owner'],
                        help='Tags required for resources (default: Environment Project Owner)')
    parser.add_argument('--slack-webhook', default=None,
                        help='Slack webhook URL for sending alerts')
    parser.add_argument('--dingtalk-webhook', default=None,
                        help='DingTalk webhook URL for sending alerts')
    parser.add_argument('--spike-threshold', type=float, default=50,
                        help='Cost spike threshold percentage (default: 50)')
    
    args = parser.parse_args()
    
    if args.start_date and not args.end_date:
        args.end_date = datetime.date.today()
    elif args.end_date and not args.start_date:
        args.start_date = args.end_date - relativedelta(months=1)

    optimizer = CloudCostOptimizer(
        region=args.region, 
        role_name=args.role_name,
        monthly_budget=args.monthly_budget,
        required_tags=args.required_tags,
        slack_webhook=args.slack_webhook,
        dingtalk_webhook=args.dingtalk_webhook
    )
    
    optimizer.run_analysis(
        start_date=args.start_date,
        end_date=args.end_date,
        tags=args.tags,
        cross_account=args.cross_account
    )


if __name__ == '__main__':
    main()
