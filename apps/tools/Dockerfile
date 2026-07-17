FROM golang:1.26.5 AS builder

WORKDIR /src
COPY go.mod ./
COPY . ./

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/homelab-backup ./cmd/homelab-backup

FROM debian:bookworm-slim
COPY --from=builder /out/homelab-backup /usr/local/bin/homelab-backup

ENTRYPOINT ["/usr/local/bin/homelab-backup"]
