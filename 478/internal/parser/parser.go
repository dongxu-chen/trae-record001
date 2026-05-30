package parser

import (
	"nginx-lint/internal/model"
)

type Parser struct {
	lexer     *Lexer
	curToken  model.Token
	peekToken model.Token
	errors    []*model.LintError
	filePath  string
}

func NewParser(input, filePath string) *Parser {
	lexer := NewLexer(input, filePath)
	p := &Parser{
		lexer:    lexer,
		errors:   []*model.LintError{},
		filePath: filePath,
	}
	p.nextToken()
	p.nextToken()
	return p
}

func (p *Parser) Errors() []*model.LintError {
	return p.errors
}

func (p *Parser) nextToken() {
	p.curToken = p.peekToken
	p.peekToken = p.lexer.NextToken()
}

func (p *Parser) Parse() []*model.Node {
	var nodes []*model.Node

	for p.curToken.Type != model.TokenEOF {
		node := p.parseStatement()
		if node != nil {
			nodes = append(nodes, node)
		}
		p.nextToken()
	}

	return nodes
}

func (p *Parser) parseStatement() *model.Node {
	switch p.curToken.Type {
	case model.TokenComment:
		return p.parseComment()
	case model.TokenIdentifier, model.TokenVariable, model.TokenString:
		return p.parseDirectiveOrBlock()
	default:
		if p.curToken.Type != model.TokenEOF {
			p.addError(p.curToken.Pos, "ERR_SYNTAX",
				"意外的token: "+p.curToken.Value,
				"检查语法，确保指令格式正确")
		}
		return nil
	}
}

func (p *Parser) parseComment() *model.Node {
	return &model.Node{
		Type:    model.NodeComment,
		Comment: p.curToken.Value,
		Pos:     p.curToken.Pos,
	}
}

func (p *Parser) parseDirectiveOrBlock() *model.Node {
	pos := p.curToken.Pos
	directive := p.curToken.Value

	var args []string
	p.nextToken()

	for p.curToken.Type != model.TokenEOF &&
		p.curToken.Type != model.TokenSemicolon &&
		p.curToken.Type != model.TokenLBrace &&
		p.curToken.Type != model.TokenRBrace {

		args = append(args, p.curToken.Value)
		p.nextToken()
	}

	node := &model.Node{
		Directive: directive,
		Arguments: args,
		Pos:       pos,
	}

	if directive == "include" && len(args) > 0 {
		node.Type = model.NodeInclude
		node.IsInclude = true
		node.IncludeRef = args[0]
	}

	if p.curToken.Type == model.TokenLBrace {
		node.Type = model.NodeBlock
		node.Children = p.parseBlock()
	} else if p.curToken.Type == model.TokenSemicolon {
		if node.Type != model.NodeInclude {
			node.Type = model.NodeDirective
		}
	} else if p.curToken.Type == model.TokenEOF {
		p.addError(pos, "ERR_UNTERMINATED",
			"指令未以分号结尾",
			"在指令末尾添加分号 ';'")
		node.Type = model.NodeDirective
	} else if p.curToken.Type == model.TokenRBrace {
		p.addError(pos, "ERR_UNEXPECTED_RBRACE",
			"意外的右大括号",
			"检查大括号匹配，或添加分号结束指令")
		node.Type = model.NodeDirective
	}

	return node
}

func (p *Parser) parseBlock() []*model.Node {
	var children []*model.Node
	p.nextToken()

	braceCount := 1

	for p.curToken.Type != model.TokenEOF && braceCount > 0 {
		if p.curToken.Type == model.TokenRBrace {
			braceCount--
			if braceCount == 0 {
				break
			}
		}
		if p.curToken.Type == model.TokenLBrace {
			braceCount++
		}

		node := p.parseStatement()
		if node != nil {
			children = append(children, node)
		}
		p.nextToken()
	}

	if braceCount > 0 {
		p.addError(p.curToken.Pos, "ERR_UNMATCHED_BRACE",
			"缺少匹配的右大括号",
			"在适当位置添加右大括号 '}'")
	}

	return children
}

func (p *Parser) addError(pos model.Position, ruleID, msg, suggestion string) {
	p.errors = append(p.errors, &model.LintError{
		Pos:        pos,
		Severity:   model.SeverityError,
		RuleID:     ruleID,
		Message:    msg,
		Suggestion: suggestion,
	})
}

func ParseFile(content, filePath string) ([]*model.Node, []*model.LintError) {
	parser := NewParser(content, filePath)
	nodes := parser.Parse()
	errs := parser.Errors()
	return nodes, errs
}
