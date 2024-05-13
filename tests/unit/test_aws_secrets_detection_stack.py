import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_secrets_detection.aws_secrets_detection_stack import AwsSecretsDetectionStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_secrets_detection/aws_secrets_detection_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsSecretsDetectionStack(app, "aws-secrets-detection")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
