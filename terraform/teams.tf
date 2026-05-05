# Per-team resources. The whole point of the project is that these resources
# are NOT tagged with team — the model has to infer ownership from behavior.

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# ---------- VPCs (one per team) ----------
resource "aws_vpc" "team" {
  for_each   = var.teams
  cidr_block = each.value.cidr
  # Intentionally no `team` tag.
  tags = { Name = "${var.project}-${each.key}-vpc" }
}

resource "aws_subnet" "team" {
  for_each          = var.teams
  vpc_id            = aws_vpc.team[each.key].id
  cidr_block        = cidrsubnet(each.value.cidr, 8, 1)
  availability_zone = "${var.region}a"
  tags              = { Name = "${var.project}-${each.key}-subnet" }
}

resource "aws_db_subnet_group" "team" {
  for_each   = var.teams
  name       = "${var.project}-${each.key}"
  subnet_ids = [aws_subnet.team[each.key].id, aws_subnet.team_b[each.key].id]
}

resource "aws_subnet" "team_b" {
  for_each          = var.teams
  vpc_id            = aws_vpc.team[each.key].id
  cidr_block        = cidrsubnet(each.value.cidr, 8, 2)
  availability_zone = "${var.region}b"
  tags              = { Name = "${var.project}-${each.key}-subnet-b" }
}

data "aws_caller_identity" "current" {}

# ---------- IAM (one role per team, distinct ARN -> behavioral signal) ----------
# Trust policy allows BOTH:
#   - EC2 service (so EC2 instances can assume the role)
#   - Anyone in this AWS account (so the simulators can sts:AssumeRole as
#     each team to generate per-team CloudTrail events)
# The second clause is the difference between "all events look like the user"
# and "events look like each team's role" — without it, behavioral attribution
# has nothing to learn from.
resource "aws_iam_role" "team" {
  for_each = var.teams
  name     = "${each.value.iam_role_prefix}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = ["ec2.amazonaws.com", "lambda.amazonaws.com"] }
        Action    = "sts:AssumeRole"
      },
      {
        Effect    = "Allow"
        Principal = { AWS = data.aws_caller_identity.current.account_id }
        Action    = "sts:AssumeRole"
      },
    ]
  })
}

# Each team role gets read access to the resources it owns. Real teams have
# more permissions but for the simulator we only need read.
resource "aws_iam_role_policy" "team_read" {
  for_each = var.teams
  role     = aws_iam_role.team[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ec2:Describe*",
        "rds:Describe*",
        "lambda:Get*", "lambda:List*", "lambda:Invoke*",
        "s3:Get*", "s3:List*", "s3:PutObject",
      ]
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "team_ssm" {
  for_each   = var.teams
  role       = aws_iam_role.team[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "team" {
  for_each = var.teams
  name     = "${each.value.iam_role_prefix}-profile"
  role     = aws_iam_role.team[each.key].name
}

# ---------- EC2 (2 per team) ----------
resource "aws_instance" "team" {
  for_each              = { for pair in setproduct(keys(var.teams), [0, 1]) :
                            "${pair[0]}-${pair[1]}" => { team = pair[0], idx = pair[1] } }
  ami                   = data.aws_ami.amazon_linux.id
  instance_type         = var.teams[each.value.team].instance_type
  subnet_id             = aws_subnet.team[each.value.team].id
  iam_instance_profile  = aws_iam_instance_profile.team[each.value.team].name
  tags                  = { Name = "${var.project}-${each.key}" }
}

# ---------- RDS (1 per team) ----------
resource "aws_db_instance" "team" {
  for_each               = var.teams
  identifier             = "${var.project}-${each.key}"
  engine                 = "postgres"
  engine_version         = "15"   # major version only; RDS picks latest minor
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  username               = "appuser"
  password               = var.rds_password
  db_subnet_group_name   = aws_db_subnet_group.team[each.key].name
  skip_final_snapshot    = true
  publicly_accessible    = false
}

# ---------- Lambda (1 per team) ----------
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/.lambda.zip"
  source {
    content  = "def handler(event, ctx):\n    return {'ok': True}\n"
    filename = "index.py"
  }
}

resource "aws_lambda_function" "team" {
  for_each      = var.teams
  function_name = "${each.value.iam_role_prefix}-fn"
  role          = aws_iam_role.team[each.key].arn
  handler       = "index.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.lambda_zip.output_path
}

# ---------- S3 (1 per team) ----------
resource "aws_s3_bucket" "team" {
  for_each      = var.teams
  bucket        = "${var.project}-${each.key}-${random_id.suffix.hex}"
  force_destroy = true
}

# ---------- VPC flow logs ----------
resource "aws_flow_log" "team" {
  for_each        = var.teams
  vpc_id          = aws_vpc.team[each.key].id
  iam_role_arn    = aws_iam_role.flow_logs.arn
  log_destination = aws_cloudwatch_log_group.flow_logs.arn
  traffic_type    = "ALL"
}
