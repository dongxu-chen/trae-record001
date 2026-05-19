package com.logplatform.parser;

import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.query_dsl.*;
import com.logplatform.parser.LogQueryParser.*;
import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.TerminalNode;

import java.util.*;

public class IteratorQueryBuilder {

    private static final String[] DEFAULT_FIELDS = {"message", "logger", "stackTrace", "host", "ip", "traceId"};

    private record StackFrame(ParseTree node, boolean processed, Object context) {}

    private final Deque<StackFrame> stack = new ArrayDeque<>();
    private final Map<ParseTree, Query> results = new IdentityHashMap<>();

    public Query build(ParseTree root) {
        stack.push(new StackFrame(root, false, null));

        while (!stack.isEmpty()) {
            StackFrame frame = stack.pop();

            if (!frame.processed()) {
                processNode(frame);
            } else {
                collectResults(frame);
            }
        }

        return results.get(root);
    }

    private void processNode(StackFrame frame) {
        ParseTree node = frame.node();
        stack.push(new StackFrame(node, true, null));

        if (node instanceof ParseContext ctx) {
            pushChild(ctx.expression());
        } else if (node instanceof OrExpressionContext ctx) {
            for (int i = ctx.andExpression().size() - 1; i >= 0; i--) {
                pushChild(ctx.andExpression(i));
            }
        } else if (node instanceof AndExpressionContext ctx) {
            for (int i = ctx.notExpression().size() - 1; i >= 0; i--) {
                pushChild(ctx.notExpression(i));
            }
        } else if (node instanceof NotExpressionContext ctx) {
            pushChild(ctx.primaryExpression());
        } else if (node instanceof ParenExpressionContext ctx) {
            pushChild(ctx.expression());
        } else if (node instanceof FieldExpressionContext ctx) {
            Query leafQuery = buildFieldQuery(ctx);
            results.put(node, leafQuery);
        } else if (node instanceof PhraseExpressionContext ctx) {
            Query leafQuery = buildPhraseQuery(ctx);
            results.put(node, leafQuery);
        } else if (node instanceof TermExpressionContext ctx) {
            Query leafQuery = buildTermQuery(ctx);
            results.put(node, leafQuery);
        } else if (node instanceof RangeExpressionContext ctx) {
            Query leafQuery = buildRangeQuery(ctx);
            results.put(node, leafQuery);
        } else if (node instanceof TerminalNode) {
        } else {
            for (int i = node.getChildCount() - 1; i >= 0; i--) {
                pushChild(node.getChild(i));
            }
        }
    }

    private void pushChild(ParseTree child) {
        if (child != null) {
            stack.push(new StackFrame(child, false, null));
        }
    }

    private void collectResults(StackFrame frame) {
        ParseTree node = frame.node();

        if (node instanceof OrExpressionContext ctx) {
            List<Query> queries = collectChildQueries(ctx.andExpression());
            if (queries.size() == 1) {
                results.put(node, queries.get(0));
            } else {
                results.put(node, Query.of(b -> b.bool(bool -> bool.should(queries).minimumShouldMatch("1"))));
            }
        } else if (node instanceof AndExpressionContext ctx) {
            List<Query> queries = collectChildQueries(ctx.notExpression());
            if (queries.size() == 1) {
                results.put(node, queries.get(0));
            } else {
                results.put(node, Query.of(b -> b.bool(bool -> bool.must(queries))));
            }
        } else if (node instanceof NotExpressionContext ctx) {
            Query childQuery = results.get(ctx.primaryExpression());
            if (ctx.NOT() != null && childQuery != null) {
                results.put(node, Query.of(b -> b.bool(bool -> bool.mustNot(childQuery))));
            } else if (childQuery != null) {
                results.put(node, childQuery);
            }
        } else if (node instanceof ParenExpressionContext ctx) {
            Query childQuery = results.get(ctx.expression());
            if (childQuery != null) {
                results.put(node, childQuery);
            }
        } else if (node instanceof ParseContext ctx) {
            Query childQuery = results.get(ctx.expression());
            if (childQuery != null) {
                results.put(node, childQuery);
            }
        }
    }

    private List<Query> collectChildQueries(List<? extends ParseTree> children) {
        List<Query> queries = new ArrayList<>();
        for (ParseTree child : children) {
            Query q = results.get(child);
            if (q != null) {
                queries.add(q);
            }
        }
        return queries;
    }

    private Query buildFieldQuery(FieldExpressionContext ctx) {
        String field = ctx.IDENTIFIER().getText();

        if (ctx.term() != null) {
            String value = ctx.term().getText();
            if (containsWildcard(value)) {
                return buildWildcardQuery(field, value);
            }
            return Query.of(b -> b.match(m -> m.field(field).query(value)));
        } else if (ctx.phrase() != null) {
            String phrase = stripQuotes(ctx.phrase().PHRASE().getText());
            return Query.of(b -> b.matchPhrase(m -> m.field(field).query(phrase)));
        } else if (ctx.rangeExpr() != null) {
            return buildRangeQueryFromContext(field, ctx.rangeExpr());
        } else if (ctx.wildcardTerm() != null) {
            return buildWildcardQuery(field, ctx.wildcardTerm().getText());
        }

        return null;
    }

    private Query buildPhraseQuery(PhraseExpressionContext ctx) {
        String phrase = stripQuotes(ctx.PHRASE().getText());
        return Query.of(b -> b.multiMatch(m -> m
                .fields(Arrays.asList(DEFAULT_FIELDS))
                .query(phrase)
                .type(TextQueryType.Phrase)));
    }

    private Query buildTermQuery(TermExpressionContext ctx) {
        String term = ctx.getText();
        if (containsWildcard(term)) {
            return buildMultiMatchWildcardQuery(term);
        }
        return Query.of(b -> b.multiMatch(m -> m
                .fields(Arrays.asList(DEFAULT_FIELDS))
                .query(term)
                .type(TextQueryType.BestFields)));
    }

    private Query buildRangeQuery(RangeExpressionContext ctx) {
        return null;
    }

    private Query buildRangeQueryFromContext(String field, RangeExprContext ctx) {
        String from = ctx.value(0).getText();
        String to = ctx.value(1).getText();

        if (ctx.inclusiveRange() != null) {
            return Query.of(b -> b.range(r -> r
                    .field(field)
                    .gte(FieldValue.of(stripQuotes(from)))
                    .lte(FieldValue.of(stripQuotes(to)))));
        } else {
            return Query.of(b -> b.range(r -> r
                    .field(field)
                    .gt(FieldValue.of(stripQuotes(from)))
                    .lt(FieldValue.of(stripQuotes(to)))));
        }
    }

    private Query buildWildcardQuery(String field, String pattern) {
        return Query.of(b -> b.wildcard(w -> w.field(field).value(pattern.toLowerCase())));
    }

    private Query buildMultiMatchWildcardQuery(String pattern) {
        List<Query> queries = new ArrayList<>();
        for (String field : DEFAULT_FIELDS) {
            queries.add(buildWildcardQuery(field, pattern));
        }
        return Query.of(b -> b.bool(bool -> bool.should(queries).minimumShouldMatch("1")));
    }

    private boolean containsWildcard(String text) {
        return text.contains("*") || text.contains("?");
    }

    private String stripQuotes(String text) {
        if ((text.startsWith("\"") && text.endsWith("\"")) ||
            (text.startsWith("'") && text.endsWith("'"))) {
            return text.substring(1, text.length() - 1);
        }
        return text;
    }
}
