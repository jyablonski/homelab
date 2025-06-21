# Dockerfile
FROM golang:1.23 AS builder

WORKDIR /app
COPY . .

RUN go build -o app main.go

FROM debian:bookworm-slim
COPY --from=builder /app/app /app/app

ENTRYPOINT ["/app/app"]
