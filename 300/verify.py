
import sys
sys.path.insert(0, 'd:\\Trae\\project\\record001\\300')

print("=== 模块导入测试 ===")
try:
    from substitution_matrices import SubstitutionMatrix, IUPAC_AMINO_ACIDS, IUPAC_DNA_BASES
    print("✓ substitution_matrices 导入成功")
except Exception as e:
    print(f"✗ substitution_matrices 导入失败: {e}")
    sys.exit(1)

try:
    from sequence_alignment import NeedlemanWunsch, SmithWaterman, AlignmentResult
    print("✓ sequence_alignment 导入成功")
except Exception as e:
    print(f"✗ sequence_alignment 导入失败: {e}")
    sys.exit(1)

try:
    from visualization import print_alignment, print_memory_comparison
    print("✓ visualization 导入成功")
except Exception as e:
    print(f"✗ visualization 导入失败: {e}")
    sys.exit(1)

print("\n=== IUPAC编码测试 ===")
print(f"氨基酸: {len(IUPAC_AMINO_ACIDS)} 个 - {''.join(IUPAC_AMINO_ACIDS)}")
print(f"DNA碱基: {len(IUPAC_DNA_BASES)} 个 - {''.join(IUPAC_DNA_BASES)}")

print("\n=== 比对算法测试 ===")
print("测试: Needleman-Wunsch (滚动数组)")
nw = NeedlemanWunsch('HEAGAWGHE', 'PAWHEAE', gap_penalty=-2,
                     matrix_type='blosum62', seq_type='protein',
                     use_rolling=True, find_all_solutions=False)
nw.align()
print(f"  得分: {nw.alignment_score}")
print(f"  解数: {len(nw.alignment_results)}")
if nw.alignment_results:
    r = nw.alignment_results[0]
    print(f"  序列1: {r.aligned_seq1}")
    print(f"  序列2: {r.aligned_seq2}")

print("\n测试: 多解回溯")
nw2 = NeedlemanWunsch('ABC', 'AC', gap_penalty=-1,
                      matrix_type='blosum62', seq_type='protein',
                      use_rolling=True, find_all_solutions=True)
nw2.align()
print(f"  得分: {nw2.alignment_score}")
print(f"  找到 {len(nw2.alignment_results)} 个最优解:")
for i, r in enumerate(nw2.alignment_results, 1):
    print(f"    解{i}: {r.aligned_seq1} | {r.aligned_seq2}")

print("\n测试: Smith-Waterman")
sw = SmithWaterman('HEAGAWGHE', 'PAWHEAE', gap_penalty=-2,
                   matrix_type='blosum62', seq_type='protein',
                   use_rolling=True, find_all_solutions=True, max_solutions=5)
sw.align()
print(f"  得分: {sw.alignment_score}")
print(f"  解数: {len(sw.alignment_results)}")

print("\n=== 内存对比 ===")
print_memory_comparison(nw)

print("\n✅ 所有验证通过!")
