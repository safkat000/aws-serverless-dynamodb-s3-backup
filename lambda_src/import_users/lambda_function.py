"""Lambda 1: Retrieve demo users from JSONPlaceholder and store them in DynamoDB.

Environment variable: TABLE_NAME=jsonplaceholder-users
IAM actions: dynamodb:PutItem, plus AWSLambdaBasicExecutionRole for logs.
Handler: lambda_function.lambda_handler
"""

import json
import os
import urllib.request

import boto3

API_URL = "https://jsonplaceholder.typicode.com/users"
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    table_name = os.environ["TABLE_NAME"]
    table = dynamodb.Table(table_name)

    print(f"Fetching users from {API_URL}")
    request = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "student-lambda-dynamodb-lab/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            users = json.load(response)

        if not isinstance(users, list):
            raise ValueError("Expected a JSON list of user objects")

        saved_count = 0
        for user in users:
            if not isinstance(user, dict) or not isinstance(user.get("id"), int):
                raise ValueError(f"Unexpected user record: {user!r}")

            # Stores all attributes, including nested company/address objects.
            # Re-running this function replaces existing items with matching id values.
            table.put_item(Item=user)
            saved_count += 1
            print(f"Saved user {user['id']}: {user.get('name', '(no name)')}")

        print(f"SUCCESS: Saved {saved_count} users to DynamoDB table {table_name}")
        return {
            "statusCode": 200,
            "body": json.dumps({"table": table_name, "saved_count": saved_count}),
        }

    except Exception as exc:
        print(f"ERROR: Import failed: {exc}")
        raise  # Important: an unhandled exception increments Lambda's Errors metric.
