package parser

import (
	"nginx-lint/internal/model"
	"strings"
	"unicode"
)

type Lexer struct {
	input   string
	pos     int
	line    int
	col     int
	file    string
	lastCol int
}

func NewLexer(input, file string) *Lexer {
	return &Lexer{
		input: input,
		pos:   0,
		line:  1,
		col:   1,
		file:  file,
	}
}

func (l *Lexer) peek() rune {
	if l.pos >= len(l.input) {
		return 0
	}
	return rune(l.input[l.pos])
}

func (l *Lexer) next() rune {
	if l.pos >= len(l.input) {
		return 0
	}
	ch := rune(l.input[l.pos])
	l.pos++
	if ch == '\n' {
		l.lastCol = l.col
		l.line++
		l.col = 1
	} else {
		l.col++
	}
	return ch
}

func (l *Lexer) backup() {
	if l.pos > 0 {
		l.pos--
		ch := rune(l.input[l.pos])
		if ch == '\n' {
			l.line--
			l.col = l.lastCol
		} else {
			l.col--
		}
	}
}

func (l *Lexer) position() model.Position {
	return model.Position{
		File:   l.file,
		Line:   l.line,
		Column: l.col,
	}
}

func (l *Lexer) skipWhitespace() {
	for {
		ch := l.peek()
		if ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n' {
			l.next()
		} else {
			break
		}
	}
}

func (l *Lexer) NextToken() model.Token {
	l.skipWhitespace()

	pos := l.position()
	ch := l.peek()

	if ch == 0 {
		return model.Token{Type: model.TokenEOF, Pos: pos}
	}

	switch ch {
	case '#':
		return l.readComment(pos)
	case '{':
		l.next()
		return model.Token{Type: model.TokenLBrace, Value: "{", Pos: pos}
	case '}':
		l.next()
		return model.Token{Type: model.TokenRBrace, Value: "}", Pos: pos}
	case ';':
		l.next()
		return model.Token{Type: model.TokenSemicolon, Value: ";", Pos: pos}
	case '"':
		return l.readQuotedString(pos)
	case '\'':
		return l.readSingleQuotedString(pos)
	case '$':
		return l.readVariable(pos)
	default:
		if unicode.IsDigit(ch) {
			return l.readNumber(pos)
		}
		return l.readIdentifier(pos)
	}
}

func (l *Lexer) readComment(pos model.Position) model.Token {
	var sb strings.Builder
	l.next()
	for {
		ch := l.peek()
		if ch == 0 || ch == '\n' {
			break
		}
		sb.WriteRune(l.next())
	}
	return model.Token{Type: model.TokenComment, Value: sb.String(), Pos: pos}
}

func (l *Lexer) readQuotedString(pos model.Position) model.Token {
	var sb strings.Builder
	l.next()
	for {
		ch := l.peek()
		if ch == 0 {
			break
		}
		if ch == '\\' {
			l.next()
			next := l.next()
			switch next {
			case 'n':
				sb.WriteRune('\n')
			case 't':
				sb.WriteRune('\t')
			case 'r':
				sb.WriteRune('\r')
			case '"':
				sb.WriteRune('"')
			case '\\':
				sb.WriteRune('\\')
			default:
				sb.WriteRune('\\')
				sb.WriteRune(next)
			}
			continue
		}
		if ch == '"' {
			l.next()
			break
		}
		sb.WriteRune(l.next())
	}
	return model.Token{Type: model.TokenString, Value: sb.String(), Pos: pos}
}

func (l *Lexer) readSingleQuotedString(pos model.Position) model.Token {
	var sb strings.Builder
	l.next()
	for {
		ch := l.peek()
		if ch == 0 {
			break
		}
		if ch == '\\' {
			l.next()
			next := l.next()
			if next == '\'' {
				sb.WriteRune('\'')
			} else {
				sb.WriteRune('\\')
				sb.WriteRune(next)
			}
			continue
		}
		if ch == '\'' {
			l.next()
			break
		}
		sb.WriteRune(l.next())
	}
	return model.Token{Type: model.TokenString, Value: sb.String(), Pos: pos}
}

func (l *Lexer) readVariable(pos model.Position) model.Token {
	var sb strings.Builder
	sb.WriteRune(l.next())
	ch := l.peek()
	if ch == '{' {
		sb.WriteRune(l.next())
		for {
			ch = l.peek()
			if ch == 0 || ch == '}' {
				if ch == '}' {
					sb.WriteRune(l.next())
				}
				break
			}
			sb.WriteRune(l.next())
		}
	} else {
		for {
			ch = l.peek()
			if ch == 0 || !(unicode.IsLetter(ch) || unicode.IsDigit(ch) || ch == '_') {
				break
			}
			sb.WriteRune(l.next())
		}
	}
	return model.Token{Type: model.TokenVariable, Value: sb.String(), Pos: pos}
}

func (l *Lexer) readNumber(pos model.Position) model.Token {
	var sb strings.Builder
	hasDot := false
	for {
		ch := l.peek()
		if ch == '.' && !hasDot {
			hasDot = true
			sb.WriteRune(l.next())
		} else if unicode.IsDigit(ch) {
			sb.WriteRune(l.next())
		} else {
			break
		}
	}
	return model.Token{Type: model.TokenNumber, Value: sb.String(), Pos: pos}
}

func (l *Lexer) readIdentifier(pos model.Position) model.Token {
	var sb strings.Builder
	for {
		ch := l.peek()
		if ch == 0 || ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r' ||
			ch == '{' || ch == '}' || ch == ';' || ch == '#' ||
			ch == '"' || ch == '\'' || ch == '$' {
			break
		}
		sb.WriteRune(l.next())
	}
	return model.Token{Type: model.TokenIdentifier, Value: sb.String(), Pos: pos}
}
