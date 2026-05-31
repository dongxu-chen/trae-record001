package database

import (
	"database/sql"
	"fmt"
	"log"
	"sync"
	"time"

	_ "github.com/go-sql-driver/mysql"
	"mysql-partition-tool/config"
	"mysql-partition-tool/models"
)

type DBManager struct {
	db *sql.DB
	sync.RWMutex
}

var instance *DBManager
var once sync.Once

func GetInstance() *DBManager {
	once.Do(func() {
		instance = &DBManager{}
	})
	return instance
}

func (m *DBManager) Connect(cfg *models.DBConfig) error {
	m.Lock()
	defer m.Unlock()

	if m.db != nil {
		m.db.Close()
	}

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?charset=utf8mb4&parseTime=true&loc=Local",
		cfg.User, cfg.Password, cfg.Host, cfg.Port, cfg.Database)

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}

	db.SetMaxOpenConns(20)
	db.SetMaxIdleConns(10)
	db.SetConnMaxLifetime(time.Hour)

	if err := db.Ping(); err != nil {
		return fmt.Errorf("failed to ping database: %w", err)
	}

	m.db = db
	log.Printf("Connected to MySQL: %s@%s:%s/%s", cfg.User, cfg.Host, cfg.Port, cfg.Database)
	return nil
}

func (m *DBManager) ConnectDefault() error {
	return m.Connect(&models.DBConfig{
		Host:     config.AppConfig.DBHost,
		Port:     config.AppConfig.DBPort,
		User:     config.AppConfig.DBUser,
		Password: config.AppConfig.DBPassword,
		Database: config.AppConfig.DBName,
	})
}

func (m *DBManager) Close() error {
	m.Lock()
	defer m.Unlock()

	if m.db != nil {
		err := m.db.Close()
		m.db = nil
		return err
	}
	return nil
}

func (m *DBManager) GetDB() (*sql.DB, error) {
	m.RLock()
	defer m.RUnlock()

	if m.db == nil {
		return nil, fmt.Errorf("database not connected")
	}
	return m.db, nil
}

func (m *DBManager) TestConnection(cfg *models.DBConfig) error {
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?charset=utf8mb4&parseTime=true&loc=Local",
		cfg.User, cfg.Password, cfg.Host, cfg.Port, cfg.Database)

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	db.SetConnMaxLifetime(5 * time.Second)
	if err := db.Ping(); err != nil {
		return fmt.Errorf("failed to ping database: %w", err)
	}

	return nil
}

func (m *DBManager) GetTableList() ([]models.TableInfo, error) {
	db, err := m.GetDB()
	if err != nil {
		return nil, err
	}

	query := `
		SELECT 
			TABLE_NAME,
			TABLE_ROWS,
			DATA_LENGTH,
			INDEX_LENGTH,
			CREATE_TIME,
			UPDATE_TIME,
			ENGINE,
			TABLE_COLLATION,
			TABLE_COMMENT
		FROM information_schema.TABLES 
		WHERE TABLE_SCHEMA = DATABASE() 
		AND TABLE_TYPE = 'BASE TABLE'
		ORDER BY TABLE_ROWS DESC
	`

	rows, err := db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query tables: %w", err)
	}
	defer rows.Close()

	var tables []models.TableInfo
	for rows.Next() {
		var t models.TableInfo
		var createTime, updateTime sql.NullTime
		var tableRows, dataLength, indexLength sql.NullInt64

		err := rows.Scan(
			&t.TableName,
			&tableRows,
			&dataLength,
			&indexLength,
			&createTime,
			&updateTime,
			&t.Engine,
			&t.TableCollation,
			&t.Comment,
		)
		if err != nil {
			return nil, err
		}

		t.TableRows = tableRows.Int64
		t.DataSize = dataLength.Int64
		t.IndexSize = indexLength.Int64
		t.TotalSize = dataLength.Int64 + indexLength.Int64
		if createTime.Valid {
			t.CreateTime = createTime.Time
		}
		if updateTime.Valid {
			t.UpdateTime = updateTime.Time
		}

		tables = append(tables, t)
	}

	return tables, nil
}

