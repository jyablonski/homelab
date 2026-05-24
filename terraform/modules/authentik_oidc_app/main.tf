resource "random_password" "client_secret" {
  length  = var.client_secret_length
  special = false
}

resource "random_password" "extra_secret" {
  for_each = var.generated_secret_keys

  length  = each.value
  special = false
}

locals {
  name                   = title(replace(var.app_id, "-", " "))
  slug                   = var.app_id
  client_id              = var.app_id
  kubernetes_secret_name = "${var.app_id}-oauth-secret"
  split_oidc_urls = var.include_split_oidc_urls ? {
    # Issuer must match the `iss` claim on tokens from the in-cluster token endpoint.
    OIDC_ISSUER_URL    = "${var.internal_oauth_base}/${var.app_id}/"
    OIDC_AUTHORIZE_URL = "${var.public_oauth_base}/authorize/"
    OIDC_TOKEN_URL     = "${var.internal_oauth_base}/token/"
    OIDC_USERINFO_URL  = "${var.internal_oauth_base}/userinfo/"
    OIDC_JWKS_URL      = "${var.internal_oauth_base}/${var.app_id}/jwks/"
  } : {}
}

resource "authentik_provider_oauth2" "this" {
  name               = local.name
  client_id          = local.client_id
  client_secret      = random_password.client_secret.result
  authorization_flow = var.authorization_flow_id
  invalidation_flow  = var.invalidation_flow_id
  signing_key        = var.signing_key_id

  allowed_redirect_uris = [
    for uri in var.allowed_redirect_uris : {
      matching_mode = uri.matching_mode
      url           = uri.url
    }
  ]

  property_mappings = var.property_mapping_ids
}

resource "authentik_application" "this" {
  name              = local.name
  slug              = local.slug
  protocol_provider = authentik_provider_oauth2.this.id
  meta_launch_url   = var.meta_launch_url != "" ? var.meta_launch_url : null
}

resource "kubernetes_secret_v1" "this" {
  metadata {
    name      = local.kubernetes_secret_name
    namespace = var.kubernetes_secret_namespace
  }

  data = merge(
    {
      (var.client_id_secret_key)     = authentik_provider_oauth2.this.client_id
      (var.client_secret_secret_key) = authentik_provider_oauth2.this.client_secret
    },
    local.split_oidc_urls,
    var.secret_data,
    {
      for key, password in random_password.extra_secret : key => password.result
    },
  )

  type = "Opaque"
}
