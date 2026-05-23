variable "region" {
  description = "Tencent Cloud region"
  type        = string
}

variable "instance_type" {
  description = "CVM instance type"
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

provider "tencentcloud" {
  region = var.region
}

data "tencentcloud_images" "default" {
  image_type = ["PUBLIC_IMAGE"]
  os_name    = "ubuntu"
}

resource "tencentcloud_vpc" "main" {
  name       = "autoscaler-vpc"
  cidr_block = "10.0.0.0/16"
}

resource "tencentcloud_subnet" "public" {
  name              = "autoscaler-subnet"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.region}-1"
  is_multicast      = false
}

resource "tencentcloud_security_group" "autoscaler" {
  name        = "autoscaler-sg"
  description = "Allow traffic for autoscaler instances"
}

resource "tencentcloud_security_group_rule" "ssh_in" {
  security_group_id = tencentcloud_security_group.autoscaler.id
  type              = "ingress"
  cidr_ip           = "0.0.0.0/0"
  ip_protocol       = "tcp"
  port_range        = "22"
  policy            = "ACCEPT"
}

resource "tencentcloud_security_group_rule" "http_in" {
  security_group_id = tencentcloud_security_group.autoscaler.id
  type              = "ingress"
  cidr_ip           = "0.0.0.0/0"
  ip_protocol       = "tcp"
  port_range        = "80"
  policy            = "ACCEPT"
}

resource "tencentcloud_security_group_rule" "node_exporter_in" {
  security_group_id = tencentcloud_security_group.autoscaler.id
  type              = "ingress"
  cidr_ip           = "0.0.0.0/0"
  ip_protocol       = "tcp"
  port_range        = "9100"
  policy            = "ACCEPT"
}

resource "tencentcloud_security_group_rule" "all_out" {
  security_group_id = tencentcloud_security_group.autoscaler.id
  type              = "egress"
  cidr_ip           = "0.0.0.0/0"
  ip_protocol       = "all"
  policy            = "ACCEPT"
}

resource "tencentcloud_as_scaling_group" "autoscaler" {
  scaling_group_name = "autoscaler-scaling-group"
  configuration_id   = tencentcloud_as_launch_configuration.autoscaler.id
  max_size           = var.max_instances
  min_size           = var.min_instances
  vpc_id             = tencentcloud_vpc.main.id
  subnet_ids         = [tencentcloud_subnet.public.id]
}

resource "tencentcloud_as_launch_configuration" "autoscaler" {
  launch_configuration_name = "autoscaler-launch-config"
  image_id                  = data.tencentcloud_images.default.images[0].image_id
  instance_type             = var.instance_type
  security_group_ids        = [tencentcloud_security_group.autoscaler.id]

  user_data = base64encode(<<-EOF
              #!/bin/bash
              apt-get update -y
              apt-get install -y prometheus-node-exporter
              systemctl enable prometheus-node-exporter
              systemctl start prometheus-node-exporter
              EOF
              )
}

output "vpc_id" {
  value = tencentcloud_vpc.main.id
}

output "subnet_id" {
  value = tencentcloud_subnet.public.id
}

output "security_group_id" {
  value = tencentcloud_security_group.autoscaler.id
}

output "scaling_group_id" {
  value = tencentcloud_as_scaling_group.autoscaler.id
}

output "image_id" {
  value = data.tencentcloud_images.default.images[0].image_id
}
