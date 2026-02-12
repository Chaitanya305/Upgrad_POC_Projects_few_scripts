locals {
  stage = "prod"
}
variable "name" {
  default = "poc"
  type = string
}
#create s3 bucket for cloudtrail logs
resource "aws_s3_bucket" "s3_cloudtrail" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  bucket        = "degrees-${var.name}-cloudtrail-bucket"
  force_destroy = true
  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_s3_bucket_public_access_block" "s3_cloudtrail" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  bucket                  = aws_s3_bucket.s3_cloudtrail[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "s3_cloudtrail" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  bucket = aws_s3_bucket.s3_cloudtrail[0].id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
  # Add just this depends_on condition
  depends_on = [aws_s3_bucket_public_access_block.s3_cloudtrail[0]]
}

resource "aws_s3_bucket_versioning" "s3_cloudtrail" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  bucket = aws_s3_bucket.s3_cloudtrail[0].id
  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_cloudtrail" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  bucket = aws_s3_bucket.s3_cloudtrail[0].bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "aws_iam_policy_document" "s3_cloudtrail" {
  statement {
    sid     = "AWSCloudTrailAclCheck"
    effect  = "Allow"
    actions = ["s3:GetBucketAcl", "s3:PutObject"]
    principals {
      identifiers = ["cloudtrail.amazonaws.com"]
      type        = "Service"
    }
    resources = [
      "arn:aws:s3:::${aws_s3_bucket.s3_cloudtrail[0].id}/*",
      "arn:aws:s3:::${aws_s3_bucket.s3_cloudtrail[0].id}"
    ]
  }
}
resource "aws_s3_bucket_policy" "s3_cloudtrail" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  bucket = aws_s3_bucket.s3_cloudtrail[0].id
  policy = data.aws_iam_policy_document.s3_cloudtrail.json
}

#cloudwatch log group
resource "aws_cloudwatch_log_group" "cloudtrail_log_group" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  name = "degrees-${var.name}-cloudtrail-log-group"
}

#iam role for cloudtrail to store logs in cloudwatch
data "aws_iam_policy_document" "cloudtrail_role" {
  statement {
    sid    = "cloudtrailTrust"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}
resource "aws_iam_role" "cloudtrail_role" { 
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  assume_role_policy = data.aws_iam_policy_document.cloudtrail_role.json
  description        = "iam role for cloudtrail to store logs in cloudwatch"
  name               = "degrees-${var.name}-cloudtrail-role"
}
#policy to put logs in cloudwatch
data "aws_iam_policy_document" "cloudtrail_policy" {
  statement {
    sid     = "AWSCloudTrailCreateLogStream"
    effect  = "Allow"
    actions = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [
      "${aws_cloudwatch_log_group.cloudtrail_log_group[0].arn}:*"
    ]
  }
}
resource "aws_iam_policy" "cloudtrail_policy" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  name        = "degrees-${var.name}-cloudtrail-policy"
  description = "IAM policy for Lambda to write logs to CloudWatch"
  policy      = data.aws_iam_policy_document.cloudtrail_policy.json
}
# Attach the policy to the role
resource "aws_iam_role_policy_attachment" "cloudtrail_policy_attach" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  role       = aws_iam_role.cloudtrail_role[0].name
  policy_arn = aws_iam_policy.cloudtrail_policy[0].arn
}

#create cloudtrail.
resource "aws_cloudtrail" "aws_activity_monitoring" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  depends_on = [aws_s3_bucket.s3_cloudtrail[0], aws_cloudwatch_log_group.cloudtrail_log_group[0]]
  name                          = "degrees-${var.name}-aws-activity-monitoring"
  s3_bucket_name                = aws_s3_bucket.s3_cloudtrail[0].id
  include_global_service_events = true
  is_multi_region_trail = true
  cloud_watch_logs_group_arn = "${aws_cloudwatch_log_group.cloudtrail_log_group[0].arn}:*"
  cloud_watch_logs_role_arn = aws_iam_role.cloudtrail_role[0].arn
  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "aws_activity_monitoring_lambda_role" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  name = "degrees-${var.name}-aws-activity-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

data "aws_iam_policy_document" "aws_activity_monitoring_lambda" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "secretsmanager:GetSecretValue"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "aws_activity_monitoring_lambda" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  name        = "degrees-${var.name}-aws-activity-monitoring-lambda-policy"
  description = "IAM policy for Lambda to write logs to CloudWatch"
  policy      = data.aws_iam_policy_document.aws_activity_monitoring_lambda.json
}

