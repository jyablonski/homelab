output "application_id" {
  value = authentik_application.this.id
}

output "provider_id" {
  value = authentik_provider_oauth2.this.id
}

output "client_id" {
  value = authentik_provider_oauth2.this.client_id
}

output "client_secret" {
  value     = authentik_provider_oauth2.this.client_secret
  sensitive = true
}

output "kubernetes_secret_name" {
  value = kubernetes_secret_v1.this.metadata[0].name
}
