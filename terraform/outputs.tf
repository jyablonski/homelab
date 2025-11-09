output "grafana_client_id" {
  value = authentik_provider_oauth2.grafana.client_id
}

output "grafana_client_secret" {
  value     = authentik_provider_oauth2.grafana.client_secret
  sensitive = true
}

output "headlamp_client_id" {
  value = authentik_provider_oauth2.headlamp.client_id
}

output "headlamp_client_secret" {
  value     = authentik_provider_oauth2.headlamp.client_secret
  sensitive = true
}