func (m *DBManager) GetTableInfo(tableName string) (*models.TableInfo, error) {
	db, err := m.GetDB()
	if err != nil {
		return nil, err
	}

	query := `
		SELECT 
			TABLE_NAME,
			TABLE_ROWS,
			DATA_LENGTH,
			INDEX_LENGTH,
			CREATE_TIME,
			UPDATE_TIME,
			ENGINE,
			TABLE_COLLATION,
			TABLE_COMMENT
		FROM information_schema.TABLES 
		WHERE TABLE_SCHEMA = DATABASE() 
		AND TABLE_NAME = ?
	`

	var t models.TableInfo
	var createTime, updateTime sql.NullTime
	var tableRows, dataLength, indexLength sql.NullInt64

	err = db.QueryRow(query, tableName).Scan(
		&t.TableName,
		&tableRows,
		&dataLength,
		&indexLength,
		&createTime,
		&updateTime,
		&t.Engine,
		&t.TableCollation,
		&t.Comment,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get table info: %w", err)
	}

	t.TableRows = tableRows.Int64
	t.DataSize = dataLength.Int64
	t.IndexSize = indexLength.Int64
	t.TotalSize = dataLength.Int64 + indexLength.Int64
	if createTime.Valid {
		t.CreateTime = createTime.Time
	}
	if updateTime.Valid {
		t.UpdateTime = updateTime.Time
	}

	t.Columns, err = m.GetColumns(tableName)
	if err != nil {
		return nil, err
	}

	t.PrimaryKeys, err = m.GetPrimaryKeys(tableName)
	if err != nil {
		return nil, err
	}

	t.Indexes, err = m.GetIndexes(tableName)
	if err != nil {
		return nil, err
	}

	t.PartitionInfo, err = m.GetPartitionInfo(tableName)
	if err != nil {
		log.Printf("Warning: failed to get partition info: %v", err)
	}

	return &t, nil
}

