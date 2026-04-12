FROM golang:1.25 AS builder

WORKDIR /app
COPY . .

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o workload-chart-example ./src/main.go

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/workload-chart-example /app/workload-chart-example

EXPOSE 8080

ENTRYPOINT ["/app/workload-chart-example"]
