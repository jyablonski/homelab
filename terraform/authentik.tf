# Generate random secrets for OAuth clients
resource "random_password" "grafana_secret" {
  length  = 32
  special = false
}

resource "random_password" "headlamp_secret" {
  length  = 32
  special = false
}

# Get default authorization flow
data "authentik_flow" "default_authorization_flow" {
  slug = "default-provider-authorization-implicit-consent"
}

# Create OAuth2 Provider for Grafana
resource "authentik_provider_oauth2" "grafana" {
  name               = "Grafana"
  client_id          = "grafana"
  client_secret      = random_password.grafana_secret.result
  authorization_flow = data.authentik_flow.default_authorization_flow.id

  redirect_uris = [
    "http://localhost:3000/login/generic_oauth"
  ]

  property_mappings = [
    data.authentik_scope_mapping.openid.id,
    data.authentik_scope_mapping.email.id,
    data.authentik_scope_mapping.profile.id,
  ]
}

# Create Grafana Application
resource "authentik_application" "grafana" {
  name              = "Grafana"
  slug              = "grafana"
  protocol_provider = authentik_provider_oauth2.grafana.id
}

# Create OAuth2 Provider for Headlamp
resource "authentik_provider_oauth2" "headlamp" {
  name               = "Headlamp"
  client_id          = "headlamp"
  client_secret      = random_password.headlamp_secret.result
  authorization_flow = data.authentik_flow.default_authorization_flow.id

  redirect_uris = [
    "http://localhost:4466/oidc-callback"
  ]

  property_mappings = [
    data.authentik_scope_mapping.openid.id,
    data.authentik_scope_mapping.email.id,
    data.authentik_scope_mapping.profile.id,
  ]
}

# Create Headlamp Application
resource "authentik_application" "headlamp" {
  name              = "Headlamp"
  slug              = "headlamp"
  protocol_provider = authentik_provider_oauth2.headlamp.id
}

# Get default scope mappings
data "authentik_scope_mapping" "openid" {
  scope_name = "openid"
}

data "authentik_scope_mapping" "email" {
  scope_name = "email"
}

data "authentik_scope_mapping" "profile" {
  scope_name = "profile"
}

# Store credentials in Kubernetes secrets
resource "kubernetes_secret" "grafana_oauth" {
  metadata {
    name      = "grafana-oauth-secret"
    namespace = "monitoring"
  }

  data = {
    client_id     = authentik_provider_oauth2.grafana.client_id
    client_secret = authentik_provider_oauth2.grafana.client_secret
  }

  type = "Opaque"
}

resource "kubernetes_secret" "headlamp_oauth" {
  metadata {
    name      = "headlamp-oauth-secret"
    namespace = "kube-system"
  }

  data = {
    client_id     = authentik_provider_oauth2.headlamp.client_id
    client_secret = authentik_provider_oauth2.headlamp.client_secret
  }

  type = "Opaque"
}