func (m *DBManager) GetColumns(tableName string) ([]models.ColumnInfo, error) {
	db, err := m.GetDB()
	if err != nil {
		return nil, err
	}

	query := `
		SELECT 
			COLUMN_NAME,
			DATA_TYPE,
			COLUMN_TYPE,
			IS_NULLABLE,
			COLUMN_KEY,
			COLUMN_DEFAULT,
			EXTRA,
			COLUMN_COMMENT
		FROM information_schema.COLUMNS 
		WHERE TABLE_SCHEMA = DATABASE() 
		AND TABLE_NAME = ?
		ORDER BY ORDINAL_POSITION
	`

	rows, err := db.Query(query, tableName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var columns []models.ColumnInfo
	for rows.Next() {
		var c models.ColumnInfo
		var isNullable, columnDefault sql.NullString

		err := rows.Scan(
			&c.ColumnName,
			&c.DataType,
			&c.ColumnType,
			&isNullable,
			&c.ColumnKey,
			&columnDefault,
			&c.Extra,
			&c.Comment,
		)
		if err != nil {
			return nil, err
		}

		c.IsNullable = isNullable.String == "YES"
		c.ColumnDefault = columnDefault.String
		columns = append(columns, c)
	}

	return columns, nil
}

func (m *DBManager) GetPrimaryKeys(tableName string) ([]string, error) {
	db, err := m.GetDB()
	if err != nil {
		return nil, err
	}

	query := `
		SELECT COLUMN_NAME
		FROM information_schema.KEY_COLUMN_USAGE
		WHERE TABLE_SCHEMA = DATABASE()
		AND TABLE_NAME = ?
		AND CONSTRAINT_NAME = 'PRIMARY'
		ORDER BY ORDINAL_POSITION
	`

	rows, err := db.Query(query, tableName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var keys []string
	for rows.Next() {
		var col string
		if err := rows.Scan(&col); err != nil {
			return nil, err
		}
		keys = append(keys, col)
	}

	return keys, nil
}

func (m *DBManager) GetIndexes(tableName string) ([]models.IndexInfo, error) {
	db, err := m.GetDB()
	if err != nil {
		return nil, err
	}

	query := `
		SELECT 
			INDEX_NAME,
			NON_UNIQUE,
			SEQ_IN_INDEX,
			COLUMN_NAME,
			INDEX_TYPE,
			COMMENT
		FROM information_schema.STATISTICS
		WHERE TABLE_SCHEMA = DATABASE()
		AND TABLE_NAME = ?
		ORDER BY INDEX_NAME, SEQ_IN_INDEX
	`

	rows, err := db.Query(query, tableName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var indexes []models.IndexInfo
	for rows.Next() {
		var idx models.IndexInfo
		var nonUnique int
		err := rows.Scan(
			&idx.IndexName,
			&nonUnique,
			&idx.SeqInIndex,
			&idx.ColumnName,
			&idx.IndexType,
			&idx.Comment,
		)
		if err != nil {
			return nil, err
		}
		idx.NonUnique = nonUnique > 0
		indexes = append(indexes, idx)
	}

	return indexes, nil
}

func (m *DBManager) GetPartitionInfo(tableName string) (*models.PartitionInfo, error) {
	db, err := m.GetDB()
	if err != nil {
		return nil, err
	}

	query := `
		SELECT 
			PARTITION_NAME,
			PARTITION_ORDINAL_POSITION,
			PARTITION_METHOD,
			PARTITION_EXPRESSION,
			PARTITION_DESCRIPTION,
			TABLE_ROWS,
			DATA_LENGTH,
			INDEX_LENGTH,
			CREATE_TIME,
			UPDATE_TIME,
			PARTITION_COMMENT
		FROM information_schema.PARTITIONS
		WHERE TABLE_SCHEMA = DATABASE()
		AND TABLE_NAME = ?
		AND PARTITION_NAME IS NOT NULL
		ORDER BY PARTITION_ORDINAL_POSITION
	`

	rows, err := db.Query(query, tableName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var partitions []models.PartitionDef
	var partitionMethod, partitionExpr string

	for rows.Next() {
		var p models.PartitionDef
		var createTime, updateTime sql.NullTime
		var tableRows, dataLength, indexLength sql.NullInt64

		err := rows.Scan(
			&p.PartitionName,
			&p.PartitionOrdinal,
			&p.PartitionMethod,
			&p.PartitionExpression,
			&p.PartitionDescription,
			&tableRows,
			&dataLength,
			&indexLength,
			&createTime,
			&updateTime,
			&p.Comment,
		)
		if err != nil {
			return nil, err
		}

		p.TableRows = tableRows.Int64
		p.DataLength = dataLength.Int64
		p.IndexLength = indexLength.Int64
		if createTime.Valid {
			p.CreateTime = createTime.Time
		}
		if updateTime.Valid {
			p.UpdateTime = updateTime.Time
		}

		partitionMethod = p.PartitionMethod
		partitionExpr = p.PartitionExpression
		partitions = append(partitions, p)
	}

	if len(partitions) == 0 {
		return nil, nil
	}

	return &models.PartitionInfo{
		PartitionMethod: partitionMethod,
		PartitionExpr:   partitionExpr,
		Partitions:      partitions,
	}, nil
}

func (m *DBManager) GetColumnStats(tableName, columnName string) (minVal, maxVal interface{}, distinctCount int64, err error) {
	db, err := m.GetDB()
	if err != nil {
		return nil, nil, 0, err
	}

	query := fmt.Sprintf(`
		SELECT 
			MIN(%s),
			MAX(%s),
			COUNT(DISTINCT %s)
		FROM %s
	`, "`"+columnName+"`", "`"+columnName+"`", "`"+columnName+"`", "`"+tableName+"`")

	var min, max sql.NullString
	err = db.QueryRow(query).Scan(&min, &max, &distinctCount)
	if err != nil {
		return nil, nil, 0, err
	}

	if min.Valid {
		minVal = min.String
	}
	if max.Valid {
		maxVal = max.String
	}

	return
}

func (m *DBManager) GetRowCount(tableName string) (int64, error) {
	db, err := m.GetDB()
	if err != nil {
		return 0, err
	}

	query := fmt.Sprintf("SELECT COUNT(*) FROM `%s`", tableName)
	var count int64
	err = db.QueryRow(query).Scan(&count)
	return count, err
}

func (m *DBManager) ExecuteSQL(sql string) (sql.Result, error) {
	db, err := m.GetDB()
	if err != nil {
		return nil, err
	}
	return db.Exec(sql)
}

func (m *DBManager) ExecuteQuery(query string) ([]map[string]interface{}, error) {
	db, err := m.GetDB()
	if err != nil {
		return nil, err
	}

	rows, err := db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, err
	}

	var result []map[string]interface{}
	for rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range columns {
			valuePtrs[i] = &values[i]
		}

		if err := rows.Scan(valuePtrs...); err != nil {
			return nil, err
		}

		row := make(map[string]interface{})
		for i, col := range columns {
			val := values[i]
			if b, ok := val.([]byte); ok {
				row[col] = string(b)
			} else {
				row[col] = val
			}
		}
		result = append(result, row)
	}

	return result, nil
}
