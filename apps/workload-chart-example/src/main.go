package main

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	randomStringsGenerated = promauto.NewCounter(prometheus.CounterOpts{
		Name: "random_string_api_strings_generated_total",
		Help: "Total random strings generated successfully.",
	})
	httpRequests = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "random_string_api_http_requests_total",
			Help: "Total HTTP requests handled by endpoint, method, and status code.",
		},
		[]string{"handler", "code", "method"},
	)
	httpRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "random_string_api_http_request_duration_seconds",
			Help:    "HTTP request duration in seconds by endpoint and method.",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"handler", "method"},
	)
)

func main() {
	mux := http.NewServeMux()
	mux.Handle("/random", instrumentHandler("random", http.HandlerFunc(randomHandler)))
	mux.Handle("/metrics", promhttp.Handler())
	mux.Handle("/health/live", instrumentHandler("health_live", http.HandlerFunc(healthHandler)))
	mux.Handle("/health/ready", instrumentHandler("health_ready", http.HandlerFunc(healthHandler)))

	port := getenv("PORT", "8080")
	addr := ":" + port

	server := &http.Server{
		Addr:              addr,
		Handler:           requestLogger(mux),
		ReadHeaderTimeout: 5 * time.Second,
	}

	log.Printf("workload-chart-example listening on %s", addr)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server exited: %v", err)
	}
}

func randomHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	value, err := randomHexString(16)
	if err != nil {
		http.Error(w, "failed to generate random string", http.StatusInternalServerError)
		log.Printf(`{"level":"error","path":"%s","error":"%v"}`, r.URL.Path, err)
		return
	}

	randomStringsGenerated.Inc()

	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	fmt.Fprintln(w, value)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	fmt.Fprintln(w, "ok")
}

func requestLogger(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf(
			`{"level":"info","method":"%s","path":"%s","remote_addr":"%s","user_agent":"%s"}`,
			r.Method,
			r.URL.Path,
			r.RemoteAddr,
			r.UserAgent(),
		)
		next.ServeHTTP(w, r)
	})
}

func instrumentHandler(name string, handler http.Handler) http.Handler {
	return promhttp.InstrumentHandlerDuration(
		httpRequestDuration.MustCurryWith(prometheus.Labels{"handler": name}),
		promhttp.InstrumentHandlerCounter(
			httpRequests.MustCurryWith(prometheus.Labels{"handler": name}),
			handler,
		),
	)
}

func randomHexString(byteLength int) (string, error) {
	buf := make([]byte, byteLength)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}

	return hex.EncodeToString(buf), nil
}

func getenv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}

	return fallback
}
