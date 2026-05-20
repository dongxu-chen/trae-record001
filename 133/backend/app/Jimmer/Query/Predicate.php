<?php

namespace App\Jimmer\Query;

abstract class Predicate
{
    abstract public function apply(QueryBuilder $builder): void;
    
    public static function and(Predicate ...$predicates): AndPredicate
    {
        return new AndPredicate(...$predicates);
    }
    
    public static function or(Predicate ...$predicates): OrPredicate
    {
        return new OrPredicate(...$predicates);
    }
    
    public static function not(Predicate $predicate): NotPredicate
    {
        return new NotPredicate($predicate);
    }
    
    public static function eq(string $column, $value): ComparisonPredicate
    {
        return new ComparisonPredicate($column, '=', $value);
    }
    
    public static function ne(string $column, $value): ComparisonPredicate
    {
        return new ComparisonPredicate($column, '!=', $value);
    }
    
    public static function gt(string $column, $value): ComparisonPredicate
    {
        return new ComparisonPredicate($column, '>', $value);
    }
    
    public static function gte(string $column, $value): ComparisonPredicate
    {
        return new ComparisonPredicate($column, '>=', $value);
    }
    
    public static function lt(string $column, $value): ComparisonPredicate
    {
        return new ComparisonPredicate($column, '<', $value);
    }
    
    public static function lte(string $column, $value): ComparisonPredicate
    {
        return new ComparisonPredicate($column, '<=', $value);
    }
    
    public static function like(string $column, string $value): ComparisonPredicate
    {
        return new ComparisonPredicate($column, 'LIKE', $value);
    }
    
    public static function in(string $column, array $values): InPredicate
    {
        return new InPredicate($column, $values);
    }
    
    public static function notIn(string $column, array $values): InPredicate
    {
        return new InPredicate($column, $values, true);
    }
    
    public static function between(string $column, $min, $max): BetweenPredicate
    {
        return new BetweenPredicate($column, $min, $max);
    }
    
    public static function notBetween(string $column, $min, $max): BetweenPredicate
    {
        return new BetweenPredicate($column, $min, $max, true);
    }
    
    public static function isNull(string $column): NullPredicate
    {
        return new NullPredicate($column);
    }
    
    public static function isNotNull(string $column): NullPredicate
    {
        return new NullPredicate($column, true);
    }
    
    public static function raw(string $sql, array $bindings = []): RawPredicate
    {
        return new RawPredicate($sql, $bindings);
    }
}

class AndPredicate extends Predicate
{
    protected $predicates = [];
    
    public function __construct(Predicate ...$predicates)
    {
        $this->predicates = $predicates;
    }
    
    public function apply(QueryBuilder $builder): void
    {
        foreach ($this->predicates as $predicate) {
            $predicate->apply($builder);
        }
    }
}

class OrPredicate extends Predicate
{
    protected $predicates = [];
    
    public function __construct(Predicate ...$predicates)
    {
        $this->predicates = $predicates;
    }
    
    public function apply(QueryBuilder $builder): void
    {
        $first = true;
        foreach ($this->predicates as $predicate) {
            if ($first) {
                $predicate->apply($builder);
                $first = false;
            } else {
                $builder->whereGroup(function ($q) use ($predicate) {
                    $predicate->apply($q);
                }, 'or');
            }
        }
    }
}

class NotPredicate extends Predicate
{
    protected $predicate;
    
    public function __construct(Predicate $predicate)
    {
        $this->predicate = $predicate;
    }
    
    public function apply(QueryBuilder $builder): void
    {
        $builder->whereRaw('NOT (1=1)');
        $this->predicate->apply($builder);
    }
}

class ComparisonPredicate extends Predicate
{
    protected $column;
    protected $operator;
    protected $value;
    
    public function __construct(string $column, string $operator, $value)
    {
        $this->column = $column;
        $this->operator = $operator;
        $this->value = $value;
    }
    
    public function apply(QueryBuilder $builder): void
    {
        $builder->where($this->column, $this->operator, $this->value);
    }
}

class InPredicate extends Predicate
{
    protected $column;
    protected $values;
    protected $not;
    
    public function __construct(string $column, array $values, bool $not = false)
    {
        $this->column = $column;
        $this->values = $values;
        $this->not = $not;
    }
    
    public function apply(QueryBuilder $builder): void
    {
        $builder->whereIn($this->column, $this->values, 'and', $this->not);
    }
}

class BetweenPredicate extends Predicate
{
    protected $column;
    protected $min;
    protected $max;
    protected $not;
    
    public function __construct(string $column, $min, $max, bool $not = false)
    {
        $this->column = $column;
        $this->min = $min;
        $this->max = $max;
        $this->not = $not;
    }
    
    public function apply(QueryBuilder $builder): void
    {
        $builder->whereBetween($this->column, [$this->min, $this->max], 'and', $this->not);
    }
}

class NullPredicate extends Predicate
{
    protected $column;
    protected $not;
    
    public function __construct(string $column, bool $not = false)
    {
        $this->column = $column;
        $this->not = $not;
    }
    
    public function apply(QueryBuilder $builder): void
    {
        if ($this->not) {
            $builder->whereNotNull($this->column);
        } else {
            $builder->whereNull($this->column);
        }
    }
}

class RawPredicate extends Predicate
{
    protected $sql;
    protected $bindings;
    
    public function __construct(string $sql, array $bindings = [])
    {
        $this->sql = $sql;
        $this->bindings = $bindings;
    }
    
    public function apply(QueryBuilder $builder): void
    {
        $builder->whereRaw($this->sql, $this->bindings);
    }
}
