#!/usr/bin/env python
"""
贝叶斯网络库测试 - 完整版
"""

from bayesian_network import BayesianNetwork
import numpy as np


def test_basic_functionality():
    print("测试基本功能...")
    
    bn = BayesianNetwork("Test")
    
    bn.add_node("A", ["0", "1"])
    bn.add_node("B", ["0", "1"])
    
    bn.add_edge("A", "B")
    
    bn.set_cpt("A", {"0": 0.6, "1": 0.4})
    bn.set_cpt("B", {
        ("0", "0"): 0.8,
        ("0", "1"): 0.2,
        ("1", "0"): 0.3,
        ("1", "1"): 0.7,
    })
    
    print(f"  节点: {list(bn.nodes.keys())}")
    print(f"  边: {bn.edges}")
    print("  ✓ 基本功能通过")


def test_variable_elimination_heuristics():
    print("\n测试变量消元法的消元顺序启发式...")
    
    bn = BayesianNetwork("Test")
    
    bn.add_node("A", ["0", "1"])
    bn.add_node("B", ["0", "1"])
    bn.add_node("C", ["0", "1"])
    bn.add_node("D", ["0", "1"])
    
    bn.add_edge("A", "B")
    bn.add_edge("B", "C")
    bn.add_edge("C", "D")
    
    bn.set_cpt("A", {"0": 0.5, "1": 0.5})
    bn.set_cpt("B", {("0", "0"): 0.7, ("0", "1"): 0.3, ("1", "0"): 0.3, ("1", "1"): 0.7})
    bn.set_cpt("C", {("0", "0"): 0.8, ("0", "1"): 0.2, ("1", "0"): 0.2, ("1", "1"): 0.8})
    bn.set_cpt("D", {("0", "0"): 0.9, ("0", "1"): 0.1, ("1", "0"): 0.1, ("1", "1"): 0.9})
    
    evidence = {"A": "1"}
    query = ["D"]
    
    result_default = bn.variable_elimination(query, evidence, heuristic='min_degree')
    result_random = bn.variable_elimination(query, evidence, heuristic='random')
    result_min_fill = bn.variable_elimination(query, evidence, heuristic='min_fill')
    
    print(f"  最小度启发式 P(D=1 | A=1) = {result_default['D']['1']:.4f}")
    print(f"  随机顺序 P(D=1 | A=1) = {result_random['D']['1']:.4f}")
    print(f"  最小填充启发式 P(D=1 | A=1) = {result_min_fill['D']['1']:.4f}")
    
    assert abs(result_default['D']['1'] - result_random['D']['1']) < 1e-6, "不同启发式结果应一致"
    assert abs(result_default['D']['1'] - result_min_fill['D']['1']) < 1e-6, "不同启发式结果应一致"
    print("  ✓ 消元顺序启发式通过")


def test_gibbs_sampling_convergence():
    print("\n测试吉布斯采样的Gelman-Rubin收敛诊断...")
    
    bn = BayesianNetwork("Test")
    
    bn.add_node("A", ["0", "1"])
    bn.add_node("B", ["0", "1"])
    
    bn.add_edge("A", "B")
    
    bn.set_cpt("A", {"0": 0.6, "1": 0.4})
    bn.set_cpt("B", {
        ("0", "0"): 0.8,
        ("0", "1"): 0.2,
        ("1", "0"): 0.3,
        ("1", "1"): 0.7,
    })
    
    np.random.seed(42)
    result_with_conv = bn.gibbs_sampling(
        ["A"], evidence={"B": "1"},
        n_samples=2000, burn_in=500,
        n_chains=3, check_convergence=True,
        gr_threshold=1.1, max_iter=5
    )
    
    p_ab = 0.4 * 0.7
    p_b = 0.6 * 0.2 + 0.4 * 0.7
    expected = p_ab / p_b
    
    print(f"  带收敛诊断 P(A=1 | B=1) ≈ {result_with_conv['A']['1']:.4f}")
    print(f"  精确值 P(A=1 | B=1) = {expected:.4f}")
    
    assert abs(result_with_conv['A']['1'] - expected) < 0.05, "误差太大"
    print("  ✓ Gelman-Rubin收敛诊断通过")


