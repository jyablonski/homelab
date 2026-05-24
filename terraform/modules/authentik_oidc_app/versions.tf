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
