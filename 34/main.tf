terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "terraform-state-unique-suffix-001"
    key            = "env:/${terraform.workspace}/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock-unique-suffix-001"
    encrypt        = true
    versioning     = true
    workspace_key_prefix = "env"
  }
}

data "http" "my_public_ip" {
  url = "https://ifconfig.me/ip"
}

locals {
  environment = terraform.workspace
  env_config  = var.env_configs[local.environment]

  vpc_cidr       = local.env_config.vpc_cidr
  instance_type  = local.env_config.instance_type
  min_instances  = local.env_config.min_instances
  max_instances  = local.env_config.max_instances
  desired_instances = local.env_config.desired_instances
  scale_in_cpu   = local.env_config.scale_in_cpu
  scale_out_cpu  = local.env_config.scale_out_cpu

  my_public_ip_cidr = "${chomp(data.http.my_public_ip.response_body)}/32"
  common_tags = {
    Environment = local.environment
    Project     = "web-server"
    ManagedBy   = "terraform"
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS 区域"
  type        = string
  default     = "us-east-1"
}

variable "ami_id" {
  description = "AMI ID (Ubuntu 22.04 LTS)"
  type        = string
  default     = "ami-051f8a213df8bc089"
}

variable "key_name" {
  description = "EC2 密钥对名称"
  type        = string
  default     = "my-key-pair"
}

variable "ansible_user" {
  description = "Ansible SSH 用户"
  type        = string
  default     = "ubuntu"
}

variable "private_key_path" {
  description = "私钥文件路径"
  type        = string
  default     = "~/.ssh/my-key-pair.pem"
}

variable "env_configs" {
  description = "各环境配置"
  type = map(object({
    vpc_cidr          = string
    instance_type     = string
    min_instances     = number
    max_instances     = number
    desired_instances = number
    scale_in_cpu      = number
    scale_out_cpu     = number
  }))
  default = {
    dev = {
      vpc_cidr          = "10.1.0.0/16"
      instance_type     = "t2.micro"
      min_instances     = 1
      max_instances     = 2
      desired_instances = 1
      scale_in_cpu      = 20
      scale_out_cpu     = 60
    }
    staging = {
      vpc_cidr          = "10.2.0.0/16"
      instance_type     = "t2.small"
      min_instances     = 2
      max_instances     = 4
      desired_instances = 2
      scale_in_cpu      = 20
      scale_out_cpu     = 50
    }
    prod = {
      vpc_cidr          = "10.3.0.0/16"
      instance_type     = "t3.medium"
      min_instances     = 3
      max_instances     = 10
      desired_instances = 3
      scale_in_cpu      = 30
      scale_out_cpu     = 40
    }
  }
}

resource "aws_vpc" "main" {
  cidr_block = local.vpc_cidr

  tags = merge(local.common_tags, {
    Name = "${local.environment}-vpc"
  })
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.environment}-igw"
  })
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(local.vpc_cidr, 8, 1)
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.environment}-public-a"
  })
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(local.vpc_cidr, 8, 2)
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.environment}-public-b"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = merge(local.common_tags, {
    Name = "${local.environment}-public-rt"
  })
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "web" {
  name        = "${local.environment}-web-sg"
  description = "Allow HTTP, HTTPS, and restricted SSH"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH (restricted to current public IP)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.my_public_ip_cidr]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.environment}-web-sg"
  })
}

resource "aws_security_group" "alb" {
  name        = "${local.environment}-alb-sg"
  description = "ALB Security Group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.environment}-alb-sg"
  })
}
