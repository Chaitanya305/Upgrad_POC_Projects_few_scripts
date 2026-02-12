terraform {
    required_providers {
        aws = {
            source = "hashicorp/aws"
            version = "5.72.1"
        }
    }
}

provider "aws" {
  region = "us-east-1"
}

data "aws_iam_policy_document" "tfsec_poc" {
  statement {
    sid = "JenkinsWorkerDescribe"
    actions = [
      "ec2:DescribeSpotInstanceRequests",
      "ec2:DescribeInstances",
      "ec2:DescribeKeyPairs",
      "ec2:DescribeRegions",
      "ec2:DescribeImages",
      "ec2:DescribeAvailabilityZones",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeSubnets",
    ]
    effect    = "Allow"
    resources = ["*"]
  }
  statement {
    sid = "jenkinsWorker"
    actions = [
      "ec2:CancelSpotInstanceRequests",
      "ec2:GetConsoleOutput",
      "ec2:RequestSpotInstances",
      "ec2:RunInstances",
      "ec2:StartInstances",
      "ec2:StopInstances",
      "ec2:TerminateInstances",
      "ec2:CreateTags",
      "ec2:DeleteTags",
      "iam:ListInstanceProfilesForRole",
      "iam:PassRole",
      "lambda:InvokeFunction",
      "ec2:GetPasswordData"
    ]
    effect    = "Allow"
    resources = ["*"]
    condition {
      test     = "StringLike"
      variable = "aws:ResourceTag/Name"
      values   = ["common-*", "jenkins-*"]  # Only allow instances with names starting with 'jenkins- and common'
    }
  }
}

resource "aws_iam_policy" "tfsec_poc" {
  name_prefix = "tfsec-poc-policy"
  policy      = data.aws_iam_policy_document.tfsec_poc.json
}


#Describe not supports for condition statement. need to have separate for describe with wildecard