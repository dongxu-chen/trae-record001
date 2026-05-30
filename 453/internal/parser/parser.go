package parser

import (
	"context"
	"crypto/sha256"
	"fmt"
	"regexp"
	"strings"
	"unicode"
)

type QueryPlanFeature struct {
	EstimatedRows     float64
	ActualRows        float64
	UsingIndex        bool
	UsingPrimaryKey   bool
	UsingTemporary    bool
	UsingFilesort     bool
	UsingJoinBuffer   bool
	ScanType          string
	JoinType          string
	AccessType        string
	PossibleKeys      []string
	KeyUsed           string
	KeyLen            int
	RefColumns        []string
	Filtered          float64
	Extra             []string
	TotalCost         float64
}

type QueryPattern struct {
	Fingerprint     string
	Parameterized   string
	Tables          []string
	Operation       string
	SelectColumns   []string
	WhereColumns    []string
	JoinTables      []string
	OrderByColumns  []string
	GroupByColumns  []string
	LimitClause     bool
	ComplexityScore float64
	PlanFeatures    *QueryPlanFeature
}

type ParsedQuery struct {
	Original string
	Pattern  *QueryPattern
}

type SQLParser struct {
	paramRegex    *regexp.Regexp
	stringRegex   *regexp.Regexp
	numberRegex   *regexp.Regexp
	inListRegex   *regexp.Regexp
	commentRegex  *regexp.Regexp
}

type QueryExecutor interface {
	ExecuteQuery(ctx context.Context, query string, args ...interface{}) (*QueryResult, error)
}

type QueryResult struct {
	Columns []string
	Rows    []map[string]interface{}
	Count   int
}

func NewSQLParser() *SQLParser {
	return &SQLParser{
		paramRegex:    regexp.MustCompile(`\b\d+\b`),
		stringRegex:   regexp.MustCompile(`'[^']*'`),
		numberRegex:   regexp.MustCompile(`\b\d+(\.\d+)?\b`),
		inListRegex:   regexp.MustCompile(`\bIN\s*\([^)]+\)`),
		commentRegex:  regexp.MustCompile(`--.*$|/\*[\s\S]*?\*/`),
	}
}

func (p *SQLParser) Parse(sql string) (*ParsedQuery, error) {
	cleaned := p.cleanSQL(sql)
	parameterized := p.parameterize(cleaned)
	fingerprint := p.fingerprint(parameterized)
	tables := p.extractTables(cleaned)
	operation := p.extractOperation(cleaned)
	selectCols := p.extractSelectColumns(cleaned)
	whereCols := p.extractWhereColumns(cleaned)
	joinTables := p.extractJoinTables(cleaned)
	orderByCols := p.extractOrderByColumns(cleaned)
	groupByCols := p.extractGroupByColumns(cleaned)
	hasLimit := p.hasLimitClause(cleaned)
	complexity := p.calculateComplexity(cleaned, tables, joinTables, whereCols, groupByCols)

	pattern := &QueryPattern{
		Fingerprint:     fingerprint,
		Parameterized:   parameterized,
		Tables:          tables,
		Operation:       operation,
		SelectColumns:   selectCols,
		WhereColumns:    whereCols,
		JoinTables:      joinTables,
		OrderByColumns:  orderByCols,
		GroupByColumns:  groupByCols,
		LimitClause:     hasLimit,
		ComplexityScore: complexity,
	}

	return &ParsedQuery{
		Original: sql,
		Pattern:  pattern,
	}, nil
}

func (p *SQLParser) ParseWithPlan(ctx context.Context, sql string, executor QueryExecutor, dbType string) (*ParsedQuery, error) {
	parsed, err := p.Parse(sql)
	if err != nil {
		return nil, err
	}

	planFeatures, err := p.ExtractQueryPlan(ctx, sql, executor, dbType)
	if err != nil {
		return parsed, nil
	}

	parsed.Pattern.PlanFeatures = planFeatures
	return parsed, nil
}