def test_em_missing_data():
    print("\n测试EM算法处理缺失数据...")
    
    bn = BayesianNetwork("Test")
    
    bn.add_node("A", ["0", "1"])
    bn.add_node("B", ["0", "1"])
    
    bn.add_edge("A", "B")
    
    np.random.seed(42)
    training_data = []
    for _ in range(2000):
        a = "1" if np.random.random() < 0.4 else "0"
        if a == "0":
            b = "1" if np.random.random() < 0.2 else "0"
        else:
            b = "1" if np.random.random() < 0.7 else "0"
        training_data.append({"A": a, "B": b})
    
    data_with_missing = []
    for sample in training_data:
        new_sample = sample.copy()
        if np.random.random() < 0.3:
            del new_sample["A"]
        if np.random.random() < 0.3:
            del new_sample["B"]
        data_with_missing.append(new_sample)
    
    print(f"  完整数据样本: {len(training_data)}")
    print(f"  含缺失数据样本: {len(data_with_missing)}")
    
    bn.set_cpt("A", {"0": 0.5, "1": 0.5})
    bn.set_cpt("B", {("0", "0"): 0.5, ("0", "1"): 0.5, ("1", "0"): 0.5, ("1", "1"): 0.5})
    
    bn.fit(data_with_missing, smoothing=1.0, use_em=True, max_em_iter=50, verbose=False)
    
    cpt_a = bn.get_cpt("A")
    print(f"  EM学习 P(A=1) = {cpt_a.table[1]:.4f} (期望: 0.4)")
    
    cpt_b = bn.get_cpt("B")
    print(f"  EM学习 P(B=1 | A=0) = {cpt_b.table[0][1]:.4f} (期望: 0.2)")
    print(f"  EM学习 P(B=1 | A=1) = {cpt_b.table[1][1]:.4f} (期望: 0.7)")
    
    assert abs(cpt_a.table[1] - 0.4) < 0.1, "P(A)学习误差太大"
    assert abs(cpt_b.table[0][1] - 0.2) < 0.15, "P(B|A=0)学习误差太大"
    assert abs(cpt_b.table[1][1] - 0.7) < 0.15, "P(B|A=1)学习误差太大"
    print("  ✓ EM算法通过")


def test_structure_learning_k2():
    print("\n测试K2结构学习算法...")
    
    true_bn = BayesianNetwork("True")
    true_bn.add_node("A", ["0", "1"])
    true_bn.add_node("B", ["0", "1"])
    true_bn.add_node("C", ["0", "1"])
    
    true_bn.add_edge("A", "B")
    true_bn.add_edge("B", "C")
    
    true_bn.set_cpt("A", {"0": 0.6, "1": 0.4})
    true_bn.set_cpt("B", {("0", "0"): 0.7, ("0", "1"): 0.3, ("1", "0"): 0.3, ("1", "1"): 0.7})
    true_bn.set_cpt("C", {("0", "0"): 0.8, ("0", "1"): 0.2, ("1", "0"): 0.2, ("1", "1"): 0.8})
    
    np.random.seed(42)
    data = true_bn.sample(500)
    
    learned_bn = BayesianNetwork("K2-Learned")
    learned_bn.add_node("A", ["0", "1"])
    learned_bn.add_node("B", ["0", "1"])
    learned_bn.add_node("C", ["0", "1"])
    
    learned_bn.learn_structure_k2(
        data,
        node_order=["A", "B", "C"],
        max_parents=2,
        score='bic'
    )
    
    print(f"  真实边: {true_bn.edges}")
    print(f"  学习边: {learned_bn.edges}")
    
    learned_edge_set = set(learned_bn.edges)
    true_edge_set = set(true_bn.edges)
    correct_edges = learned_edge_set & true_edge_set
    
    print(f"  正确学习的边: {correct_edges}")
    print(f"  正确率: {len(correct_edges)}/{len(true_edge_set)}")
    
    assert len(correct_edges) >= 1, "至少应该学习到一条正确的边"
    print("  ✓ K2结构学习通过")


