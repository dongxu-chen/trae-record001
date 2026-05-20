#!/usr/bin/env python3
from k8s_health_checker import K8sHealthChecker
import yaml

def example_basic_check():
    print("=== Example 1: Basic Health Check ===")
    checker = K8sHealthChecker()
    report = checker.run_full_check(namespace="default")
    print(checker.generate_report())
    print()

def example_with_auto_restart():
    print("=== Example 2: Check with Auto-Restart (Dry Run) ===")
    checker = K8sHealthChecker()
    report = checker.run_full_check(
        namespace="all",
        auto_restart=True,
        max_restarts=3,
        dry_run=True
    )
    print(checker.generate_report())
    print()

def example_check_node_pdb():
    print("=== Example 3: Check PDB for Specific Node ===")
    checker = K8sHealthChecker()
    node_name = "worker-node-1"
    ok, violations = checker.check_pdb_for_node(node_name)
    if ok:
        print(f"Node {node_name} is safe to drain")
    else:
        print(f"Node {node_name} has PDB violations:")
        for v in violations:
            print(f"  - {v}")
    print()

def example_email_report():
    print("=== Example 4: Send Email Report ===")
    checker = K8sHealthChecker()
    checker.run_full_check()
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    email_config = config.get('email', {})
    checker.send_report_email(
        smtp_server=email_config.get('smtp_server'),
        smtp_port=email_config.get('smtp_port'),
        sender=email_config.get('sender'),
        recipients=email_config.get('recipients', []),
        username=email_config.get('username'),
        password=email_config.get('password'),
        use_tls=email_config.get('use_tls', True)
    )
    print("Email sent (check logs for details)")
    print()

def example_drain_node():
    print("=== Example 5: Drain Node (Dry Run) ===")
    checker = K8sHealthChecker()
    node_name = "worker-node-1"
    success = checker.drain_node(node_name, dry_run=True, ignore_pdb=False)
    if success:
        print(f"Node {node_name} drain successful (dry run)")
    else:
        print(f"Node {node_name} drain failed")
    print(checker.generate_report())
    print()

if __name__ == "__main__":
    print("K8s Health Checker - Usage Examples")
    print("=" * 50)
    
    try:
        example_basic_check()
        example_with_auto_restart()
        example_check_node_pdb()
        example_drain_node()
    except Exception as e:
        print(f"Error running examples: {e}")
        print("\nNote: Make sure you have access to a Kubernetes cluster")
        print("and kubeconfig is properly configured.")
