terraform {
  required_providers {
    authentik = {
      source  = "goauthentik/authentik"
      version = ">= 2026.2.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 3.1.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.9.0"
    }
  }
}

# this would have to get manually created in the authentik console
# one time after you spin up the cluster & all services
provider "authentik" {
  url   = "http://authentik.home"
  token = var.authentik_token
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}
