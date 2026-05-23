from bayesian_network import BayesianNetwork
import numpy as np
from itertools import product


def example_1_structure_learning_k2():
    print("=" * 60)
    print("示例1: 结构学习 - K2算法")
    print("=" * 60)

    true_bn = BayesianNetwork("True-Network")
    true_bn.add_node("A", ["0", "1"])
    true_bn.add_node("B", ["0", "1"])
    true_bn.add_node("C", ["0", "1"])
    true_bn.add_node("D", ["0", "1"])

    true_bn.add_edge("A", "B")
    true_bn.add_edge("B", "C")
    true_bn.add_edge("C", "D")

    true_bn.set_cpt("A", {"0": 0.6, "1": 0.4})
    true_bn.set_cpt("B", {("0", "0"): 0.7, ("0", "1"): 0.3, ("1", "0"): 0.2, ("1", "1"): 0.8})
    true_bn.set_cpt("C", {("0", "0"): 0.8, ("0", "1"): 0.2, ("1", "0"): 0.1, ("1", "1"): 0.9})
    true_bn.set_cpt("D", {("0", "0"): 0.9, ("0", "1"): 0.1, ("1", "0"): 0.1, ("1", "1"): 0.9})

    np.random.seed(42)
    n_samples = 500
    training_data = true_bn.sample(n_samples)

    print(f"\n真实网络结构:")
    print(f"  边: {true_bn.edges}")
    print(f"\n生成 {n_samples} 个训练样本")

    learned_bn = BayesianNetwork("K2-Learned")
    learned_bn.add_node("A", ["0", "1"])
    learned_bn.add_node("B", ["0", "1"])
    learned_bn.add_node("C", ["0", "1"])
    learned_bn.add_node("D", ["0", "1"])

    node_order = ["A", "B", "C", "D"]

    print("\n使用K2算法学习结构...")
    learned_bn.learn_structure_k2(
        training_data,
        node_order=node_order,
        max_parents=2,
        score='bic'
    )

    print(f"\n学习到的网络结构:")
    print(f"  边: {learned_bn.edges}")

    print("\n学习到的CPTs:")
    for node in ["A", "B", "C", "D"]:
        print(f"  P({node} | parents):")
        print(f"    {learned_bn.cpts[node].table}")

    return learned_bn, true_bn


def example_2_structure_learning_hill_climb():
    print("\n" + "=" * 60)
    print("示例2: 结构学习 - 爬山法")
    print("=" * 60)

    true_bn = BayesianNetwork("True-Network")
    true_bn.add_node("X", ["0", "1"])
    true_bn.add_node("Y", ["0", "1"])
    true_bn.add_node("Z", ["0", "1"])

    true_bn.add_edge("X", "Y")
    true_bn.add_edge("Y", "Z")

    true_bn.set_cpt("X", {"0": 0.5, "1": 0.5})
    true_bn.set_cpt("Y", {("0", "0"): 0.6, ("0", "1"): 0.4, ("1", "0"): 0.3, ("1", "1"): 0.7})
    true_bn.set_cpt("Z", {("0", "0"): 0.7, ("0", "1"): 0.3, ("1", "0"): 0.2, ("1", "1"): 0.8})

    np.random.seed(42)
    n_samples = 1000
    training_data = true_bn.sample(n_samples)

    print(f"\n真实网络结构:")
    print(f"  边: {true_bn.edges}")

    learned_bn = BayesianNetwork("HillClimb-Learned")
    learned_bn.add_node("X", ["0", "1"])
    learned_bn.add_node("Y", ["0", "1"])
    learned_bn.add_node("Z", ["0", "1"])

    print("\n使用爬山法学习结构...")
    learned_bn.learn_structure_hill_climb(
        training_data,
        max_iter=50,
        score='bic',
        verbose=True
    )

    print(f"\n学习到的网络结构:")
    print(f"  边: {learned_bn.edges}")

    return learned_bn, true_bn


