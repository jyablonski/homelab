terraform {
  required_providers {
    authentik = {
      source  = "goauthentik/authentik"
      version = "~> 2024.10.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

# this would have to get manually created in the authentik console
# one time after you spin up the cluster & all services
provider "authentik" {
  url   = "http://localhost:30080"
  token = var.authentik_token
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}
