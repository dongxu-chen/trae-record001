package tracing

import (
	"context"
	"fmt"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/jaeger"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
	"go.opentelemetry.io/otel/trace"

	"github.com/coldstart-optimizer/coldstart/internal/model"
)

type JaegerExporter struct {
	provider *sdktrace.TracerProvider
	tracer   trace.Tracer
	endpoint string
}

func NewJaegerExporter(endpoint, serviceName string) (*JaegerExporter, error) {
	exp, err := jaeger.New(jaeger.WithCollectorEndpoint(jaeger.WithEndpoint(endpoint)))
	if err != nil {
		return nil, fmt.Errorf("jaeger exporter: %w", err)
	}
	r, err := resource.Merge(
		resource.Default(),
		resource.NewSchemaless(
			semconv.ServiceName(serviceName),
			attribute.String("coldstart.source", "optimizer"),
		),
	)
	if err != nil {
		return nil, err
	}
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp),
		sdktrace.WithResource(r),
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	)
	otel.SetTracerProvider(tp)
	return &JaegerExporter{
		provider: tp,
		tracer:   tp.Tracer("coldstart-analyzer"),
		endpoint: endpoint,
	}, nil
}

func (j *JaegerExporter) Shutdown(ctx context.Context) error {
	if j.provider == nil {
		return nil
	}
	return j.provider.Shutdown(ctx)
}

func (j *JaegerExporter) Export(ctx context.Context, profile model.ColdStartProfile) (trace.Span, error) {
	rootCtx, rootSpan := j.tracer.Start(ctx, "coldstart",
		trace.WithAttributes(
			attribute.String("function", profile.Function),
			attribute.String("runtime", profile.Runtime),
			attribute.String("container.id", profile.ContainerID),
			attribute.Int64("total_ms", profile.Total.Milliseconds()),
		),
	)
	defer rootSpan.End()

	for _, rec := range profile.Phases {
		_, span := j.tracer.Start(rootCtx, string(rec.Phase),
			trace.WithAttributes(
				attribute.Int64("duration_ms", rec.Duration.Milliseconds()),
				attribute.String("source", rec.Source),
				attribute.String("detail", rec.Detail),
			),
		)
		span.End()
	}
	return rootSpan, nil
}

func (j *JaegerExporter) LiveSpan(ctx context.Context, function, containerID string, phase model.Phase, dur time.Duration, attrs map[string]string) {
	opts := []trace.SpanStartOption{
		trace.WithAttributes(
			attribute.String("function", function),
			attribute.String("container.id", containerID),
			attribute.Int64("duration_ms", dur.Milliseconds()),
		),
	}
	for k, v := range attrs {
		opts = append(opts, trace.WithAttributes(attribute.String(k, v)))
	}
	_, span := j.tracer.Start(ctx, string(phase), opts...)
	span.End()
}
