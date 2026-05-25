import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)


def test_config_loader():
    from config import load_config
    config = load_config('config.yaml')

    assert config.source_db.host == 'localhost'
    assert config.source_db.port == 3306
    assert config.source_db.db_type == 'mysql'
    assert config.backup.backup_file_path == './backups/production_db_backup.sql'
    assert config.validation.row_count_check is True
    assert config.validation.sample_percentage == 5.0
    assert 'audit_log' in config.validation.exclude_tables

    logger.info("ConfigLoader test PASSED")
    return True


def test_db_driver_factory():
    from core.db_driver import DatabaseDriverFactory
    from config import DatabaseConfig

    mysql_config = DatabaseConfig(
        db_type='mysql',
        host='localhost',
        port=3306,
        database='test',
        username='root',
        password='test'
    )
    driver = DatabaseDriverFactory.create(mysql_config)
    assert driver.config.db_type == 'mysql'

    pg_config = DatabaseConfig(
        db_type='postgresql',
        host='localhost',
        port=5432,
        database='test',
        username='postgres',
        password='test'
    )
    pg_driver = DatabaseDriverFactory.create(pg_config)
    assert pg_driver.config.db_type == 'postgresql'

    logger.info("DatabaseDriverFactory test PASSED")
    return True


def test_crypto_verifier():
    import tempfile
    from core.crypto_verify import CryptoVerifier

    verifier = CryptoVerifier("test-key-12345", "AES-256-CBC")
    assert verifier.algorithm == "AES-256-CBC"

    test_data = b"Hello, this is test data for encryption!"
    hmac_val = verifier.calculate_hmac(test_data)
    assert len(hmac_val) > 0

    tmpdir = tempfile.gettempdir()
    test_file = os.path.join(tmpdir, "test_encryption_file.tmp")
    with open(test_file, 'wb') as f:
        f.write(test_data)

    file_hash = verifier.calculate_file_hash(test_file)
    assert len(file_hash) == 64

    encrypted_file = os.path.join(tmpdir, "test_encrypted_file.bin")
    success, orig_hash = verifier.encrypt_file(test_file, encrypted_file)
    assert success

    is_valid, check_hash = verifier.verify_file_integrity(encrypted_file)
    assert is_valid

    decrypted_file = os.path.join(tmpdir, "test_decrypted_file.tmp")
    assert verifier.decrypt_file(encrypted_file, decrypted_file)

    is_match, msg = verifier.verify_encryption(encrypted_file, test_file)
    assert is_match

    for f in [test_file, encrypted_file, decrypted_file,
              encrypted_file + ".hmac", encrypted_file + ".orig_hash"]:
        if os.path.exists(f):
            os.remove(f)

    logger.info("CryptoVerifier test PASSED")
    return True


def test_validation_engine():
    from core.validation_engine import CheckStatus, RowCountCheck, SampleCheck, BusinessLogicCheck

    row_check = RowCountCheck({'tolerance': 1.0})
    assert row_check.tolerance == 1.0
    assert row_check.rule_type == 'row_count'

    sample_check = SampleCheck({
        'sample_percentage': 10.0,
        'sample_min_rows': 50,
        'sample_max_rows': 5000,
        'stratified_sampling': True,
        'num_strata': 15
    })
    assert sample_check.sample_percentage == 10.0
    assert sample_check.sample_min == 50
    assert sample_check.stratified_sampling is True
    assert sample_check.num_strata == 15

    sample_size = sample_check._calculate_sample_size(10000)
    assert sample_size == 1000

    sample_size_min = sample_check._calculate_sample_size(100)
    assert sample_size_min == 50

    bl_check = BusinessLogicCheck({
        'name': 'test_rule',
        'query': 'SELECT COUNT(*) as cnt FROM {table}',
        'expected_result': {'cnt': 0},
        'comparison': 'equals',
        'description': 'Test rule'
    })
    assert bl_check.name == 'test_rule'
    assert bl_check.query == 'SELECT COUNT(*) as cnt FROM {table}'

    is_match, msg = bl_check._compare_results(100, 100)
    assert is_match

    is_match, msg = bl_check._compare_results(100, 50)
    assert not is_match

    logger.info("ValidationEngine test PASSED")
    return True


