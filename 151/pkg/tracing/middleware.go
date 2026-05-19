package tracing

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func TracingMiddleware(serviceName string) gin.HandlerFunc {
	return func(c *gin.Context) {
		ctx := c.Request.Context()
		c.Request = c.Request.WithContext(ctx)
		c.Next()
	}
}

func TraceContextPropagationMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		ctx := c.Request.Context()
		c.Request = c.Request.WithContext(ctx)
		c.Next()
	}
}

func GetTraceHeadersMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		traceID := GetTraceID(c.Request.Context())
		if traceID != "" {
			c.Header("X-Trace-ID", traceID)
			headers := GetTraceContextHeaders(c.Request.Context())
			for k, v := range headers {
				c.Header(k, v)
			}
		}
		c.Next()
	}
}

func ResponseLoggerMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Content-Type", "application/json")
		c.Next()

		if len(c.Errors) > 0 {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error":    c.Errors.Last().Error(),
				"trace_id": GetTraceID(c.Request.Context()),
			})
		}
	}
}
