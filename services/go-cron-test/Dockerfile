FROM golang:1.25 AS builder

WORKDIR /app
COPY . .

RUN go build -o app main.go

FROM debian:bookworm-slim
COPY --from=builder /app/app /app/app

ENTRYPOINT ["/app/app"]