def example_3_causal_inference():
    print("\n" + "=" * 60)
    print("示例3: 因果推断 - Do-Calculus")
    print("=" * 60)

    bn = BayesianNetwork("Causal-Network")

    bn.add_node("Smoking", ["yes", "no"])
    bn.add_node("Tar", ["high", "low"])
    bn.add_node("Cancer", ["yes", "no"])

    bn.add_edge("Smoking", "Tar")
    bn.add_edge("Tar", "Cancer")
    bn.add_edge("Smoking", "Cancer")

    bn.set_cpt("Smoking", {"yes": 0.5, "no": 0.5})
    bn.set_cpt("Tar", {
        ("yes", "high"): 0.95, ("yes", "low"): 0.05,
        ("no", "high"): 0.05, ("no", "low"): 0.95,
    })
    bn.set_cpt("Cancer", {
        ("yes", "high", "yes"): 0.90, ("yes", "high", "no"): 0.10,
        ("yes", "low", "yes"): 0.70, ("yes", "low", "no"): 0.30,
        ("no", "high", "yes"): 0.30, ("no", "high", "no"): 0.70,
        ("no", "low", "yes"): 0.05, ("no", "low", "no"): 0.95,
    })

    print("\n网络结构 (吸烟→焦油→癌症, 吸烟→癌症)")
    print(f"边: {bn.edges}")

    print("\n1. 观察概率 P(Cancer=yes):")
    result = bn.variable_elimination(["Cancer"])
    print(f"   P(Cancer=yes) = {result['Cancer']['yes']:.4f}")

    print("\n2. 条件概率 P(Cancer=yes | Smoking=yes):")
    result = bn.variable_elimination(["Cancer"], evidence={"Smoking": "yes"})
    print(f"   P(Cancer=yes | Smoking=yes) = {result['Cancer']['yes']:.4f}")

    print("\n3. 干预概率 P(Cancer=yes | do(Smoking=yes)):")
    causal_effect_yes = bn.causal_effect(
        treatment="Smoking",
        treatment_value="yes",
        outcome="Cancer",
        outcome_value="yes"
    )
    print(f"   P(Cancer=yes | do(Smoking=yes)) = {causal_effect_yes:.4f}")

    print("\n4. 干预概率 P(Cancer=yes | do(Smoking=no)):")
    causal_effect_no = bn.causal_effect(
        treatment="Smoking",
        treatment_value="no",
        outcome="Cancer",
        outcome_value="yes"
    )
    print(f"   P(Cancer=yes | do(Smoking=no)) = {causal_effect_no:.4f}")

    print("\n5. 平均因果效应 ACE:")
    ace = bn.average_causal_effect(
        treatment="Smoking",
        treatment_value1="yes",
        treatment_value2="no",
        outcome="Cancer",
        outcome_value="yes"
    )
    print(f"   ACE = P(Cancer|do(Smoking=yes)) - P(Cancer|do(Smoking=no))")
    print(f"   ACE = {ace:.4f}")

    print("\n6. 干预后的网络 (do(Smoking=yes)):")
    intervened = bn.do_intervention({"Smoking": "yes"})
    print(f"   干预后边: {intervened.edges}")
    print(f"   (注意: 删除了指向Smoking的所有边")

    return bn