func (p *SQLParser) ExtractQueryPlan(ctx context.Context, sql string, executor QueryExecutor, dbType string) (*QueryPlanFeature, error) {
	var explainQuery string
	switch strings.ToLower(dbType) {
	case "mysql":
		explainQuery = "EXPLAIN FORMAT=JSON " + sql
	case "postgres", "pg":
		explainQuery = "EXPLAIN (ANALYZE, COSTS, BUFFERS, FORMAT JSON) " + sql
	default:
		return nil, fmt.Errorf("unsupported db type: %s", dbType)
	}

	result, err := executor.ExecuteQuery(ctx, explainQuery)
	if err != nil || result.Count == 0 {
		return nil, fmt.Errorf("failed to execute explain: %w", err)
	}

	planData, ok := result.Rows[0]
	if !ok {
		return nil, fmt.Errorf("empty explain result")
	}

	return p.parseQueryPlan(planData, dbType), nil
}

func (p *SQLParser) parseQueryPlan(planRow map[string]interface{}, dbType string) *QueryPlanFeature {
	feature := &QueryPlanFeature{
		Extra: make([]string, 0),
	}

	switch strings.ToLower(dbType) {
	case "mysql":
		p.parseMySQLPlan(planRow, feature)
	case "postgres", "pg":
		p.parsePGPlan(planRow, feature)
	}

	return feature
}

func (p *SQLParser) parseMySQLPlan(planRow map[string]interface{}, feature *QueryPlanFeature) {
	for k, v := range planRow {
		key := strings.ToLower(k)
		switch key {
		case "type":
			if s, ok := v.(string); ok {
				feature.AccessType = s
				feature.ScanType = s
			}
		case "key":
			if s, ok := v.(string); ok {
				feature.KeyUsed = s
				if s == "PRIMARY" {
					feature.UsingPrimaryKey = true
				} else if s != "" {
					feature.UsingIndex = true
				}
			}
		case "possible_keys":
			if s, ok := v.(string); ok && s != "" {
				feature.PossibleKeys = strings.Split(s, ",")
			}
		case "rows":
			if num, ok := v.(int64); ok {
				feature.EstimatedRows = float64(num)
			}
		case "filtered":
			if num, ok := v.(float64); ok {
				feature.Filtered = num
			}
		case "key_len":
			if num, ok := v.(int64); ok {
				feature.KeyLen = int(num)
			}
		case "ref":
			if s, ok := v.(string); ok && s != "" {
				feature.RefColumns = strings.Split(s, ",")
			}
		case "extra":
			if s, ok := v.(string); ok {
				feature.Extra = strings.Split(s, ";")
				lower := strings.ToLower(s)
				if strings.Contains(lower, "using index") {
					feature.UsingIndex = true
				}
				if strings.Contains(lower, "using temporary") {
					feature.UsingTemporary = true
				}
				if strings.Contains(lower, "using filesort") {
					feature.UsingFilesort = true
				}
				if strings.Contains(lower, "using join buffer") {
					feature.UsingJoinBuffer = true
				}
			}
		}
	}
}

func (p *SQLParser) parsePGPlan(planRow map[string]interface{}, feature *QueryPlanFeature) {
	for k, v := range planRow {
		key := strings.ToLower(k)
		switch key {
		case "plan":
			if plan, ok := v.(map[string]interface{}); ok {
				p.extractPGNodeFeatures(plan, feature)
			}
		}
	}
}

func (p *SQLParser) extractPGNodeFeatures(node map[string]interface{}, feature *QueryPlanFeature) {
	if nodeType, ok := node["Node Type"].(string); ok {
		feature.ScanType = nodeType
		lower := strings.ToLower(nodeType)
		if strings.Contains(lower, "index") {
			feature.UsingIndex = true
		}
		if strings.Contains(lower, "sort") {
			feature.UsingFilesort = true
		}
	}

	if idxName, ok := node["Index Name"].(string); ok {
		feature.KeyUsed = idxName
	}

	if rows, ok := node["Plan Rows"].(float64); ok {
		feature.EstimatedRows = rows
	}

	if actualRows, ok := node["Actual Rows"].(float64); ok {
		feature.ActualRows = actualRows
	}

	if cost, ok := node["Total Cost"].(float64); ok {
		feature.TotalCost = cost
	}

	if plans, ok := node["Plans"].([]interface{}); ok {
		for _, plan := range plans {
			if child, ok := plan.(map[string]interface{}); ok {
				p.extractPGNodeFeatures(child, feature)
			}
		}
	}
}

