#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.code_review_tool import CodeReviewTool


def example_directory_analysis():
    print("=" * 60)
    print("Example 1: Analyze a directory")
    print("=" * 60)
    
    tool = CodeReviewTool()
    
    current_dir = os.path.join(os.path.dirname(__file__), "test_code")
    os.makedirs(current_dir, exist_ok=True)
    
    create_test_files(current_dir)
    
    results = tool.analyze_directory(current_dir)
    results['pr_info'] = {"title": "Example Analysis", "author": "Test User"}
    
    tool.report_generator.print_summary(results)
    
    reports = tool.generate_reports(results, "all")
    print(f"\nReports generated:")
    for fmt, path in reports.items():
        print(f"  {fmt}: {path}")


def example_file_analysis():
    print("\n" + "=" * 60)
    print("Example 2: Analyze a single file")
    print("=" * 60)
    
    tool = CodeReviewTool()
    
    test_file = os.path.join(os.path.dirname(__file__), "test_code", "sample.py")
    result = tool.analyze_file(test_file)
    
    print(f"File: {test_file}")
    print(f"Linting issues: {len(result['linting'].get('issues', []))}")
    print(f"Complexity: {result['complexity'].get('average_ccn', 0):.2f} avg CCN")
    print(f"Custom rules violations: {result['custom_rules'].get('summary', {}).get('total', 0)}")


def create_test_files(directory: str):
    sample_py = os.path.join(directory, "sample.py")
    with open(sample_py, 'w') as f:
        f.write('''
def very_complex_function(a, b, c, d, e, f, g):
    """This function has too many arguments and high complexity"""
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            if g > 0:
                                return "deep nesting"
                            else:
                                return "g is negative"
                        else:
                            return "f is negative"
                    else:
                        return "e is negative"
                else:
                    return "d is negative"
            else:
                return "c is negative"
        else:
            return "b is negative"
    else:
        return "a is negative"


def another_function():
    x = 1
    y = 2
    z = 3
    return x + y + z


password = "my_secret_password_123"


class badClassName:
    def MethodName(self):
        pass
''')
    
    sample_js = os.path.join(directory, "sample.js")
    with open(sample_js, 'w') as f:
        f.write('''
function calculateTotal(a, b, c, d, e) {
    let sum = 0;
    sum += a;
    sum += b;
    sum += c;
    sum += d;
    sum += e;
    console.log("Total is: " + sum);
    return sum;
}

function duplicateFunction() {
    let sum = 0;
    sum += a;
    sum += b;
    sum += c;
    sum += d;
    sum += e;
    console.log("Total is: " + sum);
    return sum;
}
''')


if __name__ == "__main__":
    example_directory_analysis()
    example_file_analysis()
