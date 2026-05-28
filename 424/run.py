"""
竞品价格监控系统 - 主入口
支持启动Web服务、爬虫任务、代理池刷新等
"""
import sys
import signal
import argparse
from datetime import datetime

from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import (
    FLASK_CONFIG, SCHEDULER_CONFIG, SPIDER_CONFIG, PROXY, LOG_CONFIG
)
from database.models import init_database
from proxy_pool.pool import init_proxy_pool, get_proxy_pool


def setup_logging():
    log_dir = LOG_CONFIG['log_dir']
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stdout,
        level=LOG_CONFIG.get('log_level', 'INFO'),
        format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
    )
    logger.add(
        log_dir / 'app_{time:YYYY-MM-DD}.log',
        level=LOG_CONFIG.get('log_level', 'INFO'),
        rotation=LOG_CONFIG.get('max_size', '10 MB'),
        retention=LOG_CONFIG.get('retention', '30 days'),
        format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
    )


def run_spider(source=None, category=None):
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    logger.info(f"启动爬虫任务, source={source}, category={category}")

    settings = get_project_settings()
    settings.set('LOG_LEVEL', 'INFO')
    settings.set('CONCURRENT_REQUESTS', 16)

    process = CrawlerProcess(settings)
    process.crawl('competitor', source=source, category=category)
    process.start()

    logger.info("爬虫任务完成")


def run_web():
    from web.app import app

    host = FLASK_CONFIG.get('host', '0.0.0.0')
    port = FLASK_CONFIG.get('port', 5000)
    debug = FLASK_CONFIG.get('debug', True)

    logger.info(f"启动Web服务: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


def start_scheduler():
    scheduler = BackgroundScheduler(timezone=SCHEDULER_CONFIG.get('timezone', 'Asia/Shanghai'))
    scheduler.configure(job_defaults=SCHEDULER_CONFIG.get('job_defaults', {}))

    for comp in SPIDER_CONFIG.get('competitors', []):
        if not comp.get('enabled', True):
            continue

        interval = comp.get('schedule_interval', 1800)
        scheduler.add_job(
            run_spider,
            trigger=IntervalTrigger(seconds=interval),
            args=[comp['name']],
            id=f"spider_{comp['name']}",
            name=f"爬虫-{comp['name']}",
            replace_existing=True,
        )
        logger.info(f"已调度爬虫任务: {comp['name']}, 间隔: {interval}秒")

    if PROXY.get('enable', False):
        scheduler.add_job(
            refresh_proxy_pool,
            trigger=IntervalTrigger(seconds=PROXY.get('refresh_interval', 300)),
            id='proxy_refresh',
            name='代理池刷新',
            replace_existing=True,
        )
        logger.info("已调度代理池刷新任务")

    scheduler.start()
    logger.info("调度器已启动")

    return scheduler


def refresh_proxy_pool():
    pool = get_proxy_pool()
    if pool:
        pool.refresh()
        logger.info(f"代理池刷新完成, 当前大小: {pool.size}")


def init_system():
    setup_logging()

    logger.info("=" * 60)
    logger.info("竞品价格监控系统启动中...")
    logger.info("=" * 60)

    logger.info("初始化数据库...")
    init_database()
    logger.info("数据库初始化完成")

    if PROXY.get('enable', False):
        logger.info("初始化代理池...")
        init_proxy_pool()
        pool = get_proxy_pool()
        pool.refresh(force=True)
        logger.info(f"代理池初始化完成, 当前代理数: {pool.size}")

    logger.info("系统初始化完成")


def main():
    parser = argparse.ArgumentParser(
        description='竞品价格监控系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python run.py              # 启动Web服务和定时任务
  python run.py web          # 仅启动Web服务
  python run.py spider       # 运行一次爬虫任务
  python run.py spider -s taobao  # 运行指定源的爬虫
  python run.py scheduler    # 仅启动调度器
  python run.py proxy        # 刷新代理池
        ''',
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='all',
        choices=['all', 'web', 'spider', 'scheduler', 'proxy', 'init'],
        help='运行模式 (默认: all)',
    )
    parser.add_argument('-s', '--source', help='指定竞品源')
    parser.add_argument('-c', '--category', help='指定商品分类')
    parser.add_argument('-p', '--port', type=int, help='Web服务端口')
    parser.add_argument('--host', help='Web服务主机')

    args = parser.parse_args()

    if args.port:
        FLASK_CONFIG['port'] = args.port
    if args.host:
        FLASK_CONFIG['host'] = args.host

    init_system()

    if args.command == 'init':
        logger.info("系统初始化完成")
        return

    if args.command == 'web':
        run_web()

    elif args.command == 'spider':
        run_spider(source=args.source, category=args.category)

    elif args.command == 'scheduler':
        scheduler = start_scheduler()
        try:
            signal.pause()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            logger.info("调度器已停止")

    elif args.command == 'proxy':
        refresh_proxy_pool()

    elif args.command == 'all':
        scheduler = start_scheduler()

        try:
            run_web()
        except KeyboardInterrupt:
            scheduler.shutdown()
            logger.info("系统已停止")


if __name__ == '__main__':
    main()