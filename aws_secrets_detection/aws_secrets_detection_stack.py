'''
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import os
from aws_cdk import (
    # Duration,
    Stack,
    aws_lambda as _lambda,
    aws_dynamodb as _dynamodb,
    Arn,
    ArnComponents,
    ArnFormat,
    aws_events as events,
    aws_events_targets as targets,
    aws_sns as sns,
    aws_iam as iam,
    Duration as duration
)
from constructs import Construct

stack = Stack()


class AwsSecretsDetectionStack(Stack):
    """Class representing the AWS Secrets Detection stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        arn_str = Arn.format(ArnComponents(partition='aws',
            service='dynamodb',
            region=os.getenv('CDK_DEFAULT_REGION'),
            account=os.getenv('CDK_DEFAULT_ACCOUNT'),
            resource='table',
            resource_name='aws-secrets-detection-table',
            arn_format=ArnFormat.SLASH_RESOURCE_NAME))

        '''iam_arn = Arn.format(ArnComponents(
            partition='aws',
            service='iam',
            region=os.getenv('CDK_DEFAULT_REGION'),
            account=os.getenv('CDK_DEFAULT_ACCOUNT'),
            resource='role',
            resource_name='AWSEventsBasicExecutionRole',
            arn_format=ArnFormat.COLON_RESOURCE_NAME))
        '''

        # Create a role for lambda
        lambda_role = iam.Role(self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )
        # Attach a custom policy to lambda_role
        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["dynamodb:PutItem",
                "dynamodb:DescribeTable",
                "dynamodb:GetItem",
                "dynamodb:Query",
                "dynamodb:UpdateItem",
                "dynamodb:GetRecords"],
            resources= [arn_str]
        ))

        # The code that defines your stack goes here
        aws_secrets_audit_trail_detection= _lambda.Function(
           self,
           "AWSSecretsAuditTrailDetection",
           runtime=_lambda.Runtime.PYTHON_3_12,
           handler="aws-secrets-audit-trail-detection.lambda_handler",
           code=_lambda.Code.from_asset("lambda"),
           role = lambda_role,
           timeout = duration.seconds(30),
           environment={
               "DYNAMODB_TABLE_NAME": "aws-secrets-detection-table"
           }
        )
        
        # The code that defines your stack goes here
        jira_aws_secrets_detection= _lambda.Function(
           self,
           "JiraAWSSecretsDetection",
           runtime=_lambda.Runtime.PYTHON_3_12,
           handler="jira-aws-secrets-detection.lambda_handler",
           code=_lambda.Code.from_asset("lambda"),
           role = lambda_role,
           timeout = duration.seconds(30),
           environment={
               "DYNAMODB_TABLE_NAME": "aws-secrets-detection-table"
           }
        )

        # Create a dynamodb table
        # aws_secrets_detection_table = _dynamodb.TableV2(
        _dynamodb.TableV2(
            self,
            "AwsSecretsDetectionTable",
            table_name="aws-secrets-detection-table",
            partition_key=_dynamodb.Attribute(
                name="messageId",
                type=_dynamodb.AttributeType.STRING
            ),
            sort_key=_dynamodb.Attribute(
                name="AWSsecretId",
                type=_dynamodb.AttributeType.STRING
            ),
            billing=_dynamodb.Billing.provisioned(
                read_capacity=_dynamodb.Capacity.fixed(10),
                 write_capacity=_dynamodb.Capacity.autoscaled(max_capacity=15)
            ),)

        # Define the EventBridge rule
        rule = events.Rule(
            self, 'secretsManager-detect-change',
            event_pattern={
                "source": ["aws.secretsmanager"],
                "detail": {
                "eventSource": ["secretsmanager.amazonaws.com"],
                "eventName": ["CreateSecret", "UpdateSecret", "DeleteSecret"]
                }
            },
            #targets=[targets.event_]
        )

        # Create an eventbus
        event_bus = events.EventBus(self, "bus",
            event_bus_name="secrets-detect-change-event-bus"
        )

        # Define the access policy for the event bus
        #access_policy = iam.PolicyDocument(
        iam.PolicyDocument(
            statements=[iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["events:PutEvents"],
                    resources=[event_bus.event_bus_arn],
                    principals=[],
                    conditions={
                        "Bool": {
                            "elasticfilesystem:AccessedViaMountTarget": "true"
                        }
                    }
        )])

        # IAM Policy for the event bus.  Need to create a var for principal org id
        statements_event_bus=iam.PolicyStatement(
                    sid="AllowPutEvents",
                    effect=iam.Effect.ALLOW,
                    actions=["events:PutEvents"],
                    resources=[event_bus.event_bus_arn],
                    principals= [iam.AnyPrincipal()],
                    conditions={
                        "StringEquals": {
                        "aws:PrincipalOrgID": os.getenv('AWS_PRINCIPAL_ORG_ID')
                        }
                    }
        )

        event_bus.add_to_resource_policy(statements_event_bus)

        # Create an sns topic

        jira_topic = sns.Topic(self, "JiraAWSSecretsDetectionTopic")
        statements_event_bus=iam.PolicyStatement(
                    sid="AllowPublishEvents",
                    effect=iam.Effect.ALLOW,
                    actions=["sns:Publish"],
                    resources=[jira_topic.topic_arn],
                    principals= [iam.AnyPrincipal()],
                    conditions={
                        "StringEquals": {
                        "aws:PrincipalOrgID": os.getenv('AWS_PRINCIPAL_ORG_ID')
                    }
                    }
        )
        jira_topic.add_to_resource_policy(statements_event_bus)
        
        secrets_topic = sns.Topic(self, "AWSSecretsAuditTrailDetectionTopic")
        statements_event_bus=iam.PolicyStatement(
                    sid="AllowPublishEvents",
                    effect=iam.Effect.ALLOW,
                    actions=["sns:Publish"],
                    resources=[secrets_topic.topic_arn],
                    principals= [iam.AnyPrincipal()],
                    conditions={
                        "StringEquals": {
                        "aws:PrincipalOrgID": os.getenv('AWS_PRINCIPAL_ORG_ID')
                    }
                    }
        )
        secrets_topic.add_to_resource_policy(statements_event_bus)

        # Add a target to the rule (example target - SNS topic)
        rule.add_target(targets.SnsTopic(secrets_topic))

        # add lambda to topic
        #sns_subscription = sns.Subscription(self, "AwsSecretsDetectionSubscription",
        sns.Subscription(self, "AWSSecretsAuditTrailDetectionSubscription",
            topic=secrets_topic,
            endpoint=aws_secrets_audit_trail_detection.function_arn,
            protocol=sns.SubscriptionProtocol.LAMBDA,
            #subscription_role_arn=lambda_role.role_arn,
        )
        
        sns.Subscription(self, "JiraAWSSecretsDetectionSubscription",
            topic=jira_topic,
            endpoint=jira_aws_secrets_detection.function_arn,
            protocol=sns.SubscriptionProtocol.LAMBDA,
            #subscription_role_arn=lambda_role.role_arn,
        )
