variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "costdna-synth"
}

# Per-team configuration. Add or remove teams here.
variable "teams" {
  type = map(object({
    cidr            = string
    instance_type   = string
    iam_role_prefix = string
  }))
  default = {
    backend = { cidr = "10.1.0.0/16", instance_type = "t3.micro", iam_role_prefix = "backend-svc" }
    data    = { cidr = "10.2.0.0/16", instance_type = "t3.micro", iam_role_prefix = "data-pipeline" }
    ml      = { cidr = "10.3.0.0/16", instance_type = "t3.micro", iam_role_prefix = "ml-training" }
  }
}

variable "rds_password" {
  type      = string
  sensitive = true
  default   = "ChangeMe123!"
}