func (p *SQLParser) cleanSQL(sql string) string {
	sql = p.commentRegex.ReplaceAllString(sql, "")
	sql = strings.TrimSpace(sql)
	return sql
}

func (p *SQLParser) parameterize(sql string) string {
	result := p.stringRegex.ReplaceAllString(sql, "?")
	result = p.inListRegex.ReplaceAllStringFunc(result, func(match string) string {
		idx := strings.Index(match, "(")
		if idx == -1 {
			return match
		}
		return match[:idx+1] + "?)"
	})
	result = p.numberRegex.ReplaceAllString(result, "?")
	tokens := strings.Fields(result)
	normalized := make([]string, 0, len(tokens))
	for _, tok := range tokens {
		lower := strings.ToLower(tok)
		if isKeyword(lower) {
			normalized = append(normalized, lower)
		} else {
			normalized = append(normalized, tok)
		}
	}
	return strings.Join(normalized, " ")
}

func (p *SQLParser) fingerprint(parameterized string) string {
	h := sha256.New()
	h.Write([]byte(parameterized))
	return fmt.Sprintf("%x", h.Sum(nil))[:16]
}

func (p *SQLParser) extractTables(sql string) []string {
	tables := make(map[string]bool)
	upper := strings.ToUpper(sql)

	patterns := []struct {
		prefix string
		regex  *regexp.Regexp
	}{
		{"FROM", regexp.MustCompile(`(?i)\bFROM\s+(\w+)`)},
		{"JOIN", regexp.MustCompile(`(?i)\bJOIN\s+(\w+)`)},
		{"INTO", regexp.MustCompile(`(?i)\bINTO\s+(\w+)`)},
		{"UPDATE", regexp.MustCompile(`(?i)\bUPDATE\s+(\w+)`)},
	}

	for _, pat := range patterns {
		matches := pat.regex.FindAllStringSubmatch(upper, -1)
		for _, m := range matches {
			if len(m) > 1 && !isKeyword(m[1]) {
				tables[strings.ToLower(m[1])] = true
			}
		}
	}

	_ = upper
	result := make([]string, 0, len(tables))
	for t := range tables {
		result = append(result, t)
	}
	return result
}

func (p *SQLParser) extractOperation(sql string) string {
	trimmed := strings.TrimSpace(sql)
	if len(trimmed) == 0 {
		return "UNKNOWN"
	}
	firstWord := strings.ToUpper(strings.Fields(trimmed)[0])
	switch firstWord {
	case "SELECT":
		return "SELECT"
	case "INSERT":
		return "INSERT"
	case "UPDATE":
		return "UPDATE"
	case "DELETE":
		return "DELETE"
	default:
		return "UNKNOWN"
	}
}

func (p *SQLParser) extractSelectColumns(sql string) []string {
	re := regexp.MustCompile(`(?i)\bSELECT\s+(.*?)\bFROM\b`)
	matches := re.FindStringSubmatch(sql)
	if len(matches) < 2 {
		return nil
	}
	colPart := matches[1]
	if strings.TrimSpace(colPart) == "*" {
		return []string{"*"}
	}
	cols := strings.Split(colPart, ",")
	result := make([]string, 0, len(cols))
	for _, c := range cols {
		trimmed := strings.TrimSpace(c)
		parts := strings.Fields(trimmed)
		if len(parts) > 0 {
			result = append(result, parts[len(parts)-1])
		}
	}
	return result
}

func (p *SQLParser) extractWhereColumns(sql string) []string {
	re := regexp.MustCompile(`(?i)\bWHERE\s+(.*?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|\bHAVING\b|$)`)
	matches := re.FindStringSubmatch(sql)
	if len(matches) < 2 {
		return nil
	}
	wherePart := matches[1]
	colRe := regexp.MustCompile(`(\w+)\s*(?:=|!=|<|>|<=|>=|LIKE|IN|BETWEEN)`)
	colMatches := colRe.FindAllStringSubmatch(wherePart, -1)
	result := make([]string, 0)
	for _, m := range colMatches {
		if len(m) > 1 && !isKeyword(m[1]) {
			result = append(result, strings.ToLower(m[1]))
		}
	}
	return result
}

