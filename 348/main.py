import logging
import sys
import os
import time
import json
from typing import Dict, Any, Optional

from config import load_config, AppConfig
from core.db_driver import create_driver
from core.backup_restore import BackupRestoreManager
from core.validation_engine import ValidationEngine, CheckStatus
from core.data_diff import DataDiffAnalyzer
from core.quick_validate import QuickValidator
from core.recovery_drill import RecoveryDrillScheduler
from report.report_generator import ReportGenerator


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('validation.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class BackupValidationTool:
    def __init__(self, config_path: str):
        logger.info(f"Loading configuration from: {config_path}")
        self.config: AppConfig = load_config(config_path)
        self.source_driver = None
        self.verify_driver = None
        self.restore_result = None
        self.validation_summary = None
        self.diff_report = None
        self.quick_validation_result = None

    def initialize_connections(self) -> bool:
        logger.info("Initializing database connections...")

        try:
            self.source_driver = create_driver(self.config.source_db)
            if not self.source_driver.connect():
                logger.error("Failed to connect to source database")
                return False

            source_ok, source_latency = self.source_driver.test_connection()
            logger.info(f"Source DB connection test: {'OK' if source_ok else 'FAILED'} (latency: {source_latency:.3f}s)")

            self.verify_driver = create_driver(self.config.verification_db)
            if not self.verify_driver.connect():
                logger.error("Failed to connect to verification database")
                return False

            verify_ok, verify_latency = self.verify_driver.test_connection()
            logger.info(f"Verify DB connection test: {'OK' if verify_ok else 'FAILED'} (latency: {verify_latency:.3f}s)")

            return source_ok and verify_ok

        except Exception as e:
            logger.error(f"Connection initialization failed: {e}")
            return False

    def run_backup_restore(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("Starting Backup Restore Process")
        logger.info("=" * 60)

        manager = BackupRestoreManager(self.config.backup, self.verify_driver)
        self.restore_result = manager.deploy_and_restore()

        if self.restore_result['success']:
            logger.info(f"Backup restore completed successfully in {self.restore_result['duration_seconds']:.2f}s")
        else:
            logger.error(f"Backup restore failed: {self.restore_result.get('error', 'Unknown error')}")

        return self.restore_result

    def run_quick_validation(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("Running Quick Validation Mode")
        logger.info("=" * 60)

        quick_validator = QuickValidator(
            self.source_driver,
            self.verify_driver,
            {
                'row_count_tolerance': self.config.validation.row_count_tolerance,
                'tables': self.config.validation.tables_to_validate,
                'exclude_tables': self.config.validation.exclude_tables
            }
        )

        self.quick_validation_result = quick_validator.run_quick_validation()
        return self.quick_validation_result.to_dict()

    def run_validations(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("Starting Validation Process")
        logger.info("=" * 60)

        engine = ValidationEngine(
            self.config.validation,
            self.source_driver,
            self.verify_driver
        )

        self.validation_summary = engine.run_all_validations()

        logger.info(f"Validation completed. Overall status: {self.validation_summary['overall_status'].value}")
        logger.info(f"Passed: {self.validation_summary['passed']}, "
                     f"Failed: {self.validation_summary['failed']}, "
                     f"Warnings: {self.validation_summary['warnings']}, "
                     f"Errors: {self.validation_summary['errors']}")
        logger.info(f"Pass rate: {self.validation_summary['pass_rate']:.1f}%")

        return self.validation_summary

    def run_diff_analysis(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("Starting Data Diff Analysis")
        logger.info("=" * 60)

        diff_analyzer = DataDiffAnalyzer(
            self.source_driver,
            self.verify_driver,
            {
                'max_data_diffs_per_table': 100,
                'compare_row_values': True,
                'deep_compare': False,
                'tables': self.config.validation.tables_to_validate,
                'exclude_tables': self.config.validation.exclude_tables
            }
        )

        self.diff_report = diff_analyzer.run_diff_analysis()

        diffs_json = self.diff_report.to_dict()
        summary = diffs_json['summary']
        logger.info(f"Diff analysis complete: {summary['overall_status']}")
        logger.info(f"  Tables with diffs: {summary['tables_with_diffs']}")
        logger.info(f"  Schema diffs: {summary['total_schema_diffs']}")
        logger.info(f"  Data diffs: {summary['total_data_diffs']}")

        return diffs_json

    def generate_report(self) -> str:
        logger.info("=" * 60)
        logger.info("Generating Validation Report")
        logger.info("=" * 60)

        report_gen = ReportGenerator(
            output_dir=self.config.report.output_dir,
            template_path=self.config.report.template_path,
            include_detailed_log=self.config.report.include_detailed_log
        )

        config_dict = {
            'source_db': {
                'host': self.config.source_db.host,
                'port': self.config.source_db.port,
                'database': self.config.source_db.database,
                'type': self.config.source_db.db_type
            },
            'verification_db': {
                'host': self.config.verification_db.host,
                'port': self.config.verification_db.port,
                'database': self.config.verification_db.database,
                'type': self.config.verification_db.db_type
            },
            'backup': {
                'backup_file_path': self.config.backup.backup_file_path,
                'backup_type': self.config.backup.backup_type,
                'encryption_algorithm': self.config.backup.encryption_algorithm
            },
            'validation': {
                'row_count_tolerance': self.config.validation.row_count_tolerance,
                'sample_percentage': self.config.validation.sample_percentage,
                'sample_min_rows': self.config.validation.sample_min_rows,
                'sample_max_rows': self.config.validation.sample_max_rows
            }
        }

        restore_result = self.restore_result or {}
        validation_summary = self.validation_summary or {
            'overall_status': CheckStatus.SKIPPED,
            'passed': 0, 'failed': 0, 'warnings': 0, 'errors': 0,
            'skipped': 0, 'pass_rate': 0, 'results': []
        }

        report_path = report_gen.generate_report(
            restore_result=restore_result,
            validation_summary=validation_summary,
            config=config_dict
        )

        logger.info(f"Report generated: {report_path}")

        if self.diff_report:
            diff_path = os.path.join(
                self.config.report.output_dir,
                f"data_diff_{time.strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(diff_path, 'w', encoding='utf-8') as f:
                json.dump(self.diff_report.to_dict(), f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Diff report saved: {diff_path}")

        if self.quick_validation_result:
            quick_path = os.path.join(
                self.config.report.output_dir,
                f"quick_validation_{time.strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(quick_path, 'w', encoding='utf-8') as f:
                json.dump(self.quick_validation_result.to_dict(), f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Quick validation report saved: {quick_path}")

        return report_path

    def cleanup(self):
        logger.info("Cleaning up connections...")
        if self.source_driver:
            self.source_driver.disconnect()
        if self.verify_driver:
            self.verify_driver.disconnect()
        logger.info("Cleanup completed")

    def run_quick_mode(self) -> bool:
        start_time = time.time()
        success = False

        try:
            if not self.initialize_connections():
                logger.error("Failed to initialize database connections")
                return False

            self.run_quick_validation()
            self.generate_report()

            summary = self.quick_validation_result.summary if self.quick_validation_result else {}
            success = summary.get('overall_status') == 'PASSED'

        except Exception as e:
            logger.error(f"Quick validation failed: {e}", exc_info=True)
        finally:
            self.cleanup()
            elapsed = time.time() - start_time
            logger.info(f"Quick mode execution time: {elapsed:.2f}s")

        return success

    def run_diff_only_mode(self) -> bool:
        start_time = time.time()
        success = False

        try:
            if not self.initialize_connections():
                logger.error("Failed to initialize database connections")
                return False

            self.run_diff_analysis()
            self.generate_report()

            if self.diff_report:
                summary = self.diff_report.summary
                success = summary.get('overall_status') == 'CLEAN'

        except Exception as e:
            logger.error(f"Diff analysis failed: {e}", exc_info=True)
        finally:
            self.cleanup()
            elapsed = time.time() - start_time
            logger.info(f"Diff mode execution time: {elapsed:.2f}s")

        return success

    def run(self) -> bool:
        start_time = time.time()
        success = False

        try:
            if not self.initialize_connections():
                logger.error("Failed to initialize database connections")
                return False

            logger.info("All database connections established successfully")

            self.run_backup_restore()

            if not self.restore_result.get('success', False):
                logger.warning("Backup restore failed, but continuing with validation of existing data...")

            self.run_validations()

            self.run_diff_analysis()

            self.generate_report()

            overall = self.validation_summary.get('overall_status')
            if overall and overall.value in ('PASSED', 'WARNING'):
                success = True

        except Exception as e:
            logger.error(f"Validation process failed with exception: {e}", exc_info=True)
        finally:
            self.cleanup()
            elapsed = time.time() - start_time
            logger.info(f"Total execution time: {elapsed:.2f}s")
            logger.info(f"Validation {'PASSED' if success else 'FAILED'}")

        return success


def run_recovery_drill(config_path: str, interval_seconds: int, once: bool = False):
    scheduler = RecoveryDrillScheduler(
        config_path=config_path,
        schedule_config={
            'interval_seconds': interval_seconds,
            'run_diff_analysis': True,
            'run_quick_validate': True,
            'health_report_dir': './output/health'
        }
    )

    if once:
        logger.info("Running single recovery drill...")
        result = scheduler.run_single_drill()
        report = scheduler.generate_health_report()
        logger.info(f"Health status: {report.current_health_status.value}")
        logger.info(f"Health score: {result.health_score}/100")
        if report.recommendations:
            logger.info("Recommendations:")
            for rec in report.recommendations:
                logger.info(f"  - {rec}")
        return result.overall_status.value in ('HEALTHY', 'DEGRADED')
    else:
        logger.info(f"Starting automated recovery drill scheduler (interval={interval_seconds}s)...")
        logger.info("Press Ctrl+C to stop...")

        try:
            def on_drill_complete(result):
                logger.info(f"Drill complete: {result.drill_id} - {result.overall_status.value} (score={result.health_score})")

            scheduler.start(on_drill_complete=on_drill_complete)

            while scheduler.is_running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received interrupt, stopping scheduler...")
            scheduler.stop()

        return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Database Backup Recovery Validation Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Full validation with restore:
    python main.py --config config.yaml

  Quick validation mode (metadata and PK range only):
    python main.py -c config.yaml --quick

  Data diff analysis only (no restore):
    python main.py -c config.yaml --diff-only

  Run single recovery drill:
    python main.py -c config.yaml --drill --once

  Start automated recovery drill scheduler (hourly):
    python main.py -c config.yaml --drill --interval 3600

  Generate health report for last 7 days:
    python main.py -c config.yaml --health-report 168
        """
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Override output directory for reports'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '-q', '--quick',
        action='store_true',
        help='Quick validation mode: only check metadata and primary key range'
    )
    parser.add_argument(
        '-d', '--diff-only',
        action='store_true',
        help='Diff analysis mode: only compare data differences between source and target'
    )
    parser.add_argument(
        '--drill',
        action='store_true',
        help='Run recovery drill (single or scheduled)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run only one drill and exit (use with --drill)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=3600,
        help='Interval in seconds between scheduled drills (default: 3600 = 1 hour)'
    )
    parser.add_argument(
        '--health-report',
        type=int,
        metavar='HOURS',
        help='Generate health report for the last N hours and exit'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config_path = args.config
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Please create a config.yaml file based on the template.")
        sys.exit(1)

    if args.health_report:
        scheduler = RecoveryDrillScheduler(
            config_path=config_path,
            schedule_config={'health_report_dir': './output/health'}
        )
        report = scheduler.generate_health_report(period_hours=args.health_report)
        print(f"\n=== Health Report ({args.health_report} hours) ===")
        print(f"Status: {report.current_health_status.value}")
        print(f"Total drills: {report.total_drills}")
        print(f"Successful: {report.successful_drills}")
        print(f"Failed: {report.failed_drills}")
        print(f"Avg health score: {report.average_health_score:.1f}/100")
        if report.recommendations:
            print("\nRecommendations:")
            for rec in report.recommendations:
                print(f"  - {rec}")
        sys.exit(0)

    if args.drill:
        success = run_recovery_drill(config_path, args.interval, once=args.once)
        sys.exit(0 if success else 1)

    tool = BackupValidationTool(config_path)

    if args.output:
        tool.config.report.output_dir = args.output

    if args.quick:
        logger.info("Running in QUICK VALIDATION mode")
        success = tool.run_quick_mode()
    elif args.diff_only:
        logger.info("Running in DIFF ANALYSIS mode")
        success = tool.run_diff_only_mode()
    else:
        logger.info("Running in FULL VALIDATION mode")
        success = tool.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

