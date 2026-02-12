locals {
  stage = "prod"
}

variable "name" {
  default = "poc"
  type = string
}

data "aws_cloudwatch_log_group" "eks_audit_logs" {
  count    = local.stage == "prod" ? 1 : 0
  name = "/aws/eks/demo-eks-cluster/cluster" 
}

# IAM Role for Lambda
resource "aws_iam_role" "k8s_activity_monitoring_lambda_role" {
  count    = local.stage == "prod" ? 1 : 0
  name     = "degrees-${var.name}-k8s-activity-monitoring-role"
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

data "aws_iam_policy_document" "k8s_activity_monitoring_lambda" {
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

resource "aws_iam_policy" "k8s_activity_monitoring_lambda" {
  count       = local.stage == "prod" ? 1 : 0
  name        = "degrees-${var.name}-k8s-activity-monitoring-lambda-policy"
  description = "IAM policy for Lambda to write logs to CloudWatch"
  policy      = data.aws_iam_policy_document.k8s_activity_monitoring_lambda.json
}

# Attach the policy to the role
resource "aws_iam_role_policy_attachment" "k8s_activity_monitoring_lambda_attach" {
  count      = local.stage == "prod" ? 1 : 0
  role       = aws_iam_role.k8s_activity_monitoring_lambda_role[0].name
  policy_arn = aws_iam_policy.k8s_activity_monitoring_lambda[0].arn
}


locals {
  timestamp = formatdate("YYYYMMDDHHmmss", timestamp())
  zip_name  = "user_monitoring_${local.timestamp}.zip"
  zip_path  = "${path.module}/${local.zip_name}"
}

# Create a zip archive of your lambda function
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/k8s_monitoring.py"
  output_path = local.zip_path
}

#pymysql layer
resource "aws_lambda_layer_version" "pymysql_layer" {
  count               = local.stage == "prod" ? 1 : 0
  filename            = "pymysql_layer.zip"
  layer_name          = "degrees-${var.name}-pymysql-layer"
  compatible_runtimes = ["python3.9"]
}

# Lambda function
resource "aws_lambda_function" "k8s_activity_monitoring" {
  count         = local.stage == "prod" ? 1 : 0
  filename      = data.archive_file.lambda_zip.output_path
  function_name = "degrees-${var.name}-k8s-activity-monitoring"
  role          = aws_iam_role.k8s_activity_monitoring_lambda_role[0].arn
  handler       = "k8s_monitoring.lambda_handler"
  runtime       = "python3.9"
  architectures = ["x86_64"]
  layers        = [aws_lambda_layer_version.pymysql_layer[0].arn]
  timeout       = 60

  # Ensures new zip triggers a new deployment
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  depends_on = [aws_lambda_layer_version.pymysql_layer[0]]
}

# Cleanup the zip file after Lambda deployment
resource "null_resource" "cleanup_lambda_zip" {
  triggers = {
    lambda_file = data.archive_file.lambda_zip.output_path
  }

  depends_on = [aws_lambda_function.k8s_activity_monitoring[0]]

  provisioner "local-exec" {
    command = "rm -f ${data.archive_file.lambda_zip.output_path}"
  }
}

data "aws_lambda_function" "k8s_activity_monitoring"{
    count         = (local.stage == "prod"  && var.name == "common")? 1 : 0
    function_name = "degrees-common-k8s-activity-monitoring"
}

locals {
  k8s_lambda_fcuntion_name = (local.stage == "prod" && var.name == "poc") ? aws_lambda_function.k8s_activity_monitoring[0].function_name : data.aws_lambda_function.k8s_activity_monitoring[0].function_name
  k8s_lambda_fcuntion_arn = (local.stage == "prod" && var.name == "poc") ? aws_lambda_function.k8s_activity_monitoring[0].arn : data.aws_lambda_function.k8s_activity_monitoring[0].arn
}

# Allow cloudwatch log group to invoke Lambda for console sign in events
resource "aws_lambda_permission" "allow_k8s_audit_events" {
  count         = local.stage == "prod" ? 1 : 0
  statement_id  = "AllowExecutionFromEksAuditLogGroup"
  action        = "lambda:InvokeFunction"
  function_name = local.k8s_lambda_fcuntion_name
  principal     = "logs.amazonaws.com"
  source_arn    = "${data.aws_cloudwatch_log_group.eks_audit_logs[0].arn}:*"
}

#subscription filter
resource "aws_cloudwatch_log_subscription_filter" "eks_audit_logfilter" {
  name            = "eks_audit_logfilter"
  log_group_name  = "/aws/eks/demo-eks-cluster/cluster"
  filter_pattern  = "{ ($.verb = \"apply\" || $.verb = \"create\" || $.verb = \"update\" || $.verb = \"delete\" || $.verb = \"patch\") && ($.user.username = *upgrad-46com*) }"
  destination_arn = local.k8s_lambda_fcuntion_arn
  depends_on      = [aws_lambda_permission.allow_k8s_audit_events]
}

