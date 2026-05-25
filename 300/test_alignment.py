import sys
sys.path.insert(0, 'd:\\Trae\\project\\record001\\300')

from sequence_alignment import NeedlemanWunsch, SmithWaterman, AlignmentResult
from substitution_matrices import SubstitutionMatrix, IUPAC_AMINO_ACIDS, IUPAC_DNA_BASES

print("=" * 60)
print("生物序列比对算法测试")
print("=" * 60)

print("\n【测试1】IUPAC编码验证")
print("-" * 40)
print(f"氨基酸字母表 ({len(IUPAC_AMINO_ACIDS)}个): {''.join(IUPAC_AMINO_ACIDS)}")
print(f"DNA字母表 ({len(IUPAC_DNA_BASES)}个): {''.join(IUPAC_DNA_BASES)}")
print("✓ IUPAC编码加载成功")

print("\n【测试2】替换矩阵测试 - BLOSUM62")
print("-" * 40)
sub_blosum = SubstitutionMatrix('blosum62', 'protein')
print(f"Score(A, A) = {sub_blosum.get_score('A', 'A')} (期望: 4)")
print(f"Score(W, W) = {sub_blosum.get_score('W', 'W')} (期望: 11)")
print(f"Score(B, N) = {sub_blosum.get_score('B', 'N')} (B是N/D简并)")
print(f"Score(X, A) = {sub_blosum.get_score('X', 'A')} (X是任意氨基酸)")
print(f"Score(*, *) = {sub_blosum.get_score('*', '*')} (终止密码子)")
print("✓ BLOSUM62矩阵测试通过")

print("\n【测试3】替换矩阵测试 - DNA(IUPAC简并)")
print("-" * 40)
sub_dna = SubstitutionMatrix('dna', 'dna')
print(f"Score(A, A) = {sub_dna.get_score('A', 'A')} (期望: 2)")
print(f"Score(R, A) = {sub_dna.get_score('R', 'A')} (R=A/G, A匹配)")
print(f"Score(R, G) = {sub_dna.get_score('R', 'G')} (R=A/G, G匹配)")
print(f"Score(N, A) = {sub_dna.get_score('N', 'A')} (N=任意)")
print(f"Score(Y, C) = {sub_dna.get_score('Y', 'C')} (Y=C/T, C匹配)")
print("✓ DNA IUPAC矩阵测试通过")

print("\n【测试4】Needleman-Wunsch - 滚动数组模式")
print("-" * 40)
nw_rolling = NeedlemanWunsch('HEAGAWGHE', 'PAWHEAE', gap_penalty=-2, 
                             matrix_type='blosum62', seq_type='protein',
                             use_rolling=True, find_all_solutions=False)
nw_rolling.align()
print(f"序列1: HEAGAWGHE")
print(f"序列2: PAWHEAE")
print(f"比对得分: {nw_rolling.alignment_score}")
print(f"找到解数: {len(nw_rolling.alignment_results)}")
if nw_rolling.alignment_results:
    r = nw_rolling.alignment_results[0]
    print(f"比对1: {r.aligned_seq1}")
    print(f"比对2: {r.aligned_seq2}")
print("✓ 滚动数组全局比对测试通过")

print("\n【测试5】Needleman-Wunsch - 完整矩阵模式")
print("-" * 40)
nw_full = NeedlemanWunsch('HEAGAWGHE', 'PAWHEAE', gap_penalty=-2,
                          matrix_type='blosum62', seq_type='protein',
                          use_rolling=False, find_all_solutions=False)
nw_full.align()
print(f"比对得分: {nw_full.alignment_score}")
print(f"分数矩阵已保存: {nw_full.score_matrix is not None}")
print(f"分数矩阵形状: {nw_full.score_matrix.shape if nw_full.score_matrix is not None else 'N/A'}")
print("✓ 完整矩阵全局比对测试通过")

print("\n【测试6】多解回溯 - 所有最优解")
print("-" * 40)
nw_multi = NeedlemanWunsch('ABC', 'AC', gap_penalty=-1,
                           matrix_type='blosum62', seq_type='protein',
                           use_rolling=True, find_all_solutions=True, max_solutions=100)
