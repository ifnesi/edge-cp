terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "rg" {
  name     = "confluent-aks-rg-new"
  location = "West US"

  tags = {
    owner_email = "your_email_address@example.com"
  }
}


# AKS Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "confluent-aks"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "confluentaks"

  default_node_pool {
    name       = "agentpool"
    node_count = 3                 # Adjust as needed
    vm_size    = "Standard_D8_v3"  # 8 vCPUs, 32GB RAM
  }

  identity {
    type = "SystemAssigned"
  }

  kubernetes_version = "1.30.9" # Change this based on az aks get-versions output

  tags = {
    environment = "dev"
  }
}

# Output the AKS kubeconfig
output "kube_config" {
  value     = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive = true
}
