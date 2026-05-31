package router

import "errors"

var (
	ErrRuleNotFound       = errors.New("routing rule not found")
	ErrInvalidQuerySource = errors.New("invalid query source")
	ErrInvalidSQL         = errors.New("invalid SQL query")
	ErrNoDatabaseSpecified = errors.New("no database specified")
	ErrClientNotAvailable = errors.New("ClickHouse client not available")
)
