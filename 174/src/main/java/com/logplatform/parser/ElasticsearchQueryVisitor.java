package com.logplatform.parser;

import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.query_dsl.*;
import co.elastic.clients.util.ObjectBuilder;
import org.antlr.v4.runtime.tree.ParseTree;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

public class ElasticsearchQueryVisitor extends LogQueryParserBaseVisitor<Query> {

    private static final String DEFAULT_FIELD = "message";

    @Override
    public Query visitParse(LogQueryParser.ParseContext ctx) {
        return visit(ctx.expression());
    }

    @Override
    public Query visitOrExpression(LogQueryParser.OrExpressionContext ctx) {
        if (ctx.andExpression().size() == 1) {
            return visit(ctx.andExpression(0));
        }

        List<Query> queries = new ArrayList<>();
        for (LogQueryParser.AndExpressionContext expr : ctx.andExpression()) {
            queries.add(visit(expr));
        }

        return Query.of(b -> b.bool(BoolQuery.of(bool -> bool.should(queries).minimumShouldMatch("1"))));
    }

    @Override
    public Query visitAndExpression(LogQueryParser.AndExpressionContext ctx) {
        if (ctx.notExpression().size() == 1) {
            return visit(ctx.notExpression(0));
        }

        List<Query> queries = new ArrayList<>();
        for (LogQueryParser.NotExpressionContext expr : ctx.notExpression()) {
            queries.add(visit(expr));
        }

        return Query.of(b -> b.bool(BoolQuery.of(bool -> bool.must(queries))));
    }

    @Override
    public Query visitNotExpression(LogQueryParser.NotExpressionContext ctx) {
        Query query = visit(ctx.primaryExpression());
        if (ctx.NOT() != null) {
            return Query.of(b -> b.bool(BoolQuery.of(bool -> bool.mustNot(query))));
        }
        return query;
    }

    @Override
    public Query visitParenExpression(LogQueryParser.ParenExpressionContext ctx) {
        return visit(ctx.expression());
    }

    @Override
    public Query visitFieldExpression(LogQueryParser.FieldExpressionContext ctx) {
        String field = ctx.IDENTIFIER().getText();

        if (ctx.term() != null) {
            return buildFieldQuery(field, ctx.term().getText());
        } else if (ctx.phrase() != null) {
            return buildPhraseQuery(field, stripQuotes(ctx.phrase().PHRASE().getText()));
        } else if (ctx.rangeExpr() != null) {
            return buildRangeQuery(field, ctx.rangeExpr());
        } else if (ctx.wildcardTerm() != null) {
            return buildWildcardQuery(field, ctx.wildcardTerm().getText());
        }

        return null;
    }

    @Override
    public Query visitPhraseExpression(LogQueryParser.PhraseExpressionContext ctx) {
        String phrase = stripQuotes(ctx.PHRASE().getText());
        return buildMultiMatchQuery(phrase, "phrase");
    }

    @Override
    public Query visitTermExpression(LogQueryParser.TermExpressionContext ctx) {
        String term = ctx.getText();
        if (term.contains("*") || term.contains("?")) {
            return buildMultiMatchWildcardQuery(term);
        }
        return buildMultiMatchQuery(term, "best_fields");
    }

    private Query buildFieldQuery(String field, String value) {
        if (value.contains("*") || value.contains("?")) {
            return buildWildcardQuery(field, value);
        }
        return Query.of(b -> b.match(MatchQuery.of(m -> m.field(field).query(value))));
    }

    private Query buildPhraseQuery(String field, String phrase) {
        return Query.of(b -> b.matchPhrase(MatchPhraseQuery.of(m -> m.field(field).query(phrase))));
    }

    private Query buildWildcardQuery(String field, String pattern) {
        return Query.of(b -> b.wildcard(WildcardQuery.of(w -> w.field(field).value(pattern.toLowerCase()))));
    }

    private Query buildMultiMatchQuery(String value, String type) {
        return Query.of(b -> b.multiMatch(MultiMatchQuery.of(m -> m
                .fields("message", "logger", "stackTrace", "host", "ip", "traceId")
                .query(value)
                .type(TextQueryType.valueOf(type))
        )));
    }

    private Query buildMultiMatchWildcardQuery(String pattern) {
        List<Query> queries = new ArrayList<>();
        String[] fields = {"message", "logger", "stackTrace", "host", "ip", "traceId"};

        for (String field : fields) {
            queries.add(buildWildcardQuery(field, pattern));
        }

        return Query.of(b -> b.bool(BoolQuery.of(bool -> bool.should(queries).minimumShouldMatch("1"))));
    }

    private Query buildRangeQuery(String field, LogQueryParser.RangeExprContext ctx) {
        String from = ctx.value(0).getText();
        String to = ctx.value(1).getText();

        if (ctx.inclusiveRange() != null) {
            return Query.of(b -> b.range(RangeQuery.of(r -> r
                    .field(field)
                    .gte(FieldValue.of(stripQuotes(from)))
                    .lte(FieldValue.of(stripQuotes(to)))
            )));
        } else {
            return Query.of(b -> b.range(RangeQuery.of(r -> r
                    .field(field)
                    .gt(FieldValue.of(stripQuotes(from)))
                    .lt(FieldValue.of(stripQuotes(to)))
            )));
        }
    }

    private String stripQuotes(String text) {
        if ((text.startsWith("\"") && text.endsWith("\"")) ||
            (text.startsWith("'") && text.endsWith("'"))) {
            return text.substring(1, text.length() - 1);
        }
        return text;
    }
}
