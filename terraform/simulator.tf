# A 24/7 t3.micro that runs the per-team simulators in the cloud, so
# CloudTrail event accumulation isn't gated on the developer's laptop being
# awake. Costs ~$0.30/day, about $2 over a 7-day evaluation window.
#
# Lifecycle: created by `terraform apply` alongside the rest of the labeled
# env. Destroyed automatically by `terraform destroy` (or by
# scripts/real-aws-finish.sh).

# Use the account's default VPC for outbound internet — the per-team VPCs
# in teams.tf are intentionally isolated (no IGW), but this simulator EC2
# needs to reach STS, EC2/S3/Lambda APIs (to generate CloudTrail), and
# github.com (to pull the repo).
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# IAM role: lets this EC2 instance AssumeRole into each team role
# (so its API calls show up in CloudTrail as the team's role, which is
# what the GraphSAGE behavioral fingerprint is built from).
resource "aws_iam_role" "simulator" {
  name = "${var.project}-simulator-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "simulator_assume_team" {
  role = aws_iam_role.simulator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Resource = [for k, _ in var.teams :
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.teams[k].iam_role_prefix}-role"
      ]
    }]
  })
}

# SSM core so you can `aws ssm start-session --target <id>` into the box
# for debugging without an SSH key.
resource "aws_iam_role_policy_attachment" "simulator_ssm" {
  role       = aws_iam_role.simulator.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "simulator" {
  name = "${var.project}-simulator-profile"
  role = aws_iam_role.simulator.name
}

# Security group: outbound only. No inbound — we don't need SSH.
resource "aws_security_group" "simulator" {
  name        = "${var.project}-simulator-sg"
  description = "egress only - simulator host"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# user_data: install python+git, clone the repo, install costdna, write a
# systemd unit that runs the scheduled simulator with auto-restart.
locals {
  simulator_user_data = <<-USERDATA
    #!/bin/bash
    set -eux

    dnf install -y python3.11 python3.11-pip git

    sudo -u ec2-user bash -lc '
      cd /home/ec2-user
      git clone https://github.com/pauti04/CostDNA.git costdna
      cd costdna
      python3.11 -m pip install --user -e .
    '

    cat > /etc/systemd/system/costdna-sim.service <<EOF
    [Unit]
    Description=CostDNA per-team workload simulator
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    User=ec2-user
    WorkingDirectory=/home/ec2-user/costdna
    Environment=AWS_DEFAULT_REGION=${var.region}
    Environment=PATH=/home/ec2-user/.local/bin:/usr/local/bin:/usr/bin:/bin
    ExecStart=/home/ec2-user/.local/bin/python3.11 -m simulation.run_scheduled --teams backend,data,ml --tz UTC
    StandardOutput=append:/home/ec2-user/sim.log
    StandardError=append:/home/ec2-user/sim.log
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
    EOF

    systemctl daemon-reload
    systemctl enable --now costdna-sim
  USERDATA
}

resource "aws_instance" "simulator" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = data.aws_subnets.default.ids[0]
  iam_instance_profile   = aws_iam_instance_profile.simulator.name
  vpc_security_group_ids = [aws_security_group.simulator.id]
  user_data              = local.simulator_user_data
  user_data_replace_on_change = true

  tags = {
    Name = "${var.project}-simulator"
    role = "simulator-host"
  }
}

output "simulator_instance_id" {
  value = aws_instance.simulator.id
}

output "simulator_ssm_command" {
  value = "aws ssm start-session --target ${aws_instance.simulator.id} --region ${var.region}"
  description = "Run this to shell into the simulator box for debugging"
}