# Attach the policy to the role
resource "aws_iam_role_policy_attachment" "aws_activity_monitoring_lambda_attach" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  role       = aws_iam_role.aws_activity_monitoring_lambda_role[0].name
  policy_arn = aws_iam_policy.aws_activity_monitoring_lambda[0].arn
}

# Generate name for lambda zip file
locals {
  timestamp = formatdate("YYYYMMDDHHMM", timestamp())
  zip_file  = "user_monitoring_${local.timestamp}.zip"
}

# Create zip file locally using null_resource + local-exec
resource "null_resource" "zip_lambda" {
  triggers = {
    lambda_source_hash = filemd5("user_monitoring.py")
  }
  count       = local.stage == "prod" ? 1 : 0
  provisioner "local-exec" {
    command = "zip -r ${local.zip_file} user_monitoring.py"
  }
}

resource "aws_lambda_layer_version" "pymysql_layer_nv" {
    provider = aws.virginia
    count       = local.stage == "prod" ? 1 : 0
    filename = "pymysql_layer.zip"
    layer_name = "degrees-${var.name}-pymysql_layer"
    compatible_runtimes = ["python3.9"]
}

#lambda to trigger after 
resource "aws_lambda_function" "aws_activity_monitoring_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  filename = local.zip_file
  function_name = "degrees-${var.name}-aws-activity-monitoring"
  role = aws_iam_role.aws_activity_monitoring_lambda_role[0].arn
  handler = "user_monitoring.lambda_handler"
  source_code_hash = filebase64sha256("user_monitoring.py")
  runtime = "python3.9"
  architectures = ["x86_64"]
  layers = [aws_lambda_layer_version.pymysql_layer_nv[0].arn]
  timeout = 60 #in sec
  depends_on = [ aws_lambda_layer_version.pymysql_layer_nv[0] ]
}

#create event rule for console sign in
resource "aws_cloudwatch_event_rule" "console_sign_in_event_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  name        = "degrees-${var.name}-capture-aws-sign-in"
  description = "Capture each AWS Console Sign In"

  event_pattern = jsonencode({
    detail-type = [
      "AWS Console Sign In via CloudTrail"
    ]
  })
}

#target for console sign in rule
resource "aws_cloudwatch_event_target" "console_sign_in_event_target_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  depends_on = [ aws_lambda_function.aws_activity_monitoring_nv[0], aws_cloudwatch_event_rule.console_sign_in_event_nv[0]]
  rule      = aws_cloudwatch_event_rule.console_sign_in_event_nv[0].name
  arn       = aws_lambda_function.aws_activity_monitoring_nv[0].arn
}

# Allow EventBridge rule to invoke Lambda for console sign in events
resource "aws_lambda_permission" "allow_eventbridge_console_sign_in_event_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  statement_id  = "AllowExecutionFromEventConsoleSignIn"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.aws_activity_monitoring_nv[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.console_sign_in_event_nv[0].arn
}


