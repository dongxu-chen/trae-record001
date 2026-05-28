package tracing

import (
	"context"
	"log"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/jaeger"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	tracesdk "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
	"go.opentelemetry.io/otel/trace"
)

type JaegerTracer struct {
	provider *tracesdk.TracerProvider
	tracer   trace.Tracer
}

func NewJaegerTracer(serviceName, jaegerEndpoint string) (*JaegerTracer, error) {
	exp, err := jaeger.New(jaeger.WithCollectorEndpoint(jaeger.WithEndpoint(jaegerEndpoint)))
	if err != nil {
		return nil, err
	}

	tp := tracesdk.NewTracerProvider(
		tracesdk.WithBatcher(exp),
		tracesdk.WithResource(resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceNameKey.String(serviceName),
			attribute.String("service.type", "traffic-mirror-control-plane"),
		)),
	)

	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	return &JaegerTracer{
		provider: tp,
		tracer:   tp.Tracer(serviceName),
	}, nil
}

func (j *JaegerTracer) Shutdown(ctx context.Context) error {
	log.Println("shutting down Jaeger tracer provider")
	return j.provider.Shutdown(ctx)
}

func (j *JaegerTracer) Tracer() trace.Tracer {
	return j.tracer
}

func (j *JaegerTracer) StartSpan(ctx context.Context, name string, attrs ...attribute.KeyValue) (context.Context, trace.Span) {
	return j.tracer.Start(ctx, name, trace.WithAttributes(attrs...))
}

func (j *JaegerTracer) RecordComparison(ctx context.Context, result map[string]interface{}) {
	_, span := j.tracer.Start(ctx, "comparison_recorded")
	defer span.End()

	for k, v := range result {
		switch val := v.(type) {
		case string:
			span.SetAttributes(attribute.String(k, val))
		case int:
			span.SetAttributes(attribute.Int(k, val))
		case bool:
			span.SetAttributes(attribute.Bool(k, val))
		case float64:
			span.SetAttributes(attribute.Float64(k, val))
		}
	}
}