def test_causal_inference():
    print("\n测试因果推断接口...")
    
    bn = BayesianNetwork("Causal")
    bn.add_node("X", ["0", "1"])
    bn.add_node("Y", ["0", "1"])
    bn.add_node("Z", ["0", "1"])
    
    bn.add_edge("X", "Y")
    bn.add_edge("Y", "Z")
    
    bn.set_cpt("X", {"0": 0.5, "1": 0.5})
    bn.set_cpt("Y", {("0", "0"): 0.6, ("0", "1"): 0.4, ("1", "0"): 0.3, ("1", "1"): 0.7})
    bn.set_cpt("Z", {("0", "0"): 0.7, ("0", "1"): 0.3, ("1", "0"): 0.2, ("1", "1"): 0.8})
    
    print("  网络: X→Y→Z")
    
    cond_prob = bn.variable_elimination(["Z"], evidence={"X": "1"})
    print(f"  P(Z=1 | X=1) = {cond_prob['Z']['1']:.4f}")
    
    do_prob = bn.causal_effect("X", "1", "Z", "1")
    print(f"  P(Z=1 | do(X=1)) = {do_prob:.4f}")
    
    assert do_prob > 0, "因果效应应该大于0"
    
    ace = bn.average_causal_effect("X", "1", "0", "Z", "1")
    print(f"  ACE = {ace:.4f}")
    
    intervened = bn.do_intervention({"X": "1"})
    print(f"  干预后边: {intervened.edges}")
    
    assert ("X", "Y") in intervened.edges
    assert ("Y", "Z") in intervened.edges
    print("  ✓ 因果推断通过")


def test_sensitivity_analysis():
    print("\n测试敏感性分析...")
    
    bn = BayesianNetwork("Sensitivity")
    bn.add_node("A", ["0", "1"])
    bn.add_node("B", ["0", "1"])
    
    bn.add_edge("A", "B")
    
    bn.set_cpt("A", {"0": 0.6, "1": 0.4})
    bn.set_cpt("B", {("0", "0"): 0.7, ("0", "1"): 0.3, ("1", "0"): 0.2, ("1", "1"): 0.8})
    
    result = bn.sensitivity_analysis(
        query=["B"],
        evidence=None,
        perturbation=0.1,
        method='one_at_a_time'
    )
    
    print(f"  原始结果: {result['original_result']}")
    print(f"  敏感性: {result['sensitivity']}")
    
    assert 'A' in result['sensitivity']
    assert 'B' in result['sensitivity']
    
    result2 = bn.sensitivity_analysis(
        query=["B"],
        evidence={"A": "1"},
        perturbation=0.05,
        method='derivative'
    )
    
    print(f"  导数法敏感性: {result2['sensitivity']}")
    print("  ✓ 敏感性分析通过")


def test_sampling():
    print("\n测试网络采样...")
    
    bn = BayesianNetwork("Test")
    
    bn.add_node("A", ["0", "1"])
    bn.set_cpt("A", {"0": 0.5, "1": 0.5})
    
    samples = bn.sample(100)
    print(f"  生成了 {len(samples)} 个样本")
    assert len(samples) == 100
    print("  ✓ 采样通过")


def test_cycle_detection():
    print("\n测试环检测...")
    
    bn = BayesianNetwork("Test")
    
    bn.add_node("A", ["0", "1"])
    bn.add_node("B", ["0", "1"])
    bn.add_node("C", ["0", "1"])
    
    bn.add_edge("A", "B")
    bn.add_edge("B", "C")
    
    try:
        bn.add_edge("C", "A")
        assert False, "应该检测到环"
    except ValueError as e:
        print(f"  正确检测到环: {e}")
        print("  ✓ 环检测通过")


if __name__ == "__main__":
    print("=" * 60)
    print("贝叶斯网络库测试 - 完整版")
    print("=" * 60)
    
    try:
        test_basic_functionality()
        test_variable_elimination_heuristics()
        test_gibbs_sampling_convergence()
        test_em_missing_data()
        test_structure_learning_k2()
        test_causal_inference()
        test_sensitivity_analysis()
        test_sampling()
        test_cycle_detection()
        
        print("\n" + "=" * 60)
        print("所有测试通过! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
