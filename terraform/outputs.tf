output "grafana_client_id" {
  value = module.grafana_oidc.client_id
}

output "grafana_client_secret" {
  value     = module.grafana_oidc.client_secret
  sensitive = true
}

output "django_client_id" {
  value = module.django_oidc.client_id
}

output "django_client_secret" {
  value     = module.django_oidc.client_secret
  sensitive = true
}

output "runner_client_id" {
  value = module.runner_oidc.client_id
}

output "runner_client_secret" {
  value     = module.runner_oidc.client_secret
  sensitive = true
}
