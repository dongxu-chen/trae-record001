import os
import argparse
import tempfile
import shutil
from typing import Dict, Any, List

from .config_loader import ConfigLoader
from .git_integration import GitIntegration
from .linting import LintingAnalyzer
from .complexity_analyzer import ComplexityAnalyzer
from .duplication_detector import DuplicationDetector
from .custom_rules import CustomRulesChecker
from .sonarqube_integration import SonarQubeIntegration
from .report_generator import ReportGenerator
from .rules_dsl import DSLEngine, RuleChecker
from .impact_analyzer import ImpactAnalyzer
from .ai_reviewer import AIReviewer
from .effort_estimator import EffortEstimator


class CodeReviewTool:
    def __init__(self, config_path: str = None, rules_path: str = None, dsl_rules_path: str = None):
        self.config_loader = ConfigLoader(
            config_path or "config/config.yaml",
            rules_path or "config/rules/custom_rules.yaml"
        )
        self.config = self.config_loader.load_config()
        self.custom_rules = self.config_loader.load_custom_rules()
        
        self.linting_analyzer = LintingAnalyzer(self.config)
        self.complexity_analyzer = ComplexityAnalyzer(self.config)
        self.duplication_detector = DuplicationDetector(self.config)
        self.custom_rules_checker = CustomRulesChecker(self.custom_rules)
        self.report_generator = ReportGenerator(self.config)
        
        self.impact_analyzer = ImpactAnalyzer(self.config)
        self.ai_reviewer = AIReviewer(self.config)
        self.effort_estimator = EffortEstimator(self.config)
        
        self._init_dsl_rules(dsl_rules_path)
        self._init_git_integration()
        self._init_sonarqube()
    
    def _init_dsl_rules(self, dsl_rules_path: str = None):
        dsl_path = dsl_rules_path or self.config.get('rules', {}).get('dsl_rules_file', 'config/rules/code_rules.dsl')
        self.dsl_engine = DSLEngine()
        
        if os.path.exists(dsl_path):
            self.dsl_rules = self.dsl_engine.parse_dsl_file(dsl_path)
            self.dsl_checker = RuleChecker(self.dsl_rules)
        else:
            self.dsl_rules = []
            self.dsl_checker = RuleChecker([])
    
    def _init_git_integration(self):
        platform = self.config.get('code_review', {}).get('platform', 'github')
        token = None
        
        if platform == 'github':
            token = self.config_loader.get_env_var('GITHUB_TOKEN')
        elif platform == 'gitlab':
            token = self.config_loader.get_env_var('GITLAB_TOKEN')
        
        gitlab_url = self.config_loader.get_env_var('GITLAB_URL')
        
        try:
            self.git_integration = GitIntegration(platform, token, gitlab_url)
        except Exception as e:
            print(f"Warning: Git integration initialization failed: {e}")
            self.git_integration = None
    
    def _init_sonarqube(self):
        if self.config.get('sonarqube', {}).get('enabled', False):
            sonarqube_url = self.config_loader.get_env_var('SONARQUBE_URL')
            sonarqube_token = self.config_loader.get_env_var('SONARQUBE_TOKEN')
            
            try:
                self.sonarqube = SonarQubeIntegration(self.config, sonarqube_url, sonarqube_token)
            except Exception as e:
                print(f"Warning: SonarQube integration initialization failed: {e}")
                self.sonarqube = None
        else:
            self.sonarqube = None
    
    def review_pr(self, repo_owner: str = None, repo_name: str = None, 
                   pr_number: int = None) -> Dict[str, Any]:
        code_review_config = self.config.get('code_review', {})
        repo_owner = repo_owner or code_review_config.get('repo_owner')
        repo_name = repo_name or code_review_config.get('repo_name')
        pr_number = pr_number or code_review_config.get('pr_number')
        
        if not all([repo_owner, repo_name, pr_number]):
            raise ValueError("Missing required PR information")
        
        if not self.git_integration:
            raise RuntimeError("Git integration not initialized")
        
        print(f"Fetching PR #{pr_number} from {repo_owner}/{repo_name}...")
        pr_info = self.git_integration.get_pr_details(repo_owner, repo_name, pr_number)
        
        print(f"Downloading changed files...")
        temp_dir = self.git_integration.download_pr_files(repo_owner, repo_name, pr_number)
        
        changed_files = pr_info.get('changed_files', [])
        
        try:
            analysis_results = self.analyze_directory(temp_dir, changed_files)
            analysis_results['pr_info'] = pr_info
            return analysis_results
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def analyze_directory(self, directory: str, changed_files: List[str] = None) -> Dict[str, Any]:
        print(f"\nAnalyzing directory: {directory}")
        
        results = {}
        
        print("Running linting analysis...")
        results['linting'] = self.linting_analyzer.analyze_directory(directory)
        
        print("Running complexity analysis...")
        results['complexity'] = self.complexity_analyzer.analyze_directory(directory)
        
        print("Running duplication detection...")
        results['duplication'] = self.duplication_detector.detect_directory_duplication(directory)
        
        print("Running custom rules check...")
        results['custom_rules'] = self.custom_rules_checker.check_directory(directory)
        
        if self.dsl_rules:
            print("Running DSL rules check...")
            results['dsl_rules'] = self.dsl_checker.check_directory(directory)
        else:
            results['dsl_rules'] = {"all_violations": [], "summary": {"total": 0}, "note": "No DSL rules loaded"}
        
        print("Running impact analysis...")
        results['impact_analysis'] = self.impact_analyzer.analyze_directory(directory, changed_files)
        
        print("Running AI code review...")
        results['ai_review'] = self.ai_reviewer.review_directory(directory, results)
        
        print("Estimating review effort...")
        results['effort_estimate'] = self.effort_estimator.estimate_from_directory(
            directory, changed_files, results
        ).to_dict()
        
        if self.sonarqube:
            print("Running SonarQube analysis...")
            results['sonarqube'] = self.sonarqube.get_project_issues()
        else:
            results['sonarqube'] = {"issues": [], "summary": {}, "note": "SonarQube not enabled"}
        
        return results
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        results = {}
        
        if file_path.endswith('.py'):
            results['linting'] = self.linting_analyzer.run_pylint(file_path)
        elif any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx']):
            results['linting'] = self.linting_analyzer.run_eslint(file_path)
        else:
            results['linting'] = {"issues": [], "summary": {}}
        
        results['complexity'] = self.complexity_analyzer.analyze_file(file_path)
        results['duplication'] = self.duplication_detector.detect_file_duplication(file_path)
        results['custom_rules'] = self.custom_rules_checker.check_file(file_path)
        
        if self.dsl_rules:
            violations = self.dsl_checker.check_file(file_path)
            results['dsl_rules'] = {"violations": violations, "count": len(violations)}
        else:
            results['dsl_rules'] = {"violations": [], "count": 0}
        
        directory = os.path.dirname(file_path) or '.'
        results['impact_analysis'] = self.impact_analyzer.analyze_directory(directory, [file_path])
        
        ai_comments = self.ai_reviewer.review_file(file_path, results)
        results['ai_review'] = {
            "all_comments": [c.to_dict() for c in ai_comments],
            "file_comments": {file_path: [c.to_dict() for c in ai_comments]},
            "summary": self.ai_reviewer._generate_review_summary(ai_comments)
        }
        
        results['effort_estimate'] = self.effort_estimator.estimate_from_changes(
            [file_path], results
        ).to_dict()
        
        return results
    
    def generate_reports(self, analysis_results: Dict[str, Any], 
                          output_format: str = None) -> Dict[str, str]:
        output_format = output_format or self.config.get('output', {}).get('format', 'json')
        
        reports = {}
        
        if output_format in ['json', 'all']:
            print("Generating JSON report...")
            reports['json'] = self.report_generator.generate_json_report(analysis_results)
        
        if output_format in ['text', 'all']:
            print("Generating text report...")
            reports['text'] = self.report_generator.generate_text_report(analysis_results)
        
        return reports


