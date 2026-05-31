package clickhouse

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	_ "github.com/ClickHouse/clickhouse-go/v2"
	"ch-lifecycle/config"
	"go.uber.org/zap"
)

type Client struct {
	db     *sql.DB
	logger *zap.Logger
	cfg    config.ClickHouseConfig
}

func NewClient(cfg config.ClickHouseConfig, logger *zap.Logger) (*Client, error) {
	dsn := fmt.Sprintf("clickhouse://%s:%s@%s:%d/%s?dial_timeout=%ds",
		cfg.Username, cfg.Password, cfg.Hosts[0], cfg.Port, cfg.Database, cfg.DialTimeout,
	)
	db, err := sql.Open("clickhouse", dsn)
	if err != nil {
		return nil, fmt.Errorf("open clickhouse: %w", err)
	}
	db.SetMaxOpenConns(cfg.MaxOpenConns)
	db.SetMaxIdleConns(cfg.MaxIdleConns)
	db.SetConnMaxLifetime(time.Hour)
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(cfg.DialTimeout)*time.Second)
	defer cancel()
	if err := db.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("ping clickhouse: %w", err)
	}
	logger.Info("connected to ClickHouse", zap.Strings("hosts", cfg.Hosts))
	return &Client{db: db, logger: logger, cfg: cfg}, nil
}

func (c *Client) Close() error {
	return c.db.Close()
}

func (c *Client) Query(ctx context.Context, query string, args ...interface{}) (*sql.Rows, error) {
	return c.db.QueryContext(ctx, query, args...)
}

func (c *Client) Exec(ctx context.Context, query string, args ...interface{}) (sql.Result, error) {
	return c.db.ExecContext(ctx, query, args...)
}

func (c *Client) QueryRow(ctx context.Context, query string, args ...interface{}) *sql.Row {
	return c.db.QueryRowContext(ctx, query, args...)
}

type PartitionInfo struct {
	Database      string    `json:"database"`
	Table         string    `json:"table"`
	Partition     string    `json:"partition"`
	Name          string    `json:"name"`
	Active        uint8     `json:"active"`
	Rows          uint64    `json:"rows"`
	BytesOnDisk   uint64    `json:"bytes_on_disk"`
	Modification  string    `json:"modification"`
	MinDate       string    `json:"min_date"`
	MaxDate       string    `json:"max_date"`
	Level         uint32    `json:"level"`
	Path          string    `json:"path"`
}

func (c *Client) GetPartitions(ctx context.Context, database, table string) ([]PartitionInfo, error) {
	query := `
		SELECT database, table, partition, name, active,
		       sum(rows) AS rows, sum(bytes_on_disk) AS bytes_on_disk,
		       max(modification_time) AS modification,
		       min(min_date) AS min_date, max(max_date) AS max_date,
		       max(level) AS level, any(path) AS path
		FROM system.parts
		WHERE database = ? AND table = ? AND active = 1
		GROUP BY database, table, partition, name
		ORDER BY partition`
	rows, err := c.Query(ctx, query, database, table)
	if err != nil {
		return nil, fmt.Errorf("query partitions: %w", err)
	}
	defer rows.Close()
	var parts []PartitionInfo
	for rows.Next() {
		var p PartitionInfo
		if err := rows.Scan(&p.Database, &p.Table, &p.Partition, &p.Name, &p.Active,
			&p.Rows, &p.BytesOnDisk, &p.Modification, &p.MinDate, &p.MaxDate, &p.Level, &p.Path); err != nil {
			return nil, fmt.Errorf("scan partition: %w", err)
		}
		parts = append(parts, p)
	}
	return parts, nil
}

type TableInfo struct {
	Database         string `json:"database"`
	Name             string `json:"name"`
	Engine           string `json:"engine"`
	TotalRows        uint64 `json:"total_rows"`
	TotalBytes       uint64 `json:"total_bytes"`
	PartitionKey     string `json:"partition_key"`
	SortingKey       string `json:"sorting_key"`
	PrimaryKey       string `json:"primary_key"`
	StoragePolicy    string `json:"storage_policy"`
}

