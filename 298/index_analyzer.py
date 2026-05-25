import logging
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field
from itertools import combinations

from database import TableSchema, IndexInfo, ColumnInfo
from config import IndexConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DuplicateIndex:
    table_name: str
    redundant_index: IndexInfo
    dominant_index: IndexInfo
    similarity: float
    reason: str


@dataclass
class MergeSuggestion:
    table_name: str
    indexes_to_merge: List[IndexInfo]
    suggested_index: List[str]
    benefit_score: float
    reason: str


@dataclass
class IndexAnalysisResult:
    duplicate_indexes: List[DuplicateIndex] = field(default_factory=list)
    merge_suggestions: List[MergeSuggestion] = field(default_factory=list)
    unused_indexes: List[Tuple[str, IndexInfo]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class IndexAnalyzer:
    def __init__(self, config: IndexConfig):
        self.config = config

    def analyze_indexes(
        self,
        schemas: Dict[str, TableSchema],
        used_columns: Optional[Dict[str, Set[str]]] = None
    ) -> IndexAnalysisResult:
        result = IndexAnalysisResult()
        
        for table_name, schema in schemas.items():
            table_duplicates = self._find_duplicate_indexes(table_name, schema.indexes)
            result.duplicate_indexes.extend(table_duplicates)
            
            table_merges = self._find_merge_candidates(table_name, schema.indexes)
            result.merge_suggestions.extend(table_merges)
            
            if used_columns and table_name in used_columns:
                unused = self._find_unused_indexes(
                    table_name, schema.indexes, used_columns[table_name]
                )
                result.unused_indexes.extend(unused)
        
        self._generate_recommendations(result)
        return result

    def _find_duplicate_indexes(
        self,
        table_name: str,
        indexes: List[IndexInfo]
    ) -> List[DuplicateIndex]:
        duplicates = []
        n = len(indexes)
        
        for i in range(n):
            for j in range(i + 1, n):
                idx1 = indexes[i]
                idx2 = indexes[j]
                
                if idx1.is_primary or idx2.is_primary:
                    continue
                
                similarity, reason = self._calculate_index_similarity(idx1, idx2)
                
                if similarity >= self.config.duplicate_index_similarity_threshold:
                    dominant, redundant = self._select_dominant_index(idx1, idx2)
                    duplicates.append(DuplicateIndex(
                        table_name=table_name,
                        redundant_index=redundant,
                        dominant_index=dominant,
                        similarity=similarity,
                        reason=reason
                    ))
        
        return duplicates

    def _calculate_index_similarity(
        self,
        idx1: IndexInfo,
        idx2: IndexInfo
    ) -> Tuple[float, str]:
        cols1 = idx1.columns
        cols2 = idx2.columns
        
        if cols1 == cols2:
            return 1.0, "完全相同的列组合"
        
        set1 = set(cols1)
        set2 = set(cols2)
        
        if set1 == set2 and self.config.use_column_order_compatibility:
            optimal_order = self._get_optimal_column_order(cols1, cols2)
            return 0.95, f"列集合完全相同，顺序不同（建议顺序: {optimal_order}）"
        
        min_len = min(len(cols1), len(cols2))
        prefix_match = 0
        for i in range(min_len):
            if cols1[i] == cols2[i]:
                prefix_match += 1
            else:
                break
        
        if prefix_match == min_len:
            if len(cols1) > len(cols2):
                return 0.9, f"索引1包含索引2的前缀（{prefix_match}列匹配）"
            else:
                return 0.9, f"索引2包含索引1的前缀（{prefix_match}列匹配）"
        
        intersection = set1 & set2
        union = set1 | set2
        
        if union:
            jaccard = len(intersection) / len(union)
            if jaccard >= 0.7:
                return jaccard, f"列集合相似度为 {jaccard:.2f}"
        
        return 0.0, "不相似"

    def _get_optimal_column_order(self, cols1: List[str], cols2: List[str]) -> List[str]:
        all_cols = list(set(cols1))
        order_score = {col: 0 for col in all_cols}
        
        for cols in [cols1, cols2]:
            for i, col in enumerate(cols):
                order_score[col] += len(cols) - i
        
        return sorted(all_cols, key=lambda c: order_score[c], reverse=True)

    def _select_dominant_index(
        self,
        idx1: IndexInfo,
        idx2: IndexInfo
    ) -> Tuple[IndexInfo, IndexInfo]:
        if idx1.is_unique and not idx2.is_unique:
            return idx1, idx2
        if idx2.is_unique and not idx1.is_unique:
            return idx2, idx1
        
        if len(idx1.columns) > len(idx2.columns):
            return idx1, idx2
        if len(idx2.columns) > len(idx1.columns):
            return idx2, idx1
        
        if idx1.cardinality > idx2.cardinality:
            return idx1, idx2
        return idx2, idx1

    def _find_merge_candidates(
        self,
        table_name: str,
        indexes: List[IndexInfo]
    ) -> List[MergeSuggestion]:
        suggestions = []
        
        if len(indexes) < 2:
            return suggestions
        
        non_primary = [idx for idx in indexes if not idx.is_primary]
        
        for r in range(2, min(5, len(non_primary) + 1)):
            for combo in combinations(non_primary, r):
                merged, benefit, reason = self._try_merge_indexes(combo)
                if merged:
                    suggestions.append(MergeSuggestion(
                        table_name=table_name,
                        indexes_to_merge=list(combo),
                        suggested_index=merged,
                        benefit_score=benefit,
                        reason=reason
                    ))
        
        return sorted(suggestions, key=lambda s: s.benefit_score, reverse=True)[:5]

    def _try_merge_indexes(
        self,
        indexes: List[IndexInfo]
    ) -> Tuple[Optional[List[str]], float, str]:
        all_columns = []
        column_order_score = {}
        column_freq = {}
        
        for idx in indexes:
            for i, col in enumerate(idx.columns):
                if col not in column_order_score:
                    column_order_score[col] = 0
                    column_freq[col] = 0
                column_order_score[col] += len(idx.columns) - i
                column_freq[col] += 1
        
        if self.config.use_column_order_compatibility:
            all_col_sets = [set(idx.columns) for idx in indexes]
            common_cols = set.intersection(*all_col_sets) if all_col_sets else set()
            
            if common_cols and len(indexes) >= 2:
                sorted_cols = sorted(
                    column_order_score.keys(),
                    key=lambda c: (column_freq[c], column_order_score[c]),
                    reverse=True
                )
                
                if len(sorted_cols) > self.config.max_columns_per_index:
                    sorted_cols = sorted_cols[:self.config.max_columns_per_index]
                
                original_count = len(indexes)
                merged_count = 1
                space_saving = (original_count - merged_count) / original_count
                coverage_score = len(sorted_cols) / max(len(column_order_score), 1)
                
                benefit = space_saving * 0.5 + coverage_score * 0.3 + 0.2
                reason = f"列集合高度重叠（{len(common_cols)}列相同），建议按频率+位置排序合并"
                return sorted_cols, benefit, reason
        
        prefix_columns = set()
        for idx in indexes:
            if idx.columns:
                prefix_columns.add(idx.columns[0])
        
        if len(prefix_columns) > 1:
            return None, 0.0, "索引前缀不同，无法有效合并"
        
        sorted_cols = sorted(
            column_order_score.keys(),
            key=lambda c: column_order_score[c],
            reverse=True
        )
        
        if len(sorted_cols) > self.config.max_columns_per_index:
            sorted_cols = sorted_cols[:self.config.max_columns_per_index]
        
        original_count = len(indexes)
        merged_count = 1
        space_saving = (original_count - merged_count) / original_count
        
        coverage_score = len(sorted_cols) / max(len(column_order_score), 1)
        
        benefit = space_saving * 0.6 + coverage_score * 0.4
        
        return sorted_cols, benefit, f"合并 {original_count} 个索引为 1 个，覆盖 {len(sorted_cols)} 列"

    def _find_unused_indexes(
        self,
        table_name: str,
        indexes: List[IndexInfo],
        used_columns: Set[str]
    ) -> List[Tuple[str, IndexInfo]]:
        unused = []
        
        for idx in indexes:
            if idx.is_primary:
                continue
            
            idx_columns = set(idx.columns)
            overlap = idx_columns & used_columns
            
            if not overlap or len(overlap) / len(idx_columns) < 0.3:
                unused.append((table_name, idx))
        
        return unused

    def _generate_recommendations(self, result: IndexAnalysisResult):
        for dup in result.duplicate_indexes:
            result.recommendations.append(
                f"[冗余索引] 表 {dup.table_name}: "
                f"删除 {dup.redundant_index.name} "
                f"(被 {dup.dominant_index.name} 覆盖, "
                f"相似度: {dup.similarity:.2f})"
            )
        
        for merge in result.merge_suggestions:
            idx_names = ', '.join(idx.name for idx in merge.indexes_to_merge)
            result.recommendations.append(
                f"[合并建议] 表 {merge.table_name}: "
                f"将 [{idx_names}] 合并为 ({', '.join(merge.suggested_index)}) "
                f"(收益: {merge.benefit_score:.2f})"
            )
        
        for table_name, idx in result.unused_indexes:
            result.recommendations.append(
                f"[未使用索引] 表 {table_name}: "
                f"索引 {idx.name} ({', '.join(idx.columns)}) 很少被使用"
            )

    def generate_candidate_indexes(
        self,
        schema: TableSchema,
        candidate_columns: List[str],
        existing_indexes: List[IndexInfo] = None
    ) -> List[List[str]]:
        candidates = []
        existing_indexes = existing_indexes or []
        
        existing_sets = {tuple(idx.columns) for idx in existing_indexes}
        
        for r in range(1, min(self.config.max_columns_per_index, len(candidate_columns)) + 1):
            for combo in combinations(candidate_columns, r):
                if self._is_valid_index_order(combo, schema):
                    if tuple(combo) not in existing_sets:
                        candidates.append(list(combo))
        
        return candidates

    def _is_valid_index_order(self, columns: Tuple[str, ...], schema: TableSchema) -> bool:
        if len(columns) <= 1:
            return True
        
        column_map = {col.name: col for col in schema.columns}
        
        low_card_cols = []
        for col_name in columns:
            col_info = column_map.get(col_name)
            if col_info and col_info.cardinality > 0:
                selectivity = col_info.cardinality / max(schema.row_count, 1)
                if selectivity < 0.1:
                    low_card_cols.append(col_name)
        
        if low_card_cols and columns[0] in low_card_cols:
            return False
        
        return True

    def estimate_index_size(self, schema: TableSchema, columns: List[str]) -> int:
        row_count = schema.row_count or 1000
        total_size = 0
        
        column_map = {col.name: col for col in schema.columns}
        
        for col_name in columns:
            col_info = column_map.get(col_name)
            if col_info:
                type_size = self._estimate_type_size(col_info.data_type)
                total_size += type_size
            else:
                total_size += 8
        
        overhead_per_row = 8
        total_per_row = total_size + overhead_per_row
        
        fill_factor = 0.7
        
        return int(row_count * total_per_row / fill_factor)

    def _estimate_type_size(self, data_type: str) -> int:
        data_type = data_type.lower()
        
        if 'int' in data_type:
            if 'big' in data_type:
                return 8
            elif 'tiny' in data_type:
                return 1
            elif 'small' in data_type:
                return 2
            else:
                return 4
        elif 'float' in data_type:
            return 4
        elif 'double' in data_type or 'real' in data_type:
            return 8
        elif 'decimal' in data_type or 'numeric' in data_type:
            return 16
        elif 'datetime' in data_type or 'timestamp' in data_type:
            return 8
        elif 'date' in data_type:
            return 4
        elif 'time' in data_type:
            return 4
        elif 'char' in data_type:
            match = __import__('re').search(r'\((\d+)\)', data_type)
            if match:
                return int(match.group(1))
            return 10
        elif 'varchar' in data_type or 'text' in data_type:
            match = __import__('re').search(r'\((\d+)\)', data_type)
            if match:
                return min(int(match.group(1)), 100)
            return 50
        elif 'bool' in data_type:
            return 1
        else:
            return 8
