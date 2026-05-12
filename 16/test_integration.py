#!/usr/bin/env python3
"""Integration tests for Ansible development environment playbook.

This script tests the structure, ansible syntax, and runs integration checks for the development
environment configuration.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List


class TestDevelopmentEnvironment:
    """Test suite for the development environment Ansible playbook."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.roles_dir = self.project_root / 'roles'
        self.required_roles = ['common', 'java', 'python', 'nodejs']
        
    def run_command(self, command: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=check
        )
    
    def test_directory_structure(self) -> bool:
        """Test that the directory structure is correct."""
        print("Testing directory structure...")
        
        if not (self.project_root / 'playbook.yml').exists():
            print("  ERROR: playbook.yml not found")
            return False
        
        for role in self.required_roles:
            role_path = self.roles_dir / role
            if not role_path.exists():
                print(f"  ERROR: Role '{role}' not found")
                return False
            
            required_dirs = ['tasks', 'defaults', 'meta']
            for d in required_dirs:
                dir_path = role_path / d
                if not dir_path.exists():
                    print(f"  ERROR: Directory '{d}' not found in role '{role}'")
                    return False
        
        vars_path = self.roles_dir / 'common' / 'vars' / 'main.yml'
        if not vars_path.exists():
            print("  ERROR: common/vars/main.yml not found")
            return False
        
        print("  Directory structure test passed!")
        return True
    
    def test_playbook_syntax(self) -> bool:
        """Test Ansible playbook syntax using ansible-playbook --syntax-check."""
        print("Testing Ansible playbook syntax...")
        
        try:
            result = self.run_command([
                'ansible-playbook',
                '--syntax-check',
                str(self.project_root / 'playbook.yml')
            ], check=False)
            
            if result.returncode != 0:
                print(f"  Syntax check failed: {result.stderr}")
                return False
        except FileNotFoundError:
            print("  WARNING: ansible-playbook not available, skipping syntax check")
            return True
        
        print("  Playbook syntax test passed!")
        return True
    
    def test_role_dependencies(self) -> bool:
        """Test that role dependencies are correctly configured."""
        print("Testing role dependencies...")
        
        dependent_roles = ['java', 'python', 'nodejs']
        for role_name in dependent_roles:
            meta_path = self.roles_dir / role_name / 'meta' / 'main.yml'
            
            with open(meta_path, 'r') as f:
                lines = f.readlines()
            
            dependencies_section = False
            has_common = False
            
            for line in lines:
                line_stripped = line.strip()
                if line_stripped == 'dependencies:':
                    dependencies_section = True
                    continue
                if dependencies_section:
                    if line_stripped.startswith('-') and 'common' in line:
                        has_common = True
                        break
                    if line_stripped and not line_stripped.startswith(' ') and not line_stripped.startswith('-'):
                        break
            
            if not has_common:
                print(f"  ERROR: Role '{role_name}' should depend on 'common'")
                return False
        
        print("  Role dependencies test passed!")
        return True
    
    def test_common_encrypted_vars(self) -> bool:
        """Test that common role has encrypted variables structure."""
        print("Testing common role encrypted variables structure...")
        
        vars_path = self.roles_dir / 'common' / 'vars' / 'main.yml'
        
        with open(vars_path, 'r') as f:
            vars_content = f.read()
        
        if 'vault_common_packages' not in vars_content:
            print("  ERROR: vault_common_packages should be defined for ansible-vault")
            return False
        
        defaults_path = self.roles_dir / 'common' / 'defaults' / 'main.yml'
        
        with open(defaults_path, 'r') as f:
            defaults_content = f.read()
        
        if 'vault_common_packages' not in defaults_content:
            print("  ERROR: defaults should reference vault variables")
            return False
        
        print("  Common encrypted variables test passed!")
        return True
    
    def test_python_pyenv_support(self) -> bool:
        """Test that python role has pyenv support."""
        print("Testing python role pyenv support...")
        
        defaults_path = self.roles_dir / 'python' / 'defaults' / 'main.yml'
        
        with open(defaults_path, 'r') as f:
            defaults_content = f.read()
        
        checks = [
            ('python_install_method: pyenv', 'Default install method should be pyenv'),
            ('python_versions', 'python_versions should be defined'),
            ('python_global_version', 'python_global_version should be defined'),
        ]
        
        for check_str, error_msg in checks:
            if check_str not in defaults_content:
                print(f"  ERROR: {error_msg}")
                return False
        
        pyenv_tasks_path = self.roles_dir / 'python' / 'tasks' / 'pyenv.yml'
        if not pyenv_tasks_path.exists():
            print("  ERROR: pyenv.yml should exist")
            return False
        
        print("  Python pyenv support test passed!")
        return True
    
    def test_playbook_roles_integration(self) -> bool:
        """Test that playbook correctly includes all roles."""
        print("Testing playbook roles integration...")
        
        playbook_path = self.project_root / 'playbook.yml'
        
        with open(playbook_path, 'r') as f:
            playbook_content = f.read()
        
        for role in self.required_roles:
            role_checks = [
                f"- role: {role}",
                f'- role: "{role}"',
                f"- role: '{role}'",
            ]
            found = any(check in playbook_content for check in role_checks)
            if not found:
                print(f"  ERROR: Role '{role}' should be in playbook")
                return False
        
        print("  Playbook roles integration test passed!")
        return True
    
    def run_all_tests(self) -> bool:
        """Run all tests and return success status."""
        print("="*60)
        print("Running Development Environment Integration Tests")
        print("="*60)
        
        tests = [
            ('Directory Structure', self.test_directory_structure),
            ('Playbook Syntax', self.test_playbook_syntax),
            ('Role Dependencies', self.test_role_dependencies),
            ('Common Encrypted Vars', self.test_common_encrypted_vars),
            ('Python Pyenv Support', self.test_python_pyenv_support),
            ('Playbook Roles Integration', self.test_playbook_roles_integration),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"  Test '{test_name}' failed with exception: {e}")
                results[test_name] = False
        
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        
        all_passed = True
        for test_name, passed in results.items():
            status = "PASSED" if passed else "FAILED"
            print(f"  {test_name}: {status}")
            if not passed:
                all_passed = False
        
        print("="*60)
        if all_passed:
            print("All tests passed!")
        else:
            print("Some tests failed")
        print("="*60)
        
        return all_passed


def main():
    tester = TestDevelopmentEnvironment()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