def example_4_sensitivity_analysis():
    print("\n" + "=" * 60)
    print("示例4: 敏感性分析")
    print("=" * 60)

    bn = BayesianNetwork("Sensitivity-Test")

    bn.add_node("Cloudy", ["yes", "no"])
    bn.add_node("Rain", ["yes", "no"])
    bn.add_node("Sprinkler", ["on", "off"])
    bn.add_node("GrassWet", ["yes", "no"])

    bn.add_edge("Cloudy", "Rain")
    bn.add_edge("Cloudy", "Sprinkler")
    bn.add_edge("Rain", "GrassWet")
    bn.add_edge("Sprinkler", "GrassWet")

    bn.set_cpt("Cloudy", {"yes": 0.5, "no": 0.5})
    bn.set_cpt("Sprinkler", {
        ("yes", "on"): 0.1, ("yes", "off"): 0.9,
        ("no", "on"): 0.5, ("no", "off"): 0.5,
    })
    bn.set_cpt("Rain", {
        ("yes", "yes"): 0.8, ("yes", "no"): 0.2,
        ("no", "yes"): 0.2, ("no", "no"): 0.8,
    })
    bn.set_cpt("GrassWet", {
        ("yes", "on", "yes"): 0.99, ("yes", "on", "no"): 0.01,
        ("yes", "off", "yes"): 0.9, ("yes", "off", "no"): 0.1,
        ("no", "on", "yes"): 0.9, ("no", "on", "no"): 0.1,
        ("no", "off", "yes"): 0.0, ("no", "off", "no"): 1.0,
    })

    query = ["Rain"]
    evidence = {"GrassWet": "yes"}

    print("\n查询: P(Rain | GrassWet=yes)")
    result = bn.variable_elimination(query, evidence)
    print(f"  P(Rain=yes | GrassWet=yes) = {result['Rain']['yes']:.4f}")

    print("\n1. 一次一个参数扰动分析 (扰动幅度 = 0.1):")
    sens_result = bn.sensitivity_analysis(
        query=query,
        evidence=evidence,
        perturbation=0.1,
        method='one_at_a_time'
    )

    print("\n各节点参数扰动对查询结果的最大影响:")
    for node, sens in sens_result['sensitivity'].items():
        for q_var, change in sens.items():
            print(f"  {node} → {q_var}: 最大变化 = {change:.6f}")

    print("\n2. 导数法敏感性分析:")
    sens_result2 = bn.sensitivity_analysis(
        query=query,
        evidence=evidence,
        perturbation=0.1,
        method='derivative'
    )

    print("\n各节点参数的平均导数估计:")
    for node, sens in sens_result2['sensitivity'].items():
        for q_var, deriv in sens.items():
            print(f"  {node} → {q_var}: 平均导数 = {deriv:.6f}")

    most_sensitive = max(
        ((node, list(sens.values())[0])
        for node, sens in sens_result['sensitivity'].items()
    )
    print(f"\n最敏感的节点: {most_sensitive[0]} (最大变化: {most_sensitive[1]:.6f}")

    return bn


def example_5_combined():
    print("\n" + "=" * 60)
    print("示例5: 综合演示 - 学习+推理+分析")
    print("=" * 60)

    true_bn = BayesianNetwork("True")
    true_bn.add_node("A", ["0", "1"])
    true_bn.add_node("B", ["0", "1"])
    true_bn.add_node("C", ["0", "1"])

    true_bn.add_edge("A", "B")
    true_bn.add_edge("A", "C")

    true_bn.set_cpt("A", {"0": 0.7, "1": 0.3})
    true_bn.set_cpt("B", {("0", "0"): 0.6, ("0", "1"): 0.4, ("1", "0"): 0.2, ("1", "1"): 0.8})
    true_bn.set_cpt("C", {("0", "0"): 0.8, ("0", "1"): 0.2, ("1", "0"): 0.3, ("1", "1"): 0.7})

    np.random.seed(42)
    data = true_bn.sample(800)

    print("\n步骤1: 从数据学习网络结构 (爬山法)")
    learned_bn = BayesianNetwork("Learned")
    learned_bn.add_node("A", ["0", "1"])
    learned_bn.add_node("B", ["0", "1"])
    learned_bn.add_node("C", ["0", "1"])

    learned_bn.learn_structure_hill_climb(data, max_iter=30, score='bic', verbose=False)

    print(f"  真实边: {true_bn.edges}")
    print(f"  学习边: {learned_bn.edges}")

    print("\n步骤2: 学习CPT参数")
    learned_bn.fit(data, smoothing=1.0)

    print("\n步骤3: 因果推断")
    print("  计算 do(A=1) 对 C 的因果效应:")
    effect = learned_bn.causal_effect("A", "1", "C", "1")
    print(f"  P(C=1 | do(A=1)) = {effect:.4f}")

    print("\n步骤4: 敏感性分析")
    sens = learned_bn.sensitivity_analysis(
        ["C"], {"B": "1"}, perturbation=0.05, method='one_at_a_time'
    )
    print("  各节点对 P(C|B=1) 的敏感性:")
    for node, s in sens['sensitivity'].items():
        print(f"    {node}: {s['C']:.6f}")

    return learned_bn


if __name__ == "__main__":
    np.random.seed(42)

    try:
        bn1, true1 = example_1_structure_learning_k2()
    except Exception as e:
        print(f"示例1出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        bn2, true2 = example_2_structure_learning_hill_climb()
    except Exception as e:
        print(f"示例2出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        bn3 = example_3_causal_inference()
    except Exception as e:
        print(f"示例3出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        bn4 = example_4_sensitivity_analysis()
    except Exception as e:
        print(f"示例4出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        bn5 = example_5_combined()
    except Exception as e:
        print(f"示例5出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)