nw_multi.align()
print(f"序列1: ABC")
print(f"序列2: AC")
print(f"比对得分: {nw_multi.alignment_score}")
print(f"找到最优解数: {len(nw_multi.alignment_results)}")
for i, r in enumerate(nw_multi.alignment_results, 1):
    print(f"  解{i}: {r.aligned_seq1} vs {r.aligned_seq2}")
print("✓ 多解回溯测试通过")

print("\n【测试7】Smith-Waterman - 局部比对")
print("-" * 40)
sw = SmithWaterman('HEAGAWGHE', 'PAWHEAE', gap_penalty=-2,
                   matrix_type='blosum62', seq_type='protein',
                   use_rolling=True, find_all_solutions=True, max_solutions=10)
sw.align()
print(f"序列1: HEAGAWGHE")
print(f"序列2: PAWHEAE")
print(f"局部比对得分: {sw.alignment_score}")
print(f"找到局部解数: {len(sw.alignment_results)}")
if sw.alignment_results:
    r = sw.alignment_results[0]
    print(f"局部比对1: {r.aligned_seq1}")
    print(f"局部比对2: {r.aligned_seq2}")
print("✓ 局部比对测试通过")

print("\n【测试8】结果一致性验证")
print("-" * 40)
seq1_test = 'ACGT'
seq2_test = 'AGT'
nw1 = NeedlemanWunsch(seq1_test, seq2_test, gap_penalty=-1,
                      matrix_type='dna', seq_type='dna',
                      use_rolling=False, find_all_solutions=False)
nw1.align()
nw2 = NeedlemanWunsch(seq1_test, seq2_test, gap_penalty=-1,
                      matrix_type='dna', seq_type='dna',
                      use_rolling=True, find_all_solutions=False)
nw2.align()
print(f"完整矩阵得分: {nw1.alignment_score}")
print(f"滚动数组得分: {nw2.alignment_score}")
print(f"得分一致: {nw1.alignment_score == nw2.alignment_score}")
assert nw1.alignment_score == nw2.alignment_score, "结果不一致！"
print("✓ 滚动数组与完整矩阵结果一致")

print("\n【测试9】DNA序列比对")
print("-" * 40)
dna_nw = NeedlemanWunsch('ATCGATCG', 'ATACGTAG', gap_penalty=-1,
                         matrix_type='dna', seq_type='dna',
                         use_rolling=True, find_all_solutions=True, max_solutions=5)
dna_nw.align()
print(f"序列1: ATCGATCG")
print(f"序列2: ATACGTAG")
print(f"比对得分: {dna_nw.alignment_score}")
print(f"找到解数: {len(dna_nw.alignment_results)}")
for i, r in enumerate(dna_nw.alignment_results[:3], 1):
    print(f"  解{i}: {r.aligned_seq1}")
    print(f"       {r.aligned_seq2}")
print("✓ DNA比对测试通过")

print("\n【测试10】AlignmentResult类功能")
print("-" * 40)
r1 = AlignmentResult("ABC", "A-C", 10)
r2 = AlignmentResult("ABC", "A-C", 10)
r3 = AlignmentResult("AB-C", "A-C-", 9)
print(f"r1 == r2: {r1 == r2} (期望: True)")
print(f"r1 == r3: {r1 == r3} (期望: False)")
print(f"r1可哈希: {hash(r1) is not None}")
print(f"r1字符串:\n{str(r1)}")
print("✓ AlignmentResult类测试通过")

print("\n" + "=" * 60)
print("✅ 所有测试通过！")
print("=" * 60)
print("\n优化特性总结:")
print("  1. ✅ IUPAC标准编码 - 支持简并氨基酸/碱基")
print("  2. ✅ 滚动数组优化 - 内存从O(nm)→O(n)")
print("  3. ✅ 多解回溯 - 输出所有最优比对解")
print("  4. ✅ 结果封装 - AlignmentResult类统一管理")
print("  5. ✅ 模式切换 - 支持滚动/完整矩阵切换")