#new code here
#rule for write opeartions for ec2 iam lambda ELB
resource "aws_cloudwatch_event_rule" "write_operations_event_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  name        = "degrees-${var.name}-write-operations"
  description = "Capture AWS Write opeartions for ec2 iam lambda ELB"

  event_pattern = jsonencode({
  "source": ["aws.ec2", "aws.s3", "aws.iam", "aws.lambda", "aws.elasticloadbalancing", "aws.autoscaling"], 
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": [
      "ec2.amazonaws.com",
      "s3.amazonaws.com",
      "iam.amazonaws.com",
      "lambda.amazonaws.com",
      "elasticloadbalancing.amazonaws.com",
      "autoscaling.amazonaws.com"
    ],
    "eventName": [
      "RunInstances",
      "CreateBucket",
      "DeleteBucket",
      "CreateUser",
      "DeleteUser",
      "UpdateUser",
      "AttachUserPolicy",
      "DetachUserPolicy",
      "StartInstances",
      "StopInstances",
      "TerminateInstances",
      "RebootInstances",
      "CreateImage",
      "CreateTags",
      "DeleteTags",
      "ModifyInstanceAttribute",
      "AllocateAddress",
      "ReleaseAddress",
      "AssociateAddress",
      "DisassociateAddress",
      "CreateSecurityGroup",
      "DeleteSecurityGroup",
      "AuthorizeSecurityGroupIngress",
      "AuthorizeSecurityGroupEgress",
      "RevokeSecurityGroupIngress",
      "RevokeSecurityGroupEgress",
      "AttachVolume",
      "DetachVolume",
      "CreateVolume",
      "DeleteVolume",
      "ModifyVolume",
      "CreateAccessKey",
      "DeleteAccessKey",
      "UpdateAccessKey",
      "CreateRole",
      "DeleteRole",
      "UpdateRole",
      "AttachRolePolicy",
      "DetachRolePolicy",
      "CreateGroup",
      "DeleteGroup",
      "AddUserToGroup",
      "RemoveUserFromGroup",
      "PutRolePolicy",
      "DeleteRolePolicy",
      "PutUserPolicy",
      "DeleteUserPolicy",
      # Elastic Load Balancing (ELB / ALB / NLB)
      "CreateLoadBalancer",
      "DeleteLoadBalancer",
      "ModifyLoadBalancerAttributes",  
      # Listeners
      "CreateListener",
      "DeleteListener",
      "ModifyListener",  
      # Target Groups (ALB/NLB)
      "CreateTargetGroup",
      "DeleteTargetGroup",
      "ModifyTargetGroup",  
      # Registration / Deregistration
      "RegisterTargets",
      "DeregisterTargets",  
      # SSL / Certificates
      "AddListenerCertificates",
      "RemoveListenerCertificates",
      #rule in alb
      "CreateRule",
      "DeleteRule",
      "ModifyRule",
      "CreateVpc",
      "DeleteVpc",
      "ModifyVpcAttribute",
      "CreateSubnet",
      "DeleteSubnet",
      "ModifySubnetAttribute",
      "AllocateAddress",
      "ReleaseAddress",
      "AssociateAddress",
      "DisassociateAddress",
      "CreateNatGateway",
      "DeleteNatGateway",
      "CreateInternetGateway",
      "DeleteInternetGateway",
      "AttachInternetGateway",
      "DetachInternetGateway",
      #asg monitor
      "CreateAutoScalingGroup",
      "UpdateAutoScalingGroup",
      "DeleteAutoScalingGroup"
    ],
    "userIdentity": {
      "type": ["IAMUser", "AssumedRole"]
    }
  }})
}

#target for write opeartions rule for ec2 iam lambda ELB
resource "aws_cloudwatch_event_target" "aws_write_operations_target_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  depends_on = [ aws_lambda_function.aws_activity_monitoring_nv[0], aws_cloudwatch_event_rule.write_operations_event_nv[0]]
  rule      = aws_cloudwatch_event_rule.write_operations_event_nv[0].name
  arn       = aws_lambda_function.aws_activity_monitoring_nv[0].arn
}

#invoke permission for write opeartions rule for ec2 iam lambda ELB
resource "aws_lambda_permission" "allow_eventbridge_for_write_operations_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  statement_id  = "AllowExecutionFromEventBridgeForWriteNV"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.aws_activity_monitoring_nv[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.write_operations_event_nv[0].arn
}

#event rule for rds write opeartions
resource "aws_cloudwatch_event_rule" "write_operations_rds_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  name        = "degrees-${var.name}-write-operations-rds"
  description = "Capture Write opeartions for rds"

  event_pattern = jsonencode({
  "source": ["aws.rds"], 
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": [
      "rds.amazonaws.com"
    ],
    "eventName": [
      # RDS Core Actions
      "CreateDBInstance",
      "DeleteDBInstance",
      "ModifyDBInstance",
      "StartDBInstance",
      "StopDBInstance",
      "RebootDBInstance",
      "PromoteReadReplica",
      
      # RDS Cluster
      "CreateDBCluster",
      "DeleteDBCluster",
      "ModifyDBCluster",
      "StartDBCluster",
      "StopDBCluster",
      "RebootDBCluster",
      
      # Snapshots
      "CreateDBSnapshot",
      "DeleteDBSnapshot",
      "CopyDBSnapshot",
      "ModifyDBSnapshot",
      
      # Parameter & Option Groups
      "CreateDBParameterGroup",
      "DeleteDBParameterGroup",
      "ModifyDBParameterGroup",
      "CreateOptionGroup",
      "DeleteOptionGroup",
      "ModifyOptionGroup",
      
      # Security & Networking
      "CreateDBSecurityGroup",
      "DeleteDBSecurityGroup",
      "AuthorizeDBSecurityGroupIngress",
      "RevokeDBSecurityGroupIngress",
      "ModifyDBSubnetGroup",
      "CreateDBSubnetGroup",
      "DeleteDBSubnetGroup",
    ],
    "userIdentity": {
      "type": ["IAMUser", "AssumedRole"]
    }
  }})
}

