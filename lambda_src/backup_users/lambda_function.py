"""Lambda 2: Export a small DynamoDB demo table to timestamped JSON files in S3.

Environment variables:
  TABLE_NAME=jsonplaceholder-users
  BUCKET_NAME=<your-unique-s3-bucket-name>
  BACKUP_PREFIX=backups  (optional; defaults to backups)
IAM actions: dynamodb:Scan and s3:PutObject; plus basic Lambda logging role.
Handler: lambda_function.lambda_handler

Note: This is a teaching/demo JSON export, not a transactional database backup.
"""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3


dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")


def json_serializer(value):
    """Make the Decimal values returned by DynamoDB JSON-serializable."""
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return str(value)  # Preserve precision for non-integer decimal values.
    raise TypeError(f"Unsupported JSON type: {type(value).__name__}")


def lambda_handler(event, context):
    table_name = os.environ["TABLE_NAME"]
    bucket_name = os.environ["BUCKET_NAME"]
    backup_prefix = os.environ.get("BACKUP_PREFIX", "backups").strip("/")
    if not backup_prefix:
        raise ValueError("BACKUP_PREFIX cannot be empty")

    table = dynamodb.Table(table_name)
    print(f"Reading DynamoDB table: {table_name}")

    try:
        items = []
        scan_options = {}
        pages = 0
        while True:
            response = table.scan(**scan_options)
            pages += 1
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            scan_options["ExclusiveStartKey"] = last_key

        items.sort(key=lambda user: user.get("id", 0))
        print(f"Read {len(items)} items over {pages} DynamoDB scan page(s)")

        now = datetime.now(timezone.utc)
        request_id = getattr(context, "aws_request_id", "manual-test")
        object_key = (
            f"{backup_prefix}/{now:%Y-%m-%d}/"
            f"users-{now:%H-%M-%S-%f}-{request_id}.json"
        )

        json_bytes = json.dumps(
            items, indent=2, ensure_ascii=False, default=json_serializer
        ).encode("utf-8")
        s3.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=json_bytes,
            ContentType="application/json",
        )
        s3_uri = f"s3://{bucket_name}/{object_key}"
        print(f"SUCCESS: Exported {len(items)} users to {s3_uri}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "exported_count": len(items),
                "s3_uri": s3_uri,
                "scan_pages": pages,
            }),
        }

    except Exception as exc:
        print(f"ERROR: Export failed: {exc}")
        raise
