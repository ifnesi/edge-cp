# AKS cluster for the Edge-CP demo.
#   HA   : 3 nodes (1 KRaft + 1 broker per node via oneReplicaPerNode; SR/C3 spread across them)
#   slim : 1 node  (combined broker/KRaft + SR + C3)
#
#   terraform init
#   terraform apply -var="subscription_id=<id>" -var="variant=ha" -var="owner_email=<you@example.com>"
#   az aks get-credentials --resource-group <resource_group> --name <cluster_name>

terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

variable "subscription_id" {
  type        = string
  description = "Azure subscription ID (az account show --query id -o tsv)"
}

variable "variant" {
  type        = string
  default     = "ha"
  description = "Demo variant: ha (3 nodes) or slim (1 node)"
  validation {
    condition     = contains(["ha", "slim"], var.variant)
    error_message = "variant must be ha or slim."
  }
}

variable "location" {
  type    = string
  default = "uksouth"
}

variable "resource_group" {
  type    = string
  default = "edge-cp-poc"
}

variable "cluster_name" {
  type    = string
  default = "edge-cp"
}

variable "owner_email" {
  type        = string
  description = "Tag: owner of the resources"
}

variable "vm_size" {
  type        = string
  default     = "Standard_D4s_v5" # 4 vCPU / 16 GiB per node
  description = "Node size. D4s_v5 fits both variants; use Standard_D8s_v5 for heavier perf tests."
}

variable "kubernetes_version" {
  type    = string
  default = null # AKS default; must be within CFK 3.4 support (1.29 - 1.37): az aks get-versions -l <location>
}

locals {
  node_count = var.variant == "ha" ? 3 : 1
  tags = {
    owner_email = var.owner_email
    demo        = "edge-cp-${var.variant}"
  }
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group
  location = var.location
  tags     = local.tags
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = var.cluster_name
  kubernetes_version  = var.kubernetes_version

  default_node_pool {
    name            = "cp"
    node_count      = local.node_count
    vm_size         = var.vm_size
    os_disk_size_gb = 128
    # Spread nodes across zones where the region supports it (HA)
    zones = var.variant == "ha" ? ["1", "2", "3"] : null
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

output "get_credentials" {
  value = "az aks get-credentials --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_kubernetes_cluster.aks.name}"
}

output "kube_config" {
  value     = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive = true
}