func (c *Client) GetTables(ctx context.Context, database string) ([]TableInfo, error) {
	query := `
		SELECT database, name, engine,
		       total_rows, total_bytes,
		       partition_key, sorting_key, primary_key,
		       storage_policy
		FROM system.tables
		WHERE database = ?`
	rows, err := c.Query(ctx, query, database)
	if err != nil {
		return nil, fmt.Errorf("query tables: %w", err)
	}
	defer rows.Close()
	var tables []TableInfo
	for rows.Next() {
		var t TableInfo
		if err := rows.Scan(&t.Database, &t.Name, &t.Engine, &t.TotalRows, &t.TotalBytes,
			&t.PartitionKey, &t.SortingKey, &t.PrimaryKey, &t.StoragePolicy); err != nil {
			return nil, fmt.Errorf("scan table: %w", err)
		}
		tables = append(tables, t)
	}
	return tables, nil
}

type StoragePolicyInfo struct {
	Name     string `json:"name"`
	Disks    string `json:"disks"`
	Volumes  string `json:"volumes"`
	MoveFactor float64 `json:"move_factor"`
}

func (c *Client) GetStoragePolicies(ctx context.Context) ([]StoragePolicyInfo, error) {
	query := `
		SELECT name, disks, volumes, move_factor
		FROM system.storage_policies`
	rows, err := c.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("query storage policies: %w", err)
	}
	defer rows.Close()
	var policies []StoragePolicyInfo
	for rows.Next() {
		var p StoragePolicyInfo
		if err := rows.Scan(&p.Name, &p.Disks, &p.Volumes, &p.MoveFactor); err != nil {
			return nil, fmt.Errorf("scan storage policy: %w", err)
		}
		policies = append(policies, p)
	}
	return policies, nil
}

type DiskInfo struct {
	Name     string `json:"name"`
	Path     string `json:"path"`
	Type     string `json:"type"`
	FreeSpace uint64 `json:"free_space"`
	TotalSpace uint64 `json:"total_space"`
}

func (c *Client) GetDisks(ctx context.Context) ([]DiskInfo, error) {
	query := `
		SELECT name, path, type, free_space, total_space
		FROM system.disks`
	rows, err := c.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("query disks: %w", err)
	}
	defer rows.Close()
	var disks []DiskInfo
	for rows.Next() {
		var d DiskInfo
		if err := rows.Scan(&d.Name, &d.Path, &d.Type, &d.FreeSpace, &d.TotalSpace); err != nil {
			return nil, fmt.Errorf("scan disk: %w", err)
		}
		disks = append(disks, d)
	}
	return disks, nil
}

func (c *Client) MovePartitionToDisk(ctx context.Context, database, table, partition, disk string) error {
	query := fmt.Sprintf(
		`ALTER TABLE %s.%s MOVE PARTITION '%s' TO DISK '%s'`,
		database, table, partition, disk,
	)
	_, err := c.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("move partition to disk: %w", err)
	}
	c.logger.Info("moved partition",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
		zap.String("disk", disk),
	)
	return nil
}

func (c *Client) ShadowMovePartition(ctx context.Context, database, table, partition, targetDisk string) error {
	c.logger.Info("starting shadow partition move",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
		zap.String("target_disk", targetDisk),
	)

	shadowPart := partition + "__shadow"

	copyQuery := fmt.Sprintf(
		`ALTER TABLE %s.%s COPY PARTITION '%s' TO DISK '%s'`,
		database, table, partition, targetDisk,
	)
	if _, err := c.Exec(ctx, copyQuery); err != nil {
		return fmt.Errorf("shadow copy partition to disk %s: %w", targetDisk, err)
	}
	c.logger.Info("shadow partition copied to target disk",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
		zap.String("target_disk", targetDisk),
	)

	replaceQuery := fmt.Sprintf(
		`ALTER TABLE %s.%s REPLACE PARTITION '%s' FROM %s_shadow`,
		database, table, partition, table,
	)
	if _, err := c.Exec(ctx, replaceQuery); err != nil {
		c.logger.Warn("replace partition failed, falling back to direct move",
			zap.String("partition", partition),
			zap.Error(err),
		)
		return c.MovePartitionToDisk(ctx, database, table, partition, targetDisk)
	}
	c.logger.Info("shadow partition replaced, dropping old",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
	)

	_ = shadowPart

	return nil
}

