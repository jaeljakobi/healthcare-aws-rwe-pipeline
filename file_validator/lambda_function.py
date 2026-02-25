import json
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Validates files uploaded to S3 raw bucket
    - Checks file format (CSV, JSON)
    - Validates file size
    - Moves invalid files to quarantine
    """
    
    # Get bucket and file info from S3 event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    size = event['Records'][0]['s3']['object']['size']
    
    print(f"Processing file: {key} from bucket: {bucket}")
    print(f"File size: {size} bytes")
    
    # Validation results
    validation_results = {
        'file': key,
        'bucket': bucket,
        'timestamp': datetime.utcnow().isoformat(),
        'validations': []
    }
    
    # 1. Check file format
    if key.endswith('.csv'):
        validation_results['validations'].append({
            'check': 'format',
            'result': 'PASS',
            'format': 'CSV'
        })
    elif key.endswith('.json'):
        validation_results['validations'].append({
            'check': 'format',
            'result': 'PASS',
            'format': 'JSON'
        })
    else:
        validation_results['validations'].append({
            'check': 'format',
            'result': 'FAIL',
            'reason': 'Unknown format (not CSV or JSON)'
        })
        quarantine_file(bucket, key)
        return {
            'statusCode': 400,
            'body': json.dumps(validation_results)
        }
    
    # 2. Check file size (must be > 0 and < 100MB)
    if size == 0:
        validation_results['validations'].append({
            'check': 'size',
            'result': 'FAIL',
            'reason': 'Empty file'
        })
        quarantine_file(bucket, key)
        return {
            'statusCode': 400,
            'body': json.dumps(validation_results)
        }
    elif size > 100 * 1024 * 1024:
        validation_results['validations'].append({
            'check': 'size',
            'result': 'FAIL',
            'reason': 'File too large (>100MB)'
        })
        quarantine_file(bucket, key)
        return {
            'statusCode': 400,
            'body': json.dumps(validation_results)
        }
    else:
        validation_results['validations'].append({
            'check': 'size',
            'result': 'PASS',
            'size_mb': round(size / (1024 * 1024), 2)
        })
    
    # 3. Check if file is in correct folder
    if 'landing/' not in key:
        validation_results['validations'].append({
            'check': 'location',
            'result': 'FAIL',
            'reason': 'File not in landing/ folder'
        })
        quarantine_file(bucket, key)
        return {
            'statusCode': 400,
            'body': json.dumps(validation_results)
        }
    else:
        validation_results['validations'].append({
            'check': 'location',
            'result': 'PASS'
        })
    
    # All validations passed
    validation_results['overall_status'] = 'VALID'
    
    print(f"File validation PASSED: {key}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(validation_results)
    }


def quarantine_file(bucket, key):
    """Move invalid file to quarantine folder"""
    try:
        # Copy to quarantine
        copy_source = {'Bucket': bucket, 'Key': key}
        quarantine_key = key.replace('landing/', 'quarantine/')
        
        s3.copy_object(
            CopySource=copy_source,
            Bucket=bucket,
            Key=quarantine_key
        )
        
        # Delete from original location
        s3.delete_object(Bucket=bucket, Key=key)
        
        print(f"File moved to quarantine: {quarantine_key}")
    except Exception as e:
        print(f"Error quarantining file: {str(e)}")