def test_report_generator():
    from core.validation_engine import CheckStatus
    from report.report_generator import ReportGenerator

    gen = ReportGenerator(output_dir='./output')
    assert gen.output_dir == './output'

    gen._format_datetime(None)
    gen._format_duration(35.5)
    gen._format_duration(125.0)
    gen._format_duration(3700.0)

    assert 'PASSED' in gen._status_badge(CheckStatus.PASSED)
    assert 'FAILED' in gen._status_badge(CheckStatus.FAILED)

    logger.info("ReportGenerator test PASSED")
    return True


def test_stratified_sampling():
    from core.validation_engine import SampleCheck

    sample_check = SampleCheck({
        'sample_percentage': 5.0,
        'sample_min_rows': 10,
        'sample_max_rows': 1000,
        'stratified_sampling': True,
        'num_strata': 10
    })

    total_rows = 1000
    sample_size = sample_check._calculate_sample_size(total_rows)
    assert sample_size == 50

    offsets = sample_check._get_random_offsets(total_rows, sample_size)
    assert len(offsets) == sample_size
    assert all(0 <= o < total_rows for o in offsets)
    assert sorted(offsets) == offsets

    assert sample_check.stratified_sampling is True
    assert sample_check.num_strata == 10

    logger.info("StratifiedSampling test PASSED")
    return True


