#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import configparser
import argparse
import logging
import subprocess
from datetime import datetime

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
except ImportError:
    print('Error: APScheduler is required. Please install it with: pip install apscheduler')
    sys.exit(1)

try:
    import pytz
except ImportError:
    print('Error: pytz is required. Please install it with: pip install pytz')
    sys.exit(1)

def setup_logging(log_file='scheduler.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('scheduler')


def load_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    return config


def get_schedule_jobs(config):
    jobs = []
    for section in config.sections():
        if section.startswith('schedule:'):
            job_name = section.split(':', 1)[1]
            if config.getboolean(section, 'enabled', fallback=True):
                jobs.append(dict(config[section]))
    return jobs


def run_backup_task(instances, backup_type, config_file='config.ini'):
    logger = logging.getLogger('scheduler')
    logger.info(f'Running backup task: type={backup_type}, instances={instances}')
    
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'backup.py')
        cmd = [sys.executable, script_path, '--type', backup_type, '--config', config_file]
        
        if instances and 'all' not in instances:
            instance_list = [i.strip() for i in instances.split(',')]
            for instance in instance_list:
                cmd.extend(['--instance', instance])
        
        logger.info(f'Executing: {" ".join(cmd)}')
        
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.stdout:
            logger.info(f'Backup output: {result.stdout.decode("utf-8", errors="ignore")}')
        
        logger.info(f'Backup task completed successfully')
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f'Backup task failed: {e.stderr.decode("utf-8", errors="ignore")}')
        return False
    except Exception as e:
        logger.error(f'Backup task error: {e}')
        return False


def run_upload_task(instances, config_file='config.ini'):
    logger = logging.getLogger('scheduler')
    logger.info(f'Running upload task: instances={instances}')
    
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'upload.py')
        cmd = [sys.executable, script_path, '--all-backups', '--config', config_file]
        
        logger.info(f'Executing: {" ".join(cmd)}')
        
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.stdout:
            logger.info(f'Upload output: {result.stdout.decode("utf-8", errors="ignore")}')
        
        logger.info(f'Upload task completed successfully')
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f'Upload task failed: {e.stderr.decode("utf-8", errors="ignore")}')
        return False
    except Exception as e:
        logger.error(f'Upload task error: {e}')
        return False


def run_encrypt_task(instances, config_file='config.ini'):
    logger = logging.getLogger('scheduler')
    logger.info(f'Running encrypt task: instances={instances}')
    
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'encrypt.py')
        cmd = [sys.executable, script_path, 'encrypt', '--all-backups', '--config', config_file, '--delete-original']
        
        logger.info(f'Executing: {" ".join(cmd)}')
        
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.stdout:
            logger.info(f'Encrypt output: {result.stdout.decode("utf-8", errors="ignore")}')
        
        logger.info(f'Encrypt task completed successfully')
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f'Encrypt task failed: {e.stderr.decode("utf-8", errors="ignore")}')
        return False
    except Exception as e:
        logger.error(f'Encrypt task error: {e}')
        return False


def create_trigger(job_config, timezone):
    trigger_type = job_config.get('trigger', 'cron').lower()
    
    if trigger_type == 'cron':
        cron_kwargs = {}
        
        if 'year' in job_config:
            cron_kwargs['year'] = job_config['year']
        if 'month' in job_config:
            cron_kwargs['month'] = job_config['month']
        if 'day' in job_config:
            cron_kwargs['day'] = job_config['day']
        if 'week' in job_config:
            cron_kwargs['week'] = job_config['week']
        if 'day_of_week' in job_config:
            cron_kwargs['day_of_week'] = job_config['day_of_week']
        if 'hour' in job_config:
            cron_kwargs['hour'] = job_config['hour']
        if 'minute' in job_config:
            cron_kwargs['minute'] = job_config['minute']
        if 'second' in job_config:
            cron_kwargs['second'] = job_config['second']
        
        if timezone:
            cron_kwargs['timezone'] = timezone
        
        return CronTrigger(**cron_kwargs)
    
    elif trigger_type == 'interval':
        interval_kwargs = {}
        
        if 'weeks' in job_config:
            interval_kwargs['weeks'] = int(job_config['weeks'])
        if 'days' in job_config:
            interval_kwargs['days'] = int(job_config['days'])
        if 'hours' in job_config:
            interval_kwargs['hours'] = int(job_config['hours'])
        if 'minutes' in job_config:
            interval_kwargs['minutes'] = int(job_config['minutes'])
        if 'seconds' in job_config:
            interval_kwargs['seconds'] = int(job_config['seconds'])
        
        if not interval_kwargs:
            interval_kwargs['days'] = 1
        
        return IntervalTrigger(**interval_kwargs)
    
    elif trigger_type == 'date':
        run_date = job_config.get('run_date')
        if run_date:
            return DateTrigger(run_date=run_date)
        else:
            return DateTrigger(run_date=datetime.now())
    
    else:
        raise ValueError(f'Unknown trigger type: {trigger_type}')


