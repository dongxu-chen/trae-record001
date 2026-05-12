output "environment" {
  description = "当前环境"
  value       = terraform.workspace
}

output "alb_dns_name" {
  description = "ALB DNS 名称"
  value       = aws_lb.web.dns_name
}

output "alb_zone_id" {
  description = "ALB Zone ID"
  value       = aws_lb.web.zone_id
}

output "target_group_arn" {
  description = "目标组 ARN"
  value       = aws_lb_target_group.web.arn
}

output "asg_name" {
  description = "Auto Scaling 组名称"
  value       = aws_autoscaling_group.web.name
}

output "asg_desired_capacity" {
  description = "ASG 期望容量"
  value       = aws_autoscaling_group.web.desired_capacity
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "web_security_group_id" {
  description = "Web 服务器安全组 ID"
  value       = aws_security_group.web.id
}

output "alb_security_group_id" {
  description = "ALB 安全组 ID"
  value       = aws_security_group.alb.id
}

output "public_subnet_ids" {
  description = "公网子网 ID 列表"
  value       = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}
