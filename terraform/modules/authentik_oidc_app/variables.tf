variable "app_id" {
  description = "Canonical app identifier used for Authentik slug, OAuth2 client ID, and Kubernetes Secret name."
  type        = string
}

variable "client_secret_length" {
  description = "Generated OAuth2 client secret length."
  type        = number
  default     = 32
}

variable "authorization_flow_id" {
  description = "Authentik authorization flow ID."
  type        = string
}

variable "invalidation_flow_id" {
  description = "Authentik invalidation flow ID."
  type        = string
}

variable "signing_key_id" {
  description = "Authentik signing key ID."
  type        = string
}

variable "allowed_redirect_uris" {
  description = "Allowed OAuth2 redirect URIs."
  type = list(object({
    matching_mode = string
    url           = string
  }))
}

variable "property_mapping_ids" {
  description = "Authentik scope/property mapping IDs."
  type        = list(string)
}

variable "kubernetes_secret_namespace" {
  description = "Kubernetes Secret namespace for generated client configuration."
  type        = string
}

variable "client_id_secret_key" {
  description = "Kubernetes Secret data key for the OAuth2 client ID."
  type        = string
  default     = "OIDC_CLIENT_ID"
}

variable "client_secret_secret_key" {
  description = "Kubernetes Secret data key for the OAuth2 client secret."
  type        = string
  default     = "OIDC_CLIENT_SECRET"
}

variable "secret_data" {
  description = "Additional static Kubernetes Secret data."
  type        = map(string)
  default     = {}
}

variable "public_oauth_base" {
  description = "Browser-facing Authentik OAuth base URL (Traefik / Pi-hole)."
  type        = string
  default     = "http://authentik.home/application/o"
}

variable "internal_oauth_base" {
  description = "In-cluster Authentik OAuth base URL for server-side token and userinfo calls."
  type        = string
  default     = "http://authentik-server.authentik.svc.cluster.local/application/o"
}

variable "include_split_oidc_urls" {
  description = "When true, add OIDC_ISSUER_URL, OIDC_AUTHORIZE_URL, OIDC_TOKEN_URL, and OIDC_USERINFO_URL to the Kubernetes Secret."
  type        = bool
  default     = true
}

variable "generated_secret_keys" {
  description = "Additional generated Kubernetes Secret keys mapped to password lengths."
  type        = map(number)
  default     = {}
}

variable "meta_launch_url" {
  description = "Authentik user portal link for this application (meta_launch_url)."
  type        = string
  default     = ""
}
