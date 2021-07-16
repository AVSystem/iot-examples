resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_policy_attachment" "policy_attachment" {
  name = "attachment"
  roles = [aws_iam_role.iam_for_lambda.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


resource "random_string" "r" {
  length = 16
  special = false
}

data "archive_file" "lambda_zip" {
  type = "zip"
  source_dir = "lwm2mOperation"
  output_path = "lwm2mOperation.zip"
  depends_on = [random_string.r]
}

resource "aws_lambda_function" "lwm2mOperation" {
  filename      = "lwm2mOperation.zip"
  function_name = "lwm2mOperation"
  role          = aws_iam_role.iam_for_lambda.arn
  handler       = "lambda_function.lambda_handler"

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  runtime = "python3.8"
  environment {
    variables = {
      coioteDMrestPassword = var.coioteDMrestPassword
      coioteDMrestUri = var.coioteDMrestURL
      coioteDMrestUsername = var.coioteDMrestUsername
    }
  }

}

module "iot_rule_1" {
  name = "operationRequest"
  sql_query = "SELECT state.desired.operation AS operation, state.desired.keys AS keys, state.desired.values AS values, state.desired.attributes AS attributes, state.desired.arguments AS arguments, topic(3) AS thingName FROM '$aws/things/+/shadow/name/operation/update/accepted' WHERE isUndefined(state.desired.operation) = false"
  source  = "git::https://github.com/Passarinho4/terraform-aws-iot-topic-rule.git?ref=master" 
  lambda = ["lwm2mOperation"]
  depends_on = [aws_lambda_function.lwm2mOperation]
}

module "iot_rule_2" {
  name = "operationResponse"
  sql_query = "SELECT state.reported.result AS state.reported FROM '$aws/things/+/shadow/name/operation/update/accepted' WHERE (CASE isUndefined(state.reported.operation) WHEN true THEN false ELSE CASE state.reported.operation = 'read' OR state.reported.operation = 'write' OR state.reported.operation = 'readComposite' when true THEN true ELSE false END END) = true"
  source = "git::https://github.com/Passarinho4/terraform-aws-iot-topic-rule.git?ref=master"
  republish = [{topic = "$$aws/things/$${topic(3)}/shadow/name/datamodel/update"}]
}