def main():
    parser = argparse.ArgumentParser(description='Code Review Assistant Tool')
    parser.add_argument('--mode', choices=['pr', 'directory', 'file'], 
                        default='directory', help='Analysis mode')
    parser.add_argument('--path', help='Path to directory or file for analysis')
    parser.add_argument('--repo-owner', help='Repository owner')
    parser.add_argument('--repo-name', help='Repository name')
    parser.add_argument('--pr-number', type=int, help='Pull request number')
    parser.add_argument('--config', default='config/config.yaml', 
                        help='Path to config file')
    parser.add_argument('--rules', default='config/rules/custom_rules.yaml',
                        help='Path to custom rules file')
    parser.add_argument('--format', choices=['json', 'text', 'all'], 
                        help='Output format')
    parser.add_argument('--no-report', action='store_true', 
                        help='Do not generate report files')
    
    args = parser.parse_args()
    
    try:
        tool = CodeReviewTool(args.config, args.rules)
        
        if args.mode == 'pr':
            results = tool.review_pr(args.repo_owner, args.repo_name, args.pr_number)
        elif args.mode == 'file':
            if not args.path:
                parser.error("--path is required for file mode")
            results = tool.analyze_file(args.path)
            results = {'pr_info': {}, **results}
        else:
            if not args.path:
                args.path = os.getcwd()
            results = tool.analyze_directory(args.path)
            results = {'pr_info': {}, **results}
        
        tool.report_generator.print_summary(results)
        
        if not args.no_report:
            reports = tool.generate_reports(results, args.format)
            for format_type, report_path in reports.items():
                print(f"{format_type.upper()} report saved to: {report_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
