variable "region" {
  description = "Aliyun region"
  type        = string
}

variable "instance_type" {
  description = "ECS instance type"
  type        = string
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
  default     = ""
}

provider "alicloud" {
  region = var.region
}

data "alicloud_images" "default" {
  name_regex  = "^ubuntu_22_04_x64"
  most_recent = true
  owners      = "system"
}

resource "alicloud_vpc" "main" {
  vpc_name   = "autoscaler-vpc"
  cidr_block = "10.0.0.0/16"
}

resource "alicloud_vswitch" "public" {
  vsw_name   = "autoscaler-vswitch"
  vpc_id     = alicloud_vpc.main.id
  cidr_block = "10.0.1.0/24"
  zone_id    = "${var.region}-a"
}

resource "alicloud_security_group" "autoscaler" {
  name   = "autoscaler-sg"
  vpc_id = alicloud_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_ip     = "0.0.0.0/0"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_ip     = "0.0.0.0/0"
  }

  ingress {
    from_port   = 9100
    to_port     = 9100
    protocol    = "tcp"
    cidr_ip     = "0.0.0.0/0"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_ip     = "0.0.0.0/0"
  }
}

resource "alicloud_ess_scaling_group" "autoscaler" {
  min_size           = var.min_instances
  max_size           = var.max_instances
  scaling_group_name = "autoscaler-scaling-group"
  vswitch_ids        = [alicloud_vswitch.public.id]
}

resource "alicloud_ess_scaling_configuration" "autoscaler" {
  scaling_group_id  = alicloud_ess_scaling_group.autoscaler.id
  image_id          = data.alicloud_images.default.images[0].id
  instance_type     = var.instance_type
  security_group_id = alicloud_security_group.autoscaler.id
  force_delete      = true

  user_data = <<-EOF
              #!/bin/bash
              apt-get update -y
              apt-get install -y prometheus-node-exporter
              systemctl enable prometheus-node-exporter
              systemctl start prometheus-node-exporter
              EOF
}

resource "alicloud_ess_scaling_rule" "autoscaler" {
  scaling_group_id = alicloud_ess_scaling_group.autoscaler.id
  rule_type        = "SimpleScalingRule"
  adjustment_type  = "ChangeInCapacity"
  adjustment_value = 1
}

output "vpc_id" {
  value = alicloud_vpc.main.id
}

output "vswitch_id" {
  value = alicloud_vswitch.public.id
}

output "security_group_id" {
  value = alicloud_security_group.autoscaler.id
}

output "scaling_group_id" {
  value = alicloud_ess_scaling_group.autoscaler.id
}

output "image_id" {
  value = data.alicloud_images.default.images[0].id
}
