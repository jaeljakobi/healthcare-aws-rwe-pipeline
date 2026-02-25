import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Detects file format (CSV, JSON, or other) and tags S3 object
    """
    
    # Get file info from S3 event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    print(f"Detecting format for: {key}")
    
    # Detect format based on file extension
    if key.endswith('.csv'):
        format_type = 'CSV'
        mime_type = 'text/csv'
    elif key.endswith('.json'):
        format_type = 'JSON'
        mime_type = 'application/json'
    elif key.endswith('.xml'):
        format_type = 'XML'
        mime_type = 'application/xml'
    elif key.endswith('.parquet'):
        format_type = 'PARQUET'
        mime_type = 'application/octet-stream'
    else:
        format_type = 'UNKNOWN'
        mime_type = 'application/octet-stream'
    
    # Tag the S3 object with format type
    try:
        s3.put_object_tagging(
            Bucket=bucket,
            Key=key,
            Tagging={
                'TagSet': [
                    {'Key': 'DataFormat', 'Value': format_type},
                    {'Key': 'MimeType', 'Value': mime_type},
                    {'Key': 'ProcessingStatus', 'Value': 'PENDING'},
                    {'Key': 'DetectedAt', 'Value': datetime.utcnow().isoformat()}
                ]
            }
        )
        print(f"✅ Tagged file as {format_type}")
    except Exception as e:
        print(f"❌ Error tagging file: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }
    
    return {
        'statusCode': 200,
        'format': format_type,
        'mime_type': mime_type,
        'file': key,
        'bucket': bucket
    }