func (c *Client) CreateShadowPartition(ctx context.Context, database, table, partition, targetDisk string) error {
	c.logger.Info("creating shadow partition on target disk",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
		zap.String("target_disk", targetDisk),
	)
	query := fmt.Sprintf(
		`ALTER TABLE %s.%s MOVE PARTITION '%s' TO DISK '%s'`,
		database, table, partition, targetDisk,
	)
	_, err := c.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("create shadow partition: %w", err)
	}
	return nil
}

func (c *Client) VerifyShadowPartition(ctx context.Context, database, table, partition string) (bool, error) {
	query := fmt.Sprintf(
		`SELECT count() FROM %s.%s WHERE _partition_id = (SELECT _partition_id FROM system.parts WHERE database = '%s' AND table = '%s' AND partition = '%s' AND active = 1 LIMIT 1)`,
		database, table, database, table, partition,
	)
	var count uint64
	if err := c.QueryRow(ctx, query).Scan(&count); err != nil {
		return false, fmt.Errorf("verify shadow partition: %w", err)
	}
	return count > 0, nil
}

func (c *Client) DropOldPartition(ctx context.Context, database, table, partition string) error {
	c.logger.Info("dropping old partition after shadow switch",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
	)
	return c.DropPartition(ctx, database, table, partition)
}

func (c *Client) DropPartition(ctx context.Context, database, table, partition string) error {
	query := fmt.Sprintf(
		`ALTER TABLE %s.%s DROP PARTITION '%s'`,
		database, table, partition,
	)
	_, err := c.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("drop partition: %w", err)
	}
	c.logger.Info("dropped partition",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
	)
	return nil
}

func (c *Client) FreezePartition(ctx context.Context, database, table, partition string) error {
	query := fmt.Sprintf(
		`ALTER TABLE %s.%s FREEZE PARTITION '%s'`,
		database, table, partition,
	)
	_, err := c.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("freeze partition: %w", err)
	}
	c.logger.Info("froze partition",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
	)
	return nil
}

func (c *Client) SetTableTTL(ctx context.Context, database, table, column, interval string) error {
	query := fmt.Sprintf(
		`ALTER TABLE %s.%s MODIFY TTL %s + INTERVAL %s`,
		database, table, column, interval,
	)
	_, err := c.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("set table ttl: %w", err)
	}
	c.logger.Info("set table TTL",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("column", column),
		zap.String("interval", interval),
	)
	return nil
}

func (c *Client) SetStoragePolicy(ctx context.Context, database, table, policy string) error {
	query := fmt.Sprintf(
		`ALTER TABLE %s.%s MODIFY SETTING storage_policy = '%s'`,
		database, table, policy,
	)
	_, err := c.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("set storage policy: %w", err)
	}
	c.logger.Info("set storage policy",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("policy", policy),
	)
	return nil
}

func (c *Client) OptimizeTable(ctx context.Context, database, table, partition string, final bool) error {
	query := fmt.Sprintf(`ALTER TABLE %s.%s PARTITION '%s' OPTIMIZE`, database, table, partition)
	if final {
		query += " FINAL"
	}
	_, err := c.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("optimize partition: %w", err)
	}
	c.logger.Info("optimized partition",
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
		zap.Bool("final", final),
	)
	return nil
}
