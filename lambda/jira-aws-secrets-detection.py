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

import json
import os
import boto3

# Lambda function that does the following:
# 1. Parse SNS event to capture fields to enter records into a dynamodb table such as messageId, timestamp and message
# 2. Create dynamodb entry


# Setup env var for DynamoDB table name
dynamo_table_name = os.environ['DYNAMODB_TABLE_NAME']

# Create lambda handler function

def lambda_handler(event, context):
    # print out event
    print("Event: ",event)
    # Parse event to capture the messageId, timestamp and message
    try:
        if(event['Records'][0]['Sns']['Message']):
            record_entry = parse_event_records(event)
        else:
            print("Event: " ,event)
        if(record_entry):
            print("Creating dynamodb entry...")
            createRecord(record_entry['messageId'], record_entry['referenceId'],
                         record_entry['awssecretId'], record_entry['eventName'],
                         record_entry['sourceApp'], record_entry['eventTimeStamp'])
    # Handle non-SNS events
    except KeyError:
        print("Not a SNS event")
        record_entry=None
    
    return {
        'statusCode': 200,
        'body': json.dumps(event)
    }

# Create function to parse Event Records field
def parse_event_records(event):
    #print(event)
    message = event['Records'][0]['Sns']['Message']

    # Parse SNS json fields    
    try:
        # Parse Jira SNS event json fields
        if(json.loads(message).get('automationData', None)):
            sourceApp = "Jira"
            messageId = event['Records'][0]['Sns']['MessageId']
            timeStamp = event['Records'][0]['Sns']['Timestamp']
            # Parse the message to capture the referenceId, eventName and awssecretId
            referenceId = json.loads(message)['automationData']['jira-key']
            eventName = json.loads(message)['automationData']['jira-summary']
            awssecretId = json.loads(message)['automationData']['jira-aws-secret-key-arn']
            print(messageId)
            print(timeStamp)
            print(referenceId)
            print(eventName)
            print(awssecretId)
            recordEntry={'messageId':messageId,'referenceId': referenceId,'awssecretId': awssecretId,'eventName': eventName,'sourceApp': sourceApp,'eventTimeStamp': timeStamp}
            #createRecord(messageId,referenceId,awssecretId,eventName,sourceApp,timeStamp)
            return recordEntry
        # If other type of SNS message
        else:
            print("Other type of SNS message")
            recordEntry=None
    except KeyError as e:
        print("Exception: ",e)
        recordEntry=None
        
# Create function to create dynamodb entry
def createRecord(messageId,refId,secretID,eventName, sourceApp,timeStamp):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(dynamo_table_name)
    print("Creating record in dynamodb in table: ", dynamo_table_name)
    try:
        response = table.put_item(
        Item={
            'messageId': messageId,
            'referenceId': refId,
            'AWSsecretId': secretID,
            'eventName': eventName,
            'sourceApp': sourceApp,
            'eventTimeStamp': timeStamp
        }
    )
    except:
        print("Error creating record in dynamodb")