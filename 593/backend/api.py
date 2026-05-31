#!/usr/bin/env python3
import os
from flask import Flask, jsonify, request
from flask_cors import CORS

from .git_utils import GitUtils
from .config import Config
from .rule_engine import Report, CheckStatus
from .checkers.branch_naming import BranchNamingChecker
from .checkers.merge_direction import MergeDirectionChecker
from .checkers.pr_size import PRSizeChecker
from .checkers.commit_frequency import CommitFrequencyChecker
from .checkers.branch_age import BranchAgeChecker
from .checkers.commit_quality import CommitQualityChecker
from .checkers.team_report import TeamReportChecker
from .auto_fix import AutoFix
from .ci_integration import CIIntegration


def create_app():
    app = Flask(__name__)
    CORS(app)

    repo_path = os.getenv('GIT_REPO_PATH', '.')
    config = Config()
    
    try:
        git_utils = GitUtils(repo_path)
    except Exception:
        git_utils = None

    auto_fix = AutoFix(git_utils, config) if git_utils else None
    ci = CIIntegration(repo_path) if git_utils else None

    def make_error_response(message: str, status_code: int = 400):
        return jsonify({
            'error': message,
            'status': 'error'
        }), status_code

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'repo_path': repo_path,
            'repo_loaded': git_utils is not None
        })

    @app.route('/api/branches', methods=['GET'])
    def get_branches():
        if not git_utils:
            return make_error_response('Repository not loaded')
        
        try:
            branches = git_utils.get_all_branches()
            current = git_utils.get_current_branch()
            return jsonify({
                'branches': branches,
                'current': current
            })
        except Exception as e:
            return make_error_response(str(e), 500)

    @app.route('/api/check/branch-naming', methods=['GET'])
    def check_branch_naming():
        if not git_utils:
            return make_error_response('Repository not loaded')
        
        branch = request.args.get('branch')
        checker = BranchNamingChecker(git_utils, config)
        result = checker.check(branch)
        return jsonify(result.to_dict())

    @app.route('/api/check/merge-direction', methods=['GET'])
    def check_merge_direction():
        if not git_utils:
            return make_error_response('Repository not loaded')
        
        source = request.args.get('source')
        target = request.args.get('target', 'develop')
        
        if not source:
            return make_error_response('Source branch is required')
        
        checker = MergeDirectionChecker(git_utils, config)
        result = checker.check(source, target)
        return jsonify(result.to_dict())

    @app.route('/api/check/pr-size', methods=['GET'])
    def check_pr_size():
        if not git_utils:
            return make_error_response('Repository not loaded')
        
        source = request.args.get('source')
        target = request.args.get('target', 'develop')
        
        if not source:
            return make_error_response('Source branch is required')
        
        checker = PRSizeChecker(git_utils, config)
        result = checker.check(source, target)
        return jsonify(result.to_dict())

    @app.route('/api/check/commit-frequency', methods=['GET'])
    def check_commit_frequency():
        if not git_utils:
            return make_error_response('Repository not loaded')
        
        branch = request.args.get('branch')
        days = int(request.args.get('days', 7))
        
        checker = CommitFrequencyChecker(git_utils, config)
        result = checker.check(branch, days)
        return jsonify(result.to_dict())

    @app.route('/api/check/conflicts', methods=['GET'])
    def check_conflicts():
        if not git_utils or not auto_fix:
            return make_error_response('Repository not loaded')
        
        source = request.args.get('source')
        target = request.args.get('target', 'develop')
        
        if not source:
            source = git_utils.get_current_branch()
        
        result = auto_fix.detect_conflicts(source, target)
        return jsonify(result.to_dict())

    @app.route('/api/check/branch-age', methods=['GET'])
    def check_branch_age():
        if not git_utils:
            return make_error_response('Repository not loaded')
        
        source = request.args.get('source')
        target = request.args.get('target', 'develop')
        
        if not source:
            source = git_utils.get_current_branch()
        
        checker = BranchAgeChecker(git_utils, config)
        result = checker.check(source, target)
        return jsonify(result.to_dict())

    @app.route('/api/check/branch-age/all', methods=['GET'])
    def check_all_branch_ages():
        if not git_utils:
            return make_error_response('Repository not loaded')
        
        target = request.args.get('target', 'develop')
        checker = BranchAgeChecker(git_utils, config)
        result = checker.check_all_branches(target)
        return jsonify(result.to_dict())

    @app.route('/api/check/commit-quality', methods=['GET'])
    def check_commit_quality():
        if not git_utils:
            return make_error_response('Repository not loaded')
        
        branch = request.args.get('branch')
        days = int(request.args.get('days', 30))
        
        checker = CommitQualityChecker(git_utils, config)
        result = checker.check(branch, days)
        return jsonify(result.to_dict())

    @app.route('/api/team-report', methods=['GET'])
    def get_team_report():
        if not git_utils:
            return make_error_response('Repository not loaded')
        
        days = int(request.args.get('days', 30))
        checker = TeamReportChecker(git_utils, config)
        result = checker.check(days=days)
        return jsonify(result.to_dict())

    @app.route('/api/check/all', methods=['GET'])
    def check_all():
        if not git_utils or not ci:
            return make_error_response('Repository not loaded')
        
        source = request.args.get('source')
        target = request.args.get('target', 'develop')
        output_format = request.args.get('format', 'json')
        
        if not source:
            source = git_utils.get_current_branch()

        report = ci.run_full_check(source, target)

        if output_format == 'checklist':
            return jsonify({
                'report_id': report.report_id,
                'format': 'checklist',
                'content': report.to_checklist()
            })
        elif output_format == 'console':
            return jsonify({
                'report_id': report.report_id,
                'format': 'console',
                'content': ci.output_console(report)
            })
        
        return jsonify(report.to_dict())

    @app.route('/api/report/<report_id>', methods=['GET'])
    def get_report(report_id: str):
        if not git_utils or not ci:
            return make_error_response('Repository not loaded')
        
        source = request.args.get('source')
        target = request.args.get('target', 'develop')
        output_format = request.args.get('format', 'json')
        
        if not source:
            source = git_utils.get_current_branch()

        report = ci.run_full_check(source, target)
        
        if output_format == 'checklist':
            return jsonify({
                'report_id': report.report_id,
                'format': 'checklist',
                'content': report.to_checklist()
            })
        
        return jsonify(report.to_dict())

    @app.route('/api/fix/branch-name', methods=['POST'])
    def fix_branch_name():
        if not git_utils or not auto_fix:
            return make_error_response('Repository not loaded')
        
        data = request.get_json() or {}
        branch = data.get('branch')
        dry_run = data.get('dry_run', True)
        
        result = auto_fix.fix_branch_name(branch, dry_run)
        return jsonify(result)

    @app.route('/api/fix/squash-commits', methods=['POST'])
    def fix_squash_commits():
        if not git_utils or not auto_fix:
            return make_error_response('Repository not loaded')
        
        data = request.get_json() or {}
        branch = data.get('branch')
        num_commits = data.get('num_commits')
        message = data.get('message')
        
        result = auto_fix.fix_squash_commits(branch, num_commits, message)
        return jsonify(result)

    @app.route('/api/config', methods=['GET'])
    def get_config():
        return jsonify(config.rules)

    @app.route('/api/config', methods=['POST'])
    def update_config():
        data = request.get_json()
        return jsonify({'message': 'Config update not implemented yet', 'data': data})

    return app


def main():
    app = create_app()
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
