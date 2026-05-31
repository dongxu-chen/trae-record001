#!/usr/bin/env python3
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rule_engine import (
    RuleEngine, Rule, Severity, ValidationResult,
    CheckStatus, CheckItem, CheckResult, Report
)
from backend.checkers.branch_naming import BranchNamingChecker
from backend.checkers.merge_direction import MergeDirectionChecker
from backend.config import Config


class TestRuleEngine(unittest.TestCase):
    def setUp(self):
        self.rule_engine = RuleEngine()

    def test_add_rule(self):
        def check_func(x):
            return x > 0, 'Positive number', {'value': x}
        
        rule = Rule('test_positive', check_func, Severity.ERROR)
        self.rule_engine.add_rule('test', rule)
        
        self.assertIn('test', self.rule_engine.rules)
        self.assertEqual(len(self.rule_engine.rules['test']), 1)

    def test_match_pattern_regex(self):
        self.assertTrue(RuleEngine.match_pattern('feature/ABC-123-description', r'^feature/[A-Z]+-\d+-.+$'))
        self.assertFalse(RuleEngine.match_pattern('bad-branch', r'^feature/[A-Z]+-\d+-.+$'))

    def test_match_glob_pattern(self):
        self.assertTrue(RuleEngine.match_glob_pattern('feature/test', 'feature/*'))
        self.assertTrue(RuleEngine.match_glob_pattern('feature/sub/test', 'feature/**'))


class TestCheckItem(unittest.TestCase):
    def test_check_item_creation(self):
        item = CheckItem(
            id='test-001',
            name='Test Check',
            description='Test description',
            category='test',
            status=CheckStatus.PASS,
            severity=Severity.INFO,
            message='Test passed'
        )
        self.assertEqual(item.status, CheckStatus.PASS)
        self.assertEqual(item.severity, Severity.INFO)

    def test_check_item_to_dict(self):
        item = CheckItem(
            id='test-001',
            name='Test Check',
            description='Test description',
            category='test',
            status=CheckStatus.PASS,
            severity=Severity.INFO,
            message='Test passed',
            details={'key': 'value'},
            suggestion='Test suggestion'
        )
        item_dict = item.to_dict()
        self.assertEqual(item_dict['id'], 'test-001')
        self.assertEqual(item_dict['status'], 'pass')
        self.assertEqual(item_dict['severity'], 'info')
        self.assertEqual(item_dict['details'], {'key': 'value'})
        self.assertEqual(item_dict['suggestion'], 'Test suggestion')


class TestCheckResult(unittest.TestCase):
    def test_check_result_summary(self):
        cr = CheckResult(
            category='test',
            display_name='Test Check',
            status=CheckStatus.PASS
        )
        cr.items.append(CheckItem(
            id='test-001', name='Item 1', description='',
            category='test', status=CheckStatus.PASS,
            severity=Severity.INFO, message='Passed'
        ))
        cr.items.append(CheckItem(
            id='test-002', name='Item 2', description='',
            category='test', status=CheckStatus.FAIL,
            severity=Severity.ERROR, message='Failed'
        ))
        
        cr_dict = cr.to_dict()
        self.assertEqual(cr_dict['summary']['total'], 2)
        self.assertEqual(cr_dict['summary']['passed'], 1)
        self.assertEqual(cr_dict['summary']['failed'], 1)

    def test_get_errors(self):
        cr = CheckResult(
            category='test',
            display_name='Test Check',
            status=CheckStatus.PASS
        )
        error_item = CheckItem(
            id='test-001', name='Error Item', description='',
            category='test', status=CheckStatus.FAIL,
            severity=Severity.ERROR, message='Error'
        )
        warning_item = CheckItem(
            id='test-002', name='Warning Item', description='',
            category='test', status=CheckStatus.WARNING,
            severity=Severity.WARNING, message='Warning'
        )
        cr.items.extend([error_item, warning_item])
        
        errors = cr.get_errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'test-001')


