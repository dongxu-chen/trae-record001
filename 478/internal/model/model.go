package model

type Position struct {
	File   string
	Line   int
	Column int
}

func (p Position) String() string {
	return p.File
}

type TokenType int

const (
	TokenEOF TokenType = iota
	TokenIdentifier
	TokenString
	TokenNumber
	TokenLBrace
	TokenRBrace
	TokenSemicolon
	TokenComment
	TokenVariable
)

type Token struct {
	Type  TokenType
	Value string
	Pos   Position
}

type NodeType int

const (
	NodeDirective NodeType = iota
	NodeBlock
	NodeComment
	NodeInclude
)

type Node struct {
	Type       NodeType
	Directive  string
	Arguments  []string
	Children   []*Node
	Pos        Position
	Comment    string
	IsInclude  bool
	IncludeRef string
}

type Severity int

const (
	SeverityError Severity = iota
	SeverityWarning
	SeverityInfo
)

type LintError struct {
	Pos             Position
	Severity        Severity
	RuleID          string
	Message         string
	Suggestion      string
	RelatedPosition *Position
}

func (e *LintError) String() string {
	return e.Message
}

type Variable struct {
	Name       string
	Definition *Position
	References []Position
	IsBuiltin  bool
}

type ConfigContext struct {
	Variables    map[string]*Variable
	Directives   []*Node
	Included     map[string]bool
	CurrentBlock string
	FilePath     string
}

func NewConfigContext(filePath string) *ConfigContext {
	return &ConfigContext{
		Variables: make(map[string]*Variable),
		Included:  make(map[string]bool),
		FilePath:  filePath,
	}
}
