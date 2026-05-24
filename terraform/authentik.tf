# Get default authorization flow
data "authentik_flow" "default_authorization_flow" {
  slug = "default-provider-authorization-implicit-consent"
}

# Get default invalidation flow
data "authentik_flow" "default_invalidation_flow" {
  slug = "default-provider-invalidation-flow"
}

data "authentik_certificate_key_pair" "default" {
  name = "authentik Self-signed Certificate"
}

resource "authentik_group" "homelab_admins" {
  name         = "homelab-admins"
  is_superuser = true
}

resource "authentik_property_mapping_provider_scope" "groups" {
  name       = "homelab-oidc-groups"
  scope_name = "groups"
  expression = <<-EOT
return {
    "groups": list(request.user.ak_groups.values_list("name", flat=True)),
}
EOT
}

locals {
  oidc_property_mapping_ids = [
    data.authentik_property_mapping_provider_scope.openid.id,
    data.authentik_property_mapping_provider_scope.email.id,
    data.authentik_property_mapping_provider_scope.profile.id,
  ]

  admin_oidc_property_mapping_ids = concat(local.oidc_property_mapping_ids, [
    authentik_property_mapping_provider_scope.groups.id,
  ])
}

# Get default scope mappings
data "authentik_property_mapping_provider_scope" "openid" {
  scope_name = "openid"
}

data "authentik_property_mapping_provider_scope" "email" {
  scope_name = "email"
}

data "authentik_property_mapping_provider_scope" "profile" {
  scope_name = "profile"
}

module "grafana_oidc" {
  source = "./modules/authentik_oidc_app"

  app_id                      = "grafana"
  authorization_flow_id       = data.authentik_flow.default_authorization_flow.id
  invalidation_flow_id        = data.authentik_flow.default_invalidation_flow.id
  signing_key_id              = data.authentik_certificate_key_pair.default.id
  property_mapping_ids        = local.oidc_property_mapping_ids
  kubernetes_secret_namespace = "monitoring"
  client_id_secret_key        = "client_id"
  client_secret_secret_key    = "client_secret"
  include_split_oidc_urls     = false

  allowed_redirect_uris = [
    { matching_mode = "strict", url = "http://grafana.home/login/generic_oauth" }
  ]
}

module "django_oidc" {
  source = "./modules/authentik_oidc_app"

  app_id                      = "django"
  meta_launch_url             = "http://apps.home/django/admin/"
  authorization_flow_id       = data.authentik_flow.default_authorization_flow.id
  invalidation_flow_id        = data.authentik_flow.default_invalidation_flow.id
  signing_key_id              = data.authentik_certificate_key_pair.default.id
  property_mapping_ids        = local.admin_oidc_property_mapping_ids
  kubernetes_secret_namespace = "apps"

  allowed_redirect_uris = [
    { matching_mode = "strict", url = "http://apps.home/django/sso/callback/" }
  ]

  secret_data = {
    OIDC_SCOPES       = "openid email profile groups"
    OIDC_CALLBACK_URL = "http://apps.home/django/sso/callback/"
  }
}

module "runner_oidc" {
  source = "./modules/authentik_oidc_app"

  app_id                      = "runner"
  meta_launch_url             = "http://apps.home/runner/"
  authorization_flow_id       = data.authentik_flow.default_authorization_flow.id
  invalidation_flow_id        = data.authentik_flow.default_invalidation_flow.id
  signing_key_id              = data.authentik_certificate_key_pair.default.id
  property_mapping_ids        = local.admin_oidc_property_mapping_ids
  kubernetes_secret_namespace = "apps"

  allowed_redirect_uris = [
    { matching_mode = "strict", url = "http://apps.home/runner/auth/callback" }
  ]

  secret_data = {
    OIDC_SCOPES       = "openid email profile groups"
    OIDC_CALLBACK_URL = "http://apps.home/runner/auth/callback"
  }

  generated_secret_keys = {
    SESSION_SECRET_KEY = 64
  }
}