class TestReport(unittest.TestCase):
    def test_report_summary(self):
        report = Report(
            source_branch='feature/test',
            target_branch='develop',
            repo_path='./test'
        )
        
        cr = CheckResult(
            category='branch_naming',
            display_name='Branch Naming',
            status=CheckStatus.PASS
        )
        cr.items.append(CheckItem(
            id='bn-001', name='Valid Branch', description='',
            category='branch_naming', status=CheckStatus.PASS,
            severity=Severity.INFO, message='OK'
        ))
        report.check_results.append(cr)
        
        report_dict = report.to_dict()
        self.assertEqual(report_dict['source_branch'], 'feature/test')
        self.assertEqual(report_dict['target_branch'], 'develop')
        self.assertEqual(report_dict['summary']['total_checks'], 1)
        self.assertEqual(report_dict['summary']['passed'], 1)
        self.assertEqual(report_dict['summary']['status'], 'passed')

    def test_report_checklist_output(self):
        report = Report(
            source_branch='feature/test',
            target_branch='develop'
        )
        
        cr = CheckResult(
            category='branch_naming',
            display_name='分支命名规范检查',
            status=CheckStatus.PASS
        )
        cr.items.append(CheckItem(
            id='bn-001', name='分支类型: feature', description='Feature branch pattern',
            category='branch_naming', status=CheckStatus.PASS,
            severity=Severity.INFO, message='Branch name matches pattern',
            suggestion='Keep up the good work!'
        ))
        report.check_results.append(cr)
        
        checklist = report.to_checklist()
        self.assertIn('# Git Branch Policy Check Report', checklist)
        self.assertIn('Source Branch', checklist)
        self.assertIn('分支命名规范检查', checklist)
        self.assertIn('Keep up the good work!', checklist)


class TestBranchNamingChecker(unittest.TestCase):
    class MockGitUtils:
        def get_current_branch(self):
            return 'feature/ABC-123-test'

    def setUp(self):
        self.config = Config('config/rules.yaml')
        self.git_utils = self.MockGitUtils()
        self.checker = BranchNamingChecker(self.git_utils, self.config)

    def test_check_valid_branch_returns_checkresult(self):
        result = self.checker.check('feature/ABC-123-test')
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertEqual(result.metadata.get('matched_pattern'), 'feature')

    def test_check_invalid_branch(self):
        result = self.checker.check('invalid-branch')
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertTrue(len(result.items) > 0)
        self.assertIsNotNone(result.metadata.get('suggested_name'))

    def test_suggest_fix(self):
        suggestion = self.checker.suggest_fix('feature/test')
        self.assertIn('TICKET-001', suggestion)


class TestMergeDirectionChecker(unittest.TestCase):
    class MockGitUtils:
        pass

    def setUp(self):
        self.config = Config('config/rules.yaml')
        self.git_utils = self.MockGitUtils()
        self.checker = MergeDirectionChecker(self.git_utils, self.config)

    def test_allowed_merge_returns_checkresult(self):
        result = self.checker.check('feature/ABC-123', 'develop')
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertTrue(result.metadata.get('allowed'))

    def test_blocked_merge(self):
        result = self.checker.check('main', 'feature/ABC-123')
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertFalse(result.metadata.get('allowed'))


class TestPRSizeModuleConfig(unittest.TestCase):
    def test_module_config_exists(self):
        config = Config('config/rules.yaml')
        pr_size_rules = config.get_pr_size_rules()
        self.assertIn('modules', pr_size_rules)
        
        modules = pr_size_rules.get('modules', [])
        self.assertTrue(len(modules) > 0)
        
        core_module = next((m for m in modules if m.get('name') == 'core'), None)
        self.assertIsNotNone(core_module)
        self.assertEqual(core_module.get('severity'), 'error')
        self.assertLess(core_module.get('max_files', 999), 20)


class TestNewFeaturesConfig(unittest.TestCase):
    def test_branch_age_config_exists(self):
        config = Config('config/rules.yaml')
        rules = config.get_branch_age_rules()
        self.assertIsNotNone(rules)
        self.assertIn('warning_days', rules)
        self.assertIn('critical_days', rules)
        self.assertIn('stale_days', rules)
        self.assertEqual(rules.get('warning_days'), 30)
        self.assertEqual(rules.get('critical_days'), 60)
        self.assertEqual(rules.get('stale_days'), 90)

    def test_commit_quality_config_exists(self):
        config = Config('config/rules.yaml')
        rules = config.get_commit_quality_rules()
        self.assertIsNotNone(rules)
        self.assertIn('min_length', rules)
        self.assertIn('max_length', rules)
        self.assertIn('required_prefixes', rules)
        self.assertIn('forbidden_words', rules)
        self.assertTrue(len(rules.get('required_prefixes', [])) > 0)

    def test_team_report_config_exists(self):
        config = Config('config/rules.yaml')
        rules = config.get_team_report_rules()
        self.assertIsNotNone(rules)
        self.assertIn('compliance_threshold', rules)
        self.assertIn('excellent_threshold', rules)


if __name__ == '__main__':
    unittest.main()