func (p *SQLParser) extractJoinTables(sql string) []string {
	re := regexp.MustCompile(`(?i)\b(?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\s+(\w+)`)
	matches := re.FindAllStringSubmatch(sql, -1)
	result := make([]string, 0)
	for _, m := range matches {
		if len(m) > 1 && !isKeyword(m[1]) {
			result = append(result, strings.ToLower(m[1]))
		}
	}
	return result
}

func (p *SQLParser) extractOrderByColumns(sql string) []string {
	re := regexp.MustCompile(`(?i)\bORDER\s+BY\s+(.*?)(?:\bLIMIT\b|$)`)
	matches := re.FindStringSubmatch(sql)
	if len(matches) < 2 {
		return nil
	}
	cols := strings.Split(matches[1], ",")
	result := make([]string, 0, len(cols))
	for _, c := range cols {
		trimmed := strings.TrimSpace(c)
		parts := strings.Fields(trimmed)
		if len(parts) > 0 {
			result = append(result, strings.ToLower(parts[0]))
		}
	}
	return result
}

func (p *SQLParser) extractGroupByColumns(sql string) []string {
	re := regexp.MustCompile(`(?i)\bGROUP\s+BY\s+(.*?)(?:\bHAVING\b|\bORDER\b|\bLIMIT\b|$)`)
	matches := re.FindStringSubmatch(sql)
	if len(matches) < 2 {
		return nil
	}
	cols := strings.Split(matches[1], ",")
	result := make([]string, 0, len(cols))
	for _, c := range cols {
		trimmed := strings.TrimSpace(c)
		if trimmed != "" {
			result = append(result, strings.ToLower(trimmed))
		}
	}
	return result
}

func (p *SQLParser) hasLimitClause(sql string) bool {
	return regexp.MustCompile(`(?i)\bLIMIT\b`).MatchString(sql)
}

func (p *SQLParser) calculateComplexity(sql string, tables, joinTables, whereCols, groupByCols []string) float64 {
	score := 1.0
	score += float64(len(tables)) * 0.5
	score += float64(len(joinTables)) * 1.5
	score += float64(len(whereCols)) * 0.3
	score += float64(len(groupByCols)) * 0.8
	upper := strings.ToUpper(sql)
	if strings.Contains(upper, "SUBQUERY") || strings.Count(upper, "SELECT") > 1 {
		score += 2.0
	}
	if strings.Contains(upper, "UNION") {
		score += 1.5
	}
	if strings.Contains(upper, " DISTINCT ") {
		score += 0.5
	}
	return score
}