#target for rds write rule
resource "aws_cloudwatch_event_target" "write_operations_rds_event_target_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  depends_on = [ aws_lambda_function.aws_activity_monitoring_nv[0], aws_cloudwatch_event_rule.write_operations_rds_nv[0]]
  rule      = aws_cloudwatch_event_rule.write_operations_rds_nv[0].name
  arn       = aws_lambda_function.aws_activity_monitoring_nv[0].arn
}

#invoke permission for rds rule
resource "aws_lambda_permission" "allow_eventbridge_for_write_operations_rds_nv" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.virginia
  statement_id  = "AllowExecutionFromEventBridgeForWriteRDSNV"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.aws_activity_monitoring_nv[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.write_operations_rds_nv[0].arn
}


#for ap-south-1 rule

#lambda layer for pymsql
resource "aws_lambda_layer_version" "pymysql_layer_aps1" {
    provider = aws.mumbai
    count       = local.stage == "prod" ? 1 : 0
    filename = "pymysql_layer.zip"
    layer_name = "degrees-${var.name}-pymysql_layer"
    compatible_runtimes = ["python3.9"]
}

#New lamda for ap-south-1 region
resource "aws_lambda_function" "aws_activity_monitoring_aps1" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.mumbai
  filename = local.zip_file
  function_name = "degrees-${var.name}-aws-activity-monitoring"
  role = aws_iam_role.aws_activity_monitoring_lambda_role[0].arn
  handler = "user_monitoring.lambda_handler"
  source_code_hash = filebase64sha256("user_monitoring.py")
  runtime = "python3.9"
  architectures = ["x86_64"]
  layers = [aws_lambda_layer_version.pymysql_layer_aps1[0].arn]
  timeout = 60 #in sec
  depends_on = [ aws_lambda_layer_version.pymysql_layer_aps1[0] ]
}

#rule for write opeartions rule for ec2 iam lambda ELB in ap-south-1
resource "aws_cloudwatch_event_rule" "aws_write_operations_aps1" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.mumbai
  name        = "degrees-${var.name}-write-operations"
  description = "Capture Write opeartions for ec2 iam lambda ELB"

  event_pattern = jsonencode({
  "source": ["aws.ec2", "aws.s3", "aws.iam", "aws.lambda", "aws.elasticloadbalancing", "aws.vpc", "aws.autoscaling"], 
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": [
      "ec2.amazonaws.com",
      "s3.amazonaws.com",
      "iam.amazonaws.com",
      "lambda.amazonaws.com",
      "elasticloadbalancing.amazonaws.com",
      "autoscaling.amazonaws.com"
    ],
    "eventName": [
      "RunInstances",
      "CreateBucket",
      "DeleteBucket",
      "CreateUser",
      "DeleteUser",
      "UpdateUser",
      "AttachUserPolicy",
      "DetachUserPolicy",
      "StartInstances",
      "StopInstances",
      "TerminateInstances",
      "RebootInstances",
      "CreateImage",
      "CreateTags",
      "DeleteTags",
      "ModifyInstanceAttribute",
      "AllocateAddress",
      "ReleaseAddress",
      "AssociateAddress",
      "DisassociateAddress",
      "CreateSecurityGroup",
      "DeleteSecurityGroup",
      "AuthorizeSecurityGroupIngress",
      "AuthorizeSecurityGroupEgress",
      "RevokeSecurityGroupIngress",
      "RevokeSecurityGroupEgress",
      "AttachVolume",
      "DetachVolume",
      "CreateVolume",
      "DeleteVolume",
      "ModifyVolume",
      "CreateAccessKey",
      "DeleteAccessKey",
      "UpdateAccessKey",
      "CreateRole",
      "DeleteRole",
      "UpdateRole",
      "AttachRolePolicy",
      "DetachRolePolicy",
      "CreateGroup",
      "DeleteGroup",
      "AddUserToGroup",
      "RemoveUserFromGroup",
      "PutRolePolicy",
      "DeleteRolePolicy",
      "PutUserPolicy",
      "DeleteUserPolicy",
      # Elastic Load Balancing (ELB / ALB / NLB)
      "CreateLoadBalancer",
      "DeleteLoadBalancer",
      "ModifyLoadBalancerAttributes",  
      # Listeners
      "CreateListener",
      "DeleteListener",
      "ModifyListener",  
      # Target Groups (ALB/NLB)
      "CreateTargetGroup",
      "DeleteTargetGroup",
      "ModifyTargetGroup",  
      # Registration / Deregistration
      "RegisterTargets",
      "DeregisterTargets",  
      # SSL / Certificates
      "AddListenerCertificates",
      "RemoveListenerCertificates",
      #rule in alb
      "CreateRule",
      "DeleteRule",
      "ModifyRule",
      #vpc_rules
      "CreateVpc",
      "DeleteVpc",
      "ModifyVpcAttribute",
      "CreateSubnet",
      "DeleteSubnet",
      "ModifySubnetAttribute",
      "AllocateAddress",
      "ReleaseAddress",
      "AssociateAddress",
      "DisassociateAddress",
      "CreateNatGateway",
      "DeleteNatGateway",
      "CreateInternetGateway",
      "DeleteInternetGateway",
      "AttachInternetGateway",
      "DetachInternetGateway",
      #asg monitor
      "CreateAutoScalingGroup",
      "UpdateAutoScalingGroup",
      "DeleteAutoScalingGroup"
    ],
    "eventCategory": ["Management"],
    "userIdentity": {
      "type": ["IAMUser", "AssumedRole"]
    },
  }})
}

