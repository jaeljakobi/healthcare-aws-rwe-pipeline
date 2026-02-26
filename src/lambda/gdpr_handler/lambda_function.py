import json
import boto3
import re
from datetime import datetime

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    GDPR Compliance Handler
    - Scans files for PII (email, SSN, phone, credit cards)
    - Tags files requiring pseudonymization
    """
    
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    size = event['Records'][0]['s3']['object']['size']
    
    print(f"🔐 GDPR check: {key}")
    
    # Skip large files
    if size > 10 * 1024 * 1024:
        return {
            'statusCode': 200,
            'message': 'File too large, skipped'
        }
    
    # Read file
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8', errors='ignore')
    except Exception as e:
        return {'statusCode': 500, 'error': str(e)}
    
    # PII patterns
    pii_patterns = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    }
    
    # Scan for PII
    pii_found = []
    total_count = 0
    
    for pii_type, pattern in pii_patterns.items():
        matches = re.findall(pattern, content[:50000])
        if matches:
            count = len(matches)
            total_count += count
            pii_found.append({
                'type': pii_type,
                'count': count
            })
            print(f"⚠️  Found {count} {pii_type}")
    
    # Determine status
    if total_count > 0:
        status = 'NON_COMPLIANT'
        action = 'PSEUDONYMIZATION_REQUIRED'
    else:
        status = 'COMPLIANT'
        action = 'NONE'
    
    # Tag S3 object
    try:
        s3.put_object_tagging(
            Bucket=bucket,
            Key=key,
            Tagging={
                'TagSet': [
                    {'Key': 'GDPRStatus', 'Value': status},
                    {'Key': 'ActionRequired', 'Value': action},
                    {'Key': 'PIICount', 'Value': str(total_count)},
                    {'Key': 'CheckedAt', 'Value': datetime.utcnow().isoformat()}
                ]
            }
        )
    except Exception as e:
        print(f"⚠️  Could not tag: {str(e)}")
    
    return {
        'statusCode': 200,
        'gdpr_status': status,
        'pii_count': total_count,
        'pii_found': pii_found
    }