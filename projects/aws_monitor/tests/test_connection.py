#!/usr/bin/env python3
"""
Test AWS connection and permissions.
Run this before starting the application to verify setup.
"""

import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def test_connection():
    """Test AWS credentials and permissions."""
    
    print("=" * 50)
    print("AWS Connection Test")
    print("=" * 50)
    print()
    
    # Test credentials
    print("Testing credentials...")
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print("✓ Credentials OK")
        print(f"  Account: {identity['Account']}")
        print(f"  User ARN: {identity['Arn']}")
        print()
    except NoCredentialsError:
        print("✗ No AWS credentials found!")
        print()
        print("Configure credentials:")
        print("  1. Run: aws configure")
        print("  2. Or set: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Test permissions
    permissions = [
        ('EC2', lambda: boto3.client('ec2', region_name='us-east-1').describe_regions()),
        ('RDS', lambda: boto3.client('rds', region_name='us-east-1').describe_db_instances(MaxRecords=1)),
        ('S3', lambda: boto3.client('s3').list_buckets()),
        ('Lambda', lambda: boto3.client('lambda', region_name='us-east-1').list_functions(MaxItems=1)),
        ('CloudWatch', lambda: boto3.client('cloudwatch', region_name='us-east-1').list_metrics(MaxRecords=1)),
    ]
    
    print("Testing permissions...")
    all_ok = True
    
    for name, test_func in permissions:
        try:
            test_func()
            print(f"✓ {name:15s} OK")
        except ClientError as e:
            if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
                print(f"✗ {name:15s} Access Denied")
                all_ok = False
            else:
                print(f"⚠ {name:15s} {e.response['Error']['Code']}")
        except Exception as e:
            print(f"✗ {name:15s} Error: {e}")
            all_ok = False
    
    print()
    
    # Test Cost Explorer (optional)
    print("Testing Cost Explorer (optional)...")
    try:
        ce = boto3.client('ce', region_name='us-east-1')
        ce.get_cost_and_usage(
            TimePeriod={'Start': '2024-01-01', 'End': '2024-01-02'},
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )
        print("✓ Cost Explorer  OK")
    except Exception as e:
        print("⚠ Cost Explorer  Not available (this is optional)")
        print("  Enable in AWS Console: Billing → Cost Explorer")
    
    print()
    print("=" * 50)
    
    if all_ok:
        print("✓ All tests passed!")
        print()
        print("You're ready to run the application:")
        print("  ./run.sh")
        return True
    else:
        print("⚠ Some tests failed")
        print()
        print("Fix issues:")
        print("  1. Review docs/iam-policy.json")
        print("  2. Attach policy to your IAM user")
        print("  3. Run this test again")
        return False


if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)