#target for rule ec2 iam lambda ELB in ap-south-1
resource "aws_cloudwatch_event_target" "aws_write_operations_target_aps1" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.mumbai
  depends_on = [ aws_lambda_function.aws_activity_monitoring_aps1[0], aws_cloudwatch_event_rule.aws_write_operations_aps1[0]]
  rule      = aws_cloudwatch_event_rule.aws_write_operations_aps1[0].name
  arn       = aws_lambda_function.aws_activity_monitoring_aps1[0].arn
}

#invoke permission for rule ec2 iam lambda ELB in ap-south-1
resource "aws_lambda_permission" "allow_eventbridge_for_aws_write_operations_aps1" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.mumbai
  statement_id  = "AllowExecutionFromEventBridgeForWriteaps1"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.aws_activity_monitoring_aps1[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.aws_write_operations_aps1[0].arn
}

#rule for write operation in rds ap-south-1
resource "aws_cloudwatch_event_rule" "aws_write_operations_rds_aps1" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.mumbai
  name        = "degrees-${var.name}-write-operations-rds"
  description = "Capture each AWS Write opeartions"

  event_pattern = jsonencode({
  "source": ["aws.rds"], 
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": [
      "rds.amazonaws.com"
    ],
    "eventName": [
      # RDS Core Actions
      "CreateDBInstance",
      "DeleteDBInstance",
      "ModifyDBInstance",
      "StartDBInstance",
      "StopDBInstance",
      "RebootDBInstance",
      "PromoteReadReplica",
      # RDS Cluster
      "CreateDBCluster",
      "DeleteDBCluster",
      "ModifyDBCluster",
      "StartDBCluster",
      "StopDBCluster",
      "RebootDBCluster",
      # Snapshots
      "CreateDBSnapshot",
      "DeleteDBSnapshot",
      "CopyDBSnapshot",
      "ModifyDBSnapshot",
      # Parameter & Option Groups
      "CreateDBParameterGroup",
      "DeleteDBParameterGroup",
      "ModifyDBParameterGroup",
      "CreateOptionGroup",
      "DeleteOptionGroup",
      "ModifyOptionGroup",
      # Security & Networking
      "CreateDBSecurityGroup",
      "DeleteDBSecurityGroup",
      "AuthorizeDBSecurityGroupIngress",
      "RevokeDBSecurityGroupIngress",
      "ModifyDBSubnetGroup",
      "CreateDBSubnetGroup",
      "DeleteDBSubnetGroup",
    ],
    "userIdentity": {
      "type": ["IAMUser", "AssumedRole"]
    }
  }})
}

#target for rule write operation in rds ap-south-1
resource "aws_cloudwatch_event_target" "aws_write_operations_rds_aps1" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.mumbai
  depends_on = [ aws_lambda_function.aws_activity_monitoring_aps1[0], aws_cloudwatch_event_rule.aws_write_operations_rds_aps1[0]]
  rule      = aws_cloudwatch_event_rule.aws_write_operations_rds_aps1[0].name
  arn       = aws_lambda_function.aws_activity_monitoring_aps1[0].arn
}

#invoke permission for write operation in rds ap-south-1
resource "aws_lambda_permission" "allow_eventbridge_for_aws_write_operations_rds_aps1" {
  count       = local.stage == "prod" ? 1 : 0
  provider = aws.mumbai
  statement_id  = "AllowExecutionFromEventBridgeForWriteRDasp1"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.aws_activity_monitoring_aps1[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.aws_write_operations_rds_aps1[0].arn
}