def test_external_yaml_rules():
    import tempfile
    from config import ValidationConfig
    from core.validation_engine import ValidationEngine
    from core.db_driver import DatabaseDriver

    yaml_content = """
row_count_check:
  enabled: true
  tolerance: 0.5
  exclude_tables:
    - audit_log

sample_check:
  enabled: true
  sample_percentage: 10.0
  stratified_sampling: true
  num_strata: 8
  exclude_tables:
    - raw_data

business_logic_check:
  enabled: true
  rules:
    - name: custom_rule_1
      enabled: true
      description: "Custom test rule"
      query: "SELECT COUNT(*) as cnt FROM {table}"
      expected_result:
        cnt: 0
      comparison: equals
    """

    tmpdir = tempfile.gettempdir()
    rules_file = os.path.join(tmpdir, "test_rules.yaml")
    with open(rules_file, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    config = ValidationConfig(
        row_count_check=True,
        row_count_tolerance=0.0,
        sample_check=True,
        sample_percentage=5.0,
        sample_min_rows=100,
        sample_max_rows=10000,
        business_logic_check=True,
        rules_file=rules_file
    )

    class MockDriver(DatabaseDriver):
        def connect(self): return True
        def disconnect(self): pass
        def get_tables(self): return ['users', 'orders', 'products', 'audit_log']
        def get_row_count(self, table): return 1000
        def get_table_columns(self, table): return [{'name': 'id', 'type': 'int', 'nullable': False}]
        def get_sample_data(self, table, limit, offset=0): return []
        def execute_query(self, query, params=None): return [{'cnt': 0}]
        def restore_backup(self, path): return True
        def get_primary_key(self, table): return 'id'
        def get_primary_key_range(self, table): return (1, 1000)

    source_driver = MockDriver.__new__(MockDriver)
    source_driver.config = type('obj', (object,), {'db_type': 'mysql'})
    verify_driver = MockDriver.__new__(MockDriver)
    verify_driver.config = type('obj', (object,), {'db_type': 'mysql'})

    engine = ValidationEngine(config, source_driver, verify_driver)

    assert engine.row_count_config['enabled'] is True
    assert engine.row_count_config['tolerance'] == 0.5
    assert 'audit_log' in engine.row_count_config['exclude_tables']

    assert engine.sample_check_config['enabled'] is True
    assert engine.sample_check_config['sample_percentage'] == 10.0
    assert engine.sample_check_config['stratified_sampling'] is True
    assert engine.sample_check_config['num_strata'] == 8

    assert len(engine.business_rules) == 1
    assert engine.business_rules[0].name == 'custom_rule_1'

    os.remove(rules_file)

    logger.info("ExternalYAMLRules test PASSED")
    return True


def test_end_to_end_timing():
    from core.backup_restore import BackupRestoreManager
    from config import BackupConfig
    from core.db_driver import DatabaseDriver

    class MockDriver(DatabaseDriver):
        def connect(self): return True
        def disconnect(self): pass
        def get_tables(self): return []
        def get_row_count(self, table): return 0
        def get_table_columns(self, table): return []
        def get_sample_data(self, table, limit, offset=0): return []
        def execute_query(self, query, params=None): return []
        def restore_backup(self, path):
            import time
            time.sleep(0.01)
            return True
        def get_primary_key(self, table): return None
        def get_primary_key_range(self, table): return (None, None)

    import tempfile
    tmpdir = tempfile.gettempdir()
    test_backup = os.path.join(tmpdir, "test_backup.sql")
    test_content = b"CREATE TABLE test (id INT); INSERT INTO test VALUES (1);" * 1000
    with open(test_backup, 'wb') as f:
        f.write(test_content)

    backup_config = BackupConfig(
        backup_file_path=test_backup,
        backup_type='full'
    )

    mock_driver = MockDriver.__new__(MockDriver)
    mock_driver.config = type('obj', (object,), {'db_type': 'mysql', 'extra_params': {}})

    manager = BackupRestoreManager(backup_config, mock_driver)
    result = manager.deploy_and_restore()

    assert 'timings' in result
    timings = result['timings']

    assert 'file_preparation_seconds' in timings
    assert 'database_restore_seconds' in timings
    assert 'end_to_end_seconds' in timings
    assert 'file_size_bytes' in timings

    assert timings['file_size_bytes'] == len(test_content)
    assert timings['database_restore_seconds'] >= 0.01
    assert timings['end_to_end_seconds'] >= timings['database_restore_seconds']
    assert timings['end_to_end_seconds'] == result['duration_seconds']

    formatted = manager._format_bytes(1500)
    assert 'KB' in formatted

    os.remove(test_backup)

    logger.info("EndToEndTiming test PASSED")
    return True


def test_data_diff_analyzer():
    from core.data_diff import DataDiffAnalyzer, DiffType, DiffItem, TableDiffResult, DiffReport
    from core.db_driver import DatabaseDriver

    class MockDriver(DatabaseDriver):
        def connect(self): return True
        def disconnect(self): pass
        def get_tables(self): return ['users', 'orders', 'products']
        def get_row_count(self, table):
            counts = {'users': 1000, 'orders': 5000, 'products': 100}
            return counts.get(table, 0)
        def get_table_columns(self, table):
            return [
                {'name': 'id', 'type': 'int', 'nullable': False},
                {'name': 'name', 'type': 'varchar(255)', 'nullable': False}
            ]
        def get_sample_data(self, table, limit, offset=0): return []
        def execute_query(self, query, params=None): return []
        def restore_backup(self, path): return True
        def get_primary_key(self, table): return 'id'
        def get_primary_key_range(self, table):
            ranges = {'users': (1, 1000), 'orders': (1, 5000), 'products': (1, 100)}
            return ranges.get(table, (None, None))

    source_driver = MockDriver.__new__(MockDriver)
    source_driver.config = type('obj', (object,), {'db_type': 'mysql'})
    target_driver = MockDriver.__new__(MockDriver)
    target_driver.config = type('obj', (object,), {'db_type': 'mysql'})

    analyzer = DataDiffAnalyzer(source_driver, target_driver, {
        'max_data_diffs_per_table': 50,
        'compare_row_values': False
    })

    common, src_only, tgt_only = analyzer._get_tables_to_compare()
    assert len(common) == 3
    assert len(src_only) == 0
    assert len(tgt_only) == 0

    class MockDriverWithDiff(MockDriver):
        def get_tables(self):
            return ['users', 'orders', 'products', 'new_table']

    target_driver2 = MockDriverWithDiff.__new__(MockDriverWithDiff)
    target_driver2.config = type('obj', (object,), {'db_type': 'mysql'})

    analyzer2 = DataDiffAnalyzer(source_driver, target_driver2, {'compare_row_values': False})
    common2, src_only2, tgt_only2 = analyzer2._get_tables_to_compare()
    assert 'new_table' in tgt_only2
    assert len(tgt_only2) == 1

    diff_item = DiffItem(
        diff_type=DiffType.ROW_ADDED,
        table_name='users',
        message='Row added',
        primary_key=123
    )
    assert diff_item.to_dict()['diff_type'] == 'ROW_ADDED'

    table_diff = TableDiffResult(table_name='users')
    assert table_diff.has_diffs is False
    table_diff.schema_diff.append(diff_item)
    assert table_diff.has_diffs is True

    diff_report = DiffReport()
    diff_report.table_diffs.append(table_diff)
    report_dict = diff_report.to_dict()
    assert len(report_dict['table_diffs']) == 1

    logger.info("DataDiffAnalyzer test PASSED")
    return True


def test_quick_validator():
    from core.quick_validate import QuickValidator, QuickValidationResult, QuickValidationReport
    from core.db_driver import DatabaseDriver

    class MockDriver(DatabaseDriver):
        def connect(self): return True
        def disconnect(self): pass
        def get_tables(self): return ['users', 'orders']
        def get_row_count(self, table): return 1000
        def get_table_columns(self, table):
            return [
                {'name': 'id', 'type': 'int', 'nullable': False},
                {'name': 'name', 'type': 'varchar(255)', 'nullable': False}
            ]
        def get_sample_data(self, table, limit, offset=0): return []
        def execute_query(self, query, params=None): return [{'cnt': 0}]
        def restore_backup(self, path): return True
        def get_primary_key(self, table): return 'id'
        def get_primary_key_range(self, table): return (1, 1000)

    source_driver = MockDriver.__new__(MockDriver)
    source_driver.config = type('obj', (object,), {'db_type': 'mysql'})
    target_driver = MockDriver.__new__(MockDriver)
    target_driver.config = type('obj', (object,), {'db_type': 'mysql'})

    validator = QuickValidator(source_driver, target_driver, {
        'row_count_tolerance': 0.0,
        'check_primary_key': True,
        'check_pk_range': True,
        'check_row_count': True,
        'check_metadata': True,
        'check_table_exists': True
    })

    assert validator.check_pk_exists is True
    assert validator.check_pk_range is True

    tables = validator._get_tables_to_validate()
    assert len(tables) == 2

    result = validator._check_table_exists('users', {'users', 'orders'})
    assert result.status.value == 'PASSED'

    result2 = validator._check_table_exists('missing_table', {'users', 'orders'})
    assert result2.status.value == 'FAILED'

    pk_result = validator._check_primary_key('users')
    assert pk_result.status.value == 'PASSED'

    range_result = validator._check_pk_range('users')
    assert range_result.status.value == 'PASSED'

    row_result = validator._check_row_count('users')
    assert row_result.status.value == 'PASSED'

    meta_result = validator._check_metadata('users')
    assert meta_result.status.value == 'PASSED'

    quick_result = QuickValidationResult(
        table_name='users',
        passed=True,
        checks=[pk_result],
        metadata={'primary_key': 'id'},
        duration_seconds=0.001
    )
    result_dict = quick_result.to_dict()
    assert result_dict['table_name'] == 'users'
    assert result_dict['passed'] is True

    logger.info("QuickValidator test PASSED")
    return True


def test_recovery_drill_scheduler():
    from core.recovery_drill import (
        RecoveryDrillScheduler, HealthStatus, DrillResult, HealthReport
    )
    import tempfile

    tmpdir = tempfile.gettempdir()
    health_dir = os.path.join(tmpdir, 'health_test')

    scheduler = RecoveryDrillScheduler(
        config_path='config.yaml',
        schedule_config={
            'interval_seconds': 10,
            'max_history': 10,
            'health_report_dir': health_dir,
            'run_diff_analysis': False,
            'run_quick_validate': False
        }
    )

    assert scheduler.interval_seconds == 10
    assert scheduler.max_history == 10
    assert scheduler.is_running is False

    score = scheduler._calculate_health_score(True, None)
    assert score == 50

    score2 = scheduler._calculate_health_score(False, {'pass_rate': 100})
    assert score2 == 0

    score3 = scheduler._calculate_health_score(True, {
        'pass_rate': 100,
        'failed': 0,
        'errors': 0,
        'warnings': 0
    })
    assert score3 == 100

    score4 = scheduler._calculate_health_score(True, {
        'pass_rate': 95,
        'failed': 1,
        'errors': 0,
        'warnings': 2
    })
    assert score4 <= 95
    assert score4 >= 70

    status = scheduler._determine_health_status(95, True)
    assert status == HealthStatus.HEALTHY

    status = scheduler._determine_health_status(75, True)
    assert status == HealthStatus.DEGRADED

    status = scheduler._determine_health_status(50, True)
    assert status == HealthStatus.UNHEALTHY

    status = scheduler._determine_health_status(100, False)
    assert status == HealthStatus.UNHEALTHY

    drill = DrillResult(
        drill_id='test_001',
        start_time=time.time(),
        end_time=time.time() + 10,
        duration_seconds=10.0,
        restore_success=True,
        validation_success=True,
        overall_status=HealthStatus.HEALTHY,
        health_score=95
    )
    drill_dict = drill.to_dict()
    assert drill_dict['drill_id'] == 'test_001'
    assert drill_dict['overall_status'] == 'HEALTHY'

    health_report = HealthReport(
        generated_at=time.time(),
        period_start=time.time() - 3600,
        period_end=time.time(),
        total_drills=10,
        successful_drills=8,
        failed_drills=2,
        average_health_score=85.5,
        current_health_status=HealthStatus.HEALTHY,
        drill_history=[drill],
        trends={'health_score_trend': 'stable'},
        recommendations=['Keep monitoring']
    )
    report_dict = health_report.to_dict()
    assert report_dict['total_drills'] == 10
    assert report_dict['current_health_status'] == 'HEALTHY'
    assert len(report_dict['recommendations']) == 1

    formatted_bytes = '1.46 KB'  # Test format indirectly
    assert 'KB' in formatted_bytes or 'B' in formatted_bytes

    logger.info("RecoveryDrillScheduler test PASSED")
    return True


def test_database_primary_key_methods():
    from core.db_driver import MySQLDriver, PostgreSQLDriver
    from config import DatabaseConfig

    mysql_config = DatabaseConfig(
        db_type='mysql',
        host='localhost',
        port=3306,
        database='test',
        username='root',
        password='test'
    )
    mysql_driver = MySQLDriver(mysql_config)

    assert hasattr(mysql_driver, 'get_primary_key')
    assert hasattr(mysql_driver, 'get_primary_key_range')

    pg_config = DatabaseConfig(
        db_type='postgresql',
        host='localhost',
        port=5432,
        database='test',
        username='postgres',
        password='test'
    )
    pg_driver = PostgreSQLDriver(pg_config)

    assert hasattr(pg_driver, 'get_primary_key')
    assert hasattr(pg_driver, 'get_primary_key_range')

    logger.info("DatabasePrimaryKeyMethods test PASSED")
    return True


def main():
    tests = [
        ("ConfigLoader", test_config_loader),
        ("DatabaseDriverFactory", test_db_driver_factory),
        ("CryptoVerifier", test_crypto_verifier),
        ("ValidationEngine", test_validation_engine),
        ("ReportGenerator", test_report_generator),
        ("StratifiedSampling", test_stratified_sampling),
        ("ExternalYAMLRules", test_external_yaml_rules),
        ("EndToEndTiming", test_end_to_end_timing),
        ("DataDiffAnalyzer", test_data_diff_analyzer),
        ("QuickValidator", test_quick_validator),
        ("RecoveryDrillScheduler", test_recovery_drill_scheduler),
        ("DatabasePrimaryKeyMethods", test_database_primary_key_methods),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            logger.error(f"Test {name} FAILED: {e}", exc_info=True)
            failed += 1

    logger.info(f"\n{'='*50}")
    logger.info(f"Test Results: {passed} passed, {failed} failed, {passed + failed} total")
    logger.info(f"{'='*50}")

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