func (qp *QueryPattern) FeatureVector() []float64 {
	vec := make([]float64, 32)
	ops := map[string]int{"SELECT": 0, "INSERT": 1, "UPDATE": 2, "DELETE": 3}
	if idx, ok := ops[qp.Operation]; ok {
		vec[idx] = 1.0
	}
	vec[4] = float64(len(qp.Tables))
	vec[5] = float64(len(qp.SelectColumns))
	vec[6] = float64(len(qp.WhereColumns))
	vec[7] = float64(len(qp.JoinTables))
	vec[8] = float64(len(qp.OrderByColumns))
	vec[9] = float64(len(qp.GroupByColumns))
	if qp.LimitClause {
		vec[10] = 1.0
	}
	vec[11] = qp.ComplexityScore
	if len(qp.Tables) > 0 {
		vec[12] = 1.0
	}
	if len(qp.WhereColumns) > 0 {
		vec[13] = 1.0
	}
	if len(qp.GroupByColumns) > 0 {
		vec[14] = 1.0
	}
	if len(qp.JoinTables) > 0 {
		vec[15] = 1.0
	}

	if qp.PlanFeatures != nil {
		if qp.PlanFeatures.UsingIndex {
			vec[16] = 1.0
		}
		if qp.PlanFeatures.UsingPrimaryKey {
			vec[17] = 1.0
		}
		if qp.PlanFeatures.UsingTemporary {
			vec[18] = 1.0
		}
		if qp.PlanFeatures.UsingFilesort {
			vec[19] = 1.0
		}
		if qp.PlanFeatures.UsingJoinBuffer {
			vec[20] = 1.0
		}
		vec[21] = qp.PlanFeatures.EstimatedRows / 1000.0
		vec[22] = qp.PlanFeatures.ActualRows / 1000.0
		vec[23] = qp.PlanFeatures.Filtered / 100.0
		vec[24] = float64(qp.PlanFeatures.KeyLen) / 100.0
		vec[25] = qp.PlanFeatures.TotalCost / 1000.0
		vec[26] = float64(len(qp.PlanFeatures.PossibleKeys))
		vec[27] = float64(len(qp.PlanFeatures.RefColumns))

		accessTypeScore := map[string]float64{
			"system": 0.0, "const": 0.1, "eq_ref": 0.2, "ref": 0.3,
			"range": 0.4, "index": 0.6, "all": 1.0,
		}
		if score, ok := accessTypeScore[strings.ToLower(qp.PlanFeatures.AccessType)]; ok {
			vec[28] = score
		} else {
			vec[28] = 0.5
		}

		scanTypeScore := map[string]float64{
			"index scan":     0.3, "index only scan": 0.1,
			"seq scan":       0.9, "bitmap scan":     0.5,
			"nested loop":    0.4, "hash join":       0.6,
			"merge join":     0.5,
		}
		if score, ok := scanTypeScore[strings.ToLower(qp.PlanFeatures.ScanType)]; ok {
			vec[29] = score
		} else {
			vec[29] = 0.5
		}

		if qp.PlanFeatures.EstimatedRows > 0 && qp.PlanFeatures.ActualRows > 0 {
			ratio := qp.PlanFeatures.EstimatedRows / qp.PlanFeatures.ActualRows
			if ratio > 10.0 {
				ratio = 10.0
			}
			vec[30] = ratio / 10.0
		}

		vec[31] = float64(len(qp.PlanFeatures.Extra))
	}

	return vec
}

func isKeyword(s string) bool {
	keywords := map[string]bool{
		"SELECT": true, "FROM": true, "WHERE": true, "JOIN": true,
		"INNER": true, "LEFT": true, "RIGHT": true, "OUTER": true,
		"ON": true, "AND": true, "OR": true, "NOT": true,
		"INSERT": true, "INTO": true, "VALUES": true, "UPDATE": true,
		"SET": true, "DELETE": true, "CREATE": true, "DROP": true,
		"ALTER": true, "INDEX": true, "TABLE": true, "ORDER": true,
		"BY": true, "GROUP": true, "HAVING": true, "LIMIT": true,
		"OFFSET": true, "AS": true, "IN": true, "IS": true,
		"NULL": true, "LIKE": true, "BETWEEN": true, "EXISTS": true,
		"DISTINCT": true, "UNION": true, "ALL": true, "ASC": true,
		"DESC": true, "COUNT": true, "SUM": true, "AVG": true,
		"MIN": true, "MAX": true, "CASE": true, "WHEN": true,
		"THEN": true, "ELSE": true, "END": true, "WITH": true,
		"FULL": true, "CROSS": true, "NATURAL": true, "USING": true,
	}
	return keywords[strings.ToUpper(s)]
}

func tokenizeSQL(sql string) []string {
	var tokens []string
	var current strings.Builder
	inString := false

	for _, r := range sql {
		if r == '\'' {
			inString = !inString
			current.WriteRune(r)
			continue
		}
		if inString {
			current.WriteRune(r)
			continue
		}
		if unicode.IsSpace(r) || r == ',' || r == '(' || r == ')' || r == ';' {
			if current.Len() > 0 {
				tokens = append(tokens, current.String())
				current.Reset()
			}
			continue
		}
		current.WriteRune(r)
	}
	if current.Len() > 0 {
		tokens = append(tokens, current.String())
	}
	return tokens
}
