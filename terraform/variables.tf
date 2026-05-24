variable "authentik_token" {
  description = "API token for the Authentik provider"
  type        = string
  sensitive   = true
}

variable "homelab_admin_username" {
  description = "Primary homelab Authentik admin username (Terraform-managed internal user)"
  type        = string
  default     = "jyablonski"
}

variable "homelab_admin_name" {
  description = "Display name for the Terraform-managed homelab admin user"
  type        = string
  default     = "jacob"
}

variable "homelab_admin_email" {
  description = "Email for the Terraform-managed homelab admin user"
  type        = string
  default     = "jyablonski9@gmail.com"
}

variable "homelab_admin_password" {
  description = "Password for the Terraform-managed homelab admin user (set via SOPS in apply-authentik-terraform.sh)"
  type        = string
  sensitive   = true
}
