terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    alicloud = {
      source  = "aliyun/alicloud"
      version = ">= 1.0"
    }
    tencentcloud = {
      source  = "tencentcloudstack/tencentcloud"
      version = ">= 1.0"
    }
  }
}

variable "cloud_provider" {
  description = "Cloud provider: aws, aliyun, tencent, or hybrid"
  type        = string
  default     = "aws"
}

variable "region" {
  description = "Cloud region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "Instance type"
  type        = string
  default     = "t2.micro"
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
  default     = ""
}

locals {
  use_aws       = var.cloud_provider == "aws" || var.cloud_provider == "hybrid"
  use_aliyun    = var.cloud_provider == "aliyun" || var.cloud_provider == "hybrid"
  use_tencent   = var.cloud_provider == "tencent" || var.cloud_provider == "hybrid"
}

module "aws_infrastructure" {
  count  = local.use_aws ? 1 : 0
  source = "./modules/aws"

  region         = var.region
  instance_type  = var.instance_type
  min_instances  = var.min_instances
  max_instances  = var.max_instances
  key_name       = var.key_name
}

module "aliyun_infrastructure" {
  count  = local.use_aliyun ? 1 : 0
  source = "./modules/aliyun"

  region         = var.region
  instance_type  = var.instance_type
  min_instances  = var.min_instances
  max_instances  = var.max_instances
  key_name       = var.key_name
}

module "tencent_infrastructure" {
  count  = local.use_tencent ? 1 : 0
  source = "./modules/tencent"

  region         = var.region
  instance_type  = var.instance_type
  min_instances  = var.min_instances
  max_instances  = var.max_instances
  key_name       = var.key_name
}

module "prometheus" {
  source = "./modules/prometheus"

  region    = var.region
  providers = var.cloud_provider
}
