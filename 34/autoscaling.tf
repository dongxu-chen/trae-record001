resource "aws_launch_template" "web" {
  name_prefix   = "${local.environment}-web-lt-"
  image_id      = var.ami_id
  instance_type = local.instance_type
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.web.id]

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  update_default_version = true

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "${local.environment}-web-server"
    })
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(local.common_tags, {
      Name = "${local.environment}-web-server-volume"
    })
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "web" {
  name_prefix          = "${local.environment}-web-asg-"
  vpc_zone_identifier  = [aws_subnet.public_a.id, aws_subnet.public_b.id]
  desired_capacity     = local.desired_instances
  min_size             = local.min_instances
  max_size             = local.max_instances
  launch_template {
    id      = aws_launch_template.web.id
    version = "$Latest"
  }

  target_group_arns = [aws_lb_target_group.web.arn]

  tag {
    key                 = "Name"
    value               = "${local.environment}-web-server"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = local.environment
    propagate_at_launch = true
  }

  tag {
    key                 = "Project"
    value               = "web-server"
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_policy" "scale_out" {
  name                   = "${local.environment}-scale-out"
  autoscaling_group_name = aws_autoscaling_group.web.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = local.scale_out_cpu
  }
}

resource "aws_autoscaling_policy" "scale_in" {
  name                   = "${local.environment}-scale-in"
  autoscaling_group_name = aws_autoscaling_group.web.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = local.scale_in_cpu
  }
}
