package driver

import (
	"context"
	"db-bench/internal/config"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/mongo/readpref"
)

type MongoDBDriver struct {
	BaseDriver
	client     *mongo.Client
	collection *mongo.Collection
}

func NewMongoDBDriver(cfg config.DatabaseConfig) *MongoDBDriver {
	return &MongoDBDriver{
		BaseDriver: BaseDriver{cfg: cfg},
	}
}

func (d *MongoDBDriver) Connect(ctx context.Context) error {
	uri := fmt.Sprintf("mongodb://%s:%s@%s:%d/%s?authSource=admin&maxPoolSize=%d",
		d.cfg.User, d.cfg.Password, d.cfg.Host, d.cfg.Port, d.cfg.Database, d.cfg.MaxConnections)

	clientOpts := options.Client().
		ApplyURI(uri).
		SetConnectTimeout(d.cfg.Timeout).
		SetMaxPoolSize(uint64(d.cfg.MaxConnections))

	client, err := mongo.Connect(ctx, clientOpts)
	if err != nil {
		return fmt.Errorf("failed to connect to mongodb: %w", err)
	}

	if err := client.Ping(ctx, readpref.Primary()); err != nil {
		client.Disconnect(ctx)
		return fmt.Errorf("failed to ping mongodb: %w", err)
	}

	d.client = client
	d.collection = client.Database(d.cfg.Database).Collection("benchmark")
	return nil
}

func (d *MongoDBDriver) Close(ctx context.Context) error {
	if d.client != nil {
		return d.client.Disconnect(ctx)
	}
	return nil
}

type MongoDocument struct {
	ID        int       `bson:"_id"`
	Value     string    `bson:"value"`
	CreatedAt time.Time `bson:"created_at"`
	UpdatedAt time.Time `bson:"updated_at"`
}

func (d *MongoDBDriver) InitSchema(ctx context.Context, totalRecords int) error {
	if err := d.collection.Drop(ctx); err != nil {
		return fmt.Errorf("failed to drop collection: %w", err)
	}

	indexModel := mongo.IndexModel{
		Keys: bson.D{{Key: "value", Value: 1}},
	}
	if _, err := d.collection.Indexes().CreateOne(ctx, indexModel); err != nil {
		return fmt.Errorf("failed to create index: %w", err)
	}

	docs := make([]interface{}, 0, 1000)
	for i := 0; i < totalRecords; i++ {
		docs = append(docs, MongoDocument{
			ID:        i,
			Value:     d.GenerateValue(),
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
		})

		if len(docs) >= 1000 {
			if _, err := d.collection.InsertMany(ctx, docs); err != nil {
				return fmt.Errorf("failed to insert batch at %d: %w", i, err)
			}
			docs = docs[:0]
		}
	}

	if len(docs) > 0 {
		if _, err := d.collection.InsertMany(ctx, docs); err != nil {
			return fmt.Errorf("failed to insert final batch: %w", err)
		}
	}

	return nil
}

func (d *MongoDBDriver) Read(ctx context.Context, key int) Result {
	start := time.Now()
	var result MongoDocument
	filter := bson.M{"_id": key}
	err := d.collection.FindOne(ctx, filter).Decode(&result)
	duration := float64(time.Since(start).Microseconds()) / 1000.0

	return Result{
		DurationMs: duration,
		Success:    err == nil,
		Error:      err,
		OpType:     OpRead,
	}
}

func (d *MongoDBDriver) Write(ctx context.Context, key int, value string) Result {
	start := time.Now()
	filter := bson.M{"_id": key}
	update := bson.M{
		"$set": bson.M{
			"value":      value,
			"updated_at": time.Now(),
		},
		"$setOnInsert": bson.M{
			"created_at": time.Now(),
		},
	}
	opts := options.Update().SetUpsert(true)
	_, err := d.collection.UpdateOne(ctx, filter, update, opts)
	duration := float64(time.Since(start).Microseconds()) / 1000.0

	return Result{
		DurationMs: duration,
		Success:    err == nil,
		Error:      err,
		OpType:     OpWrite,
	}
}

func (d *MongoDBDriver) HealthCheck(ctx context.Context) error {
	if d.client == nil {
		return fmt.Errorf("not connected")
	}
	return d.client.Ping(ctx, readpref.Primary())
}
