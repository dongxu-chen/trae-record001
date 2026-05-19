grammar LogQuery;

@header {
package com.logplatform.parser;
}

parse
    : expression EOF
    ;

expression
    : orExpression
    ;

orExpression
    : andExpression (OR andExpression)*
    ;

andExpression
    : notExpression (AND notExpression)*
    ;

notExpression
    : (NOT)? primaryExpression
    ;

primaryExpression
    : LPAREN expression RPAREN                        # parenExpression
    | fieldExpr                                       # fieldExpression
    | rangeExpr                                       # rangeExpression
    | phrase                                          # phraseExpression
    | term                                            # termExpression
    ;

fieldExpr
    : IDENTIFIER COLON (term | phrase | rangeExpr | wildcardTerm)
    ;

rangeExpr
    : LBRACKET value TO value RBRACKET                # inclusiveRange
    | LBRACE value TO value RBRACE                    # exclusiveRange
    ;

phrase
    : PHRASE
    ;

term
    : WILDCARD? IDENTIFIER WILDCARD?
    | NUMBER
    ;

wildcardTerm
    : WILDCARD? IDENTIFIER WILDCARD?
    ;

value
    : PHRASE
    | IDENTIFIER
    | NUMBER
    | DATETIME
    ;

AND
    : 'AND' | '&&'
    ;

OR
    : 'OR' | '||'
    ;

NOT
    : 'NOT' | '!'
    ;

TO
    : 'TO'
    ;

COLON
    : ':'
    ;

LPAREN
    : '('
    ;

RPAREN
    : ')'
    ;

LBRACKET
    : '['
    ;

RBRACKET
    : ']'
    ;

LBRACE
    : '{'
    ;

RBRACE
    : '}'
    ;

PHRASE
    : '"' ( ~["\\] | '\\' . )* '"'
    | '\'' ( ~['\\] | '\\' . )* '\''
    ;

WILDCARD
    : '*'
    | '?'
    ;

NUMBER
    : '-'? DIGIT+ ('.' DIGIT+)?
    ;

DATETIME
    : DIGIT{4} '-' DIGIT{2} '-' DIGIT{2} ('T' DIGIT{2} ':' DIGIT{2} (':' DIGIT{2})?)?
    ;

IDENTIFIER
    : ~[ \t\r\n(){}[\]:"'*?] ~[ \t\r\n(){}[\]:]*
    ;

WHITESPACE
    : [ \t\r\n]+ -> skip
    ;

fragment DIGIT
    : [0-9]
    ;
