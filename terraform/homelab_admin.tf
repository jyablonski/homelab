resource "authentik_user" "homelab_admin" {
  username = var.homelab_admin_username
  name     = var.homelab_admin_name
  email    = var.homelab_admin_email
  password = var.homelab_admin_password
  type     = "internal"

  groups = [authentik_group.homelab_admins.id]

  lifecycle {
    ignore_changes = [password]
  }
}