def create_job_function(job_config, config_file):
    task = job_config.get('task', 'backup').lower()
    instances = job_config.get('instances', 'all')
    backup_type = job_config.get('type', 'full')
    
    if task == 'backup':
        return lambda: run_backup_task(instances, backup_type, config_file)
    elif task == 'upload':
        return lambda: run_upload_task(instances, config_file)
    elif task == 'encrypt':
        return lambda: run_encrypt_task(instances, config_file)
    else:
        raise ValueError(f'Unknown task type: {task}')


def main():
    parser = argparse.ArgumentParser(description='Database Backup Scheduler')
    parser.add_argument('--config', default='config.ini', help='Configuration file path')
    parser.add_argument('--run-once', action='store_true', help='Run all jobs once and exit')
    parser.add_argument('--list-jobs', action='store_true', help='List all scheduled jobs')
    
    args = parser.parse_args()
    
    try:
        config = load_config(args.config)
        scheduler_config = config.get('scheduler', {})
        log_file = scheduler_config.get('log_file', 'scheduler.log')
        timezone_str = scheduler_config.get('timezone', 'Asia/Shanghai')
        
        logger = setup_logging(log_file)
        logger.info('=' * 60)
        logger.info('Starting Database Backup Scheduler')
        logger.info(f'Configuration file: {args.config}')
        logger.info(f'Timezone: {timezone_str}')
        logger.info('=' * 60)
        
        timezone = None
        try:
            timezone = pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f'Unknown timezone: {timezone_str}, using default')
            timezone = None
        
        jobs = get_schedule_jobs(config)
        
        if args.list_jobs:
            print('Scheduled jobs:')
            for job in jobs:
                job_name = job.get('job_name', 'unnamed')
                task = job.get('task', 'backup')
                trigger = job.get('trigger', 'cron')
                enabled = 'Enabled' if config.getboolean(f'schedule:{job_name}', 'enabled', fallback=True) else 'Disabled'
                print(f'  - {job_name} [{task}/{trigger}] - {enabled}')
            return
        
        if not jobs:
            logger.warning('No scheduled jobs found in configuration')
            return
        
        scheduler = BackgroundScheduler(timezone=timezone)
        
        for job_config in jobs:
            job_name = job_config.get('job_name', 'unnamed')
            logger.info(f'Configuring job: {job_name}')
            
            try:
                trigger = create_trigger(job_config, timezone)
                job_func = create_job_function(job_config, args.config)
                
                scheduler.add_job(
                    job_func,
                    trigger=trigger,
                    id=job_name,
                    name=job_name,
                    replace_existing=True,
                    misfire_grace_time=3600,
                    coalesce=True
                )
                
                logger.info(f'Job added: {job_name} - next run: {trigger.get_next_fire_time(None, datetime.now(timezone)) if hasattr(trigger, "get_next_fire_time") else "N/A"}')
            except Exception as e:
                logger.error(f'Failed to configure job {job_name}: {e}')
        
        if args.run_once:
            logger.info('Running all jobs once (run-once mode)...')
            scheduler.start()
            
            import time
            time.sleep(5)
            
            for job in scheduler.get_jobs():
                logger.info(f'Triggering job: {job.id}')
                scheduler.modify_job(job.id, next_run_time=datetime.now(timezone))
            
            time.sleep(60)
            logger.info('Run-once mode completed, shutting down...')
            scheduler.shutdown(wait=True)
        else:
            logger.info('Starting scheduler...')
            scheduler.start()
            logger.info('Scheduler running. Press Ctrl+C to exit.')
            
            try:
                while True:
                    import time
                    time.sleep(3600)
            except (KeyboardInterrupt, SystemExit):
                logger.info('Shutdown signal received...')
                scheduler.shutdown(wait=True)
                logger.info('Scheduler stopped')
        
    except Exception as e:
        logger.error(f'Scheduler error: {e}', exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
