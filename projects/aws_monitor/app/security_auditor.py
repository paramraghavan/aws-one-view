"""
Security Audit Engine - Scan AWS resources for security vulnerabilities.
Checks for common security misconfigurations and compliance issues.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from app.aws_client import AWSClient
from app.config import Config

logger = logging.getLogger(__name__)


class SecurityAuditor:
    """
    Scan AWS resources for security vulnerabilities and compliance issues.
    """
    
    def __init__(self):
        """Initialize the security auditor."""
        self.aws_client = AWSClient()
    
    def audit_all(self, regions: List[str]) -> Dict[str, Any]:
        """
        Run comprehensive security audit across all regions.
        
        Args:
            regions: List of AWS regions to audit
        
        Returns:
            Dictionary with security findings and overall score
        """
        logger.info("Starting security audit")
        
        findings = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': [],
            'passed': [],
            'security_score': 0,
            'total_checks': 0,
            'passed_checks': 0,
            'audited_at': datetime.utcnow().isoformat()
        }
        
        for region in regions:
            try:
                logger.info(f"Auditing security in {region}")
                
                # Check security groups
                sg_findings = self._check_security_groups(region)
                self._categorize_findings(findings, sg_findings)
                
                # Check S3 buckets (global, but check once)
                if region == regions[0]:
                    s3_findings = self._check_s3_buckets()
                    self._categorize_findings(findings, s3_findings)
                
                # Check EBS encryption
                ebs_findings = self._check_ebs_encryption(region)
                self._categorize_findings(findings, ebs_findings)
                
                # Check RDS public accessibility
                rds_findings = self._check_rds_public_access(region)
                self._categorize_findings(findings, rds_findings)
                
                # Check IAM (global, but check once)
                if region == regions[0]:
                    iam_findings = self._check_iam_security()
                    self._categorize_findings(findings, iam_findings)
                
                # Check CloudTrail
                if region == regions[0]:
                    cloudtrail_findings = self._check_cloudtrail()
                    self._categorize_findings(findings, cloudtrail_findings)
                
            except Exception as e:
                logger.error(f"Error auditing {region}: {e}")
        
        # Calculate security score (0-100)
        total_checks = findings['total_checks']
        passed_checks = findings['passed_checks']
        
        if total_checks > 0:
            findings['security_score'] = round((passed_checks / total_checks) * 100)
        else:
            findings['security_score'] = 0
        
        logger.info(f"Security audit complete. Score: {findings['security_score']}/100")
        
        return findings
    
    def _categorize_findings(self, findings: Dict, new_findings: List[Dict]):
        """Categorize findings by severity and update totals."""
        for finding in new_findings:
            severity = finding.get('severity', 'low')
            findings['total_checks'] += 1
            
            if finding.get('passed', False):
                findings['passed'].append(finding)
                findings['passed_checks'] += 1
            else:
                findings[severity].append(finding)
    
    def _check_security_groups(self, region: str) -> List[Dict[str, Any]]:
        """Check for overly permissive security groups."""
        findings = []
        
        try:
            ec2 = self.aws_client.session.client('ec2', region_name=region)
            
            response = ec2.describe_security_groups()
            
            for sg in response['SecurityGroups']:
                sg_id = sg['GroupId']
                sg_name = sg['GroupName']
                
                # Check ingress rules
                for rule in sg.get('IpPermissions', []):
                    from_port = rule.get('FromPort', 0)
                    to_port = rule.get('ToPort', 65535)
                    
                    # Check for 0.0.0.0/0 (all IPs)
                    for ip_range in rule.get('IpRanges', []):
                        cidr = ip_range.get('CidrIp', '')
                        
                        if cidr == '0.0.0.0/0':
                            # SSH (22)
                            if from_port <= 22 <= to_port:
                                findings.append({
                                    'resource_id': sg_id,
                                    'resource_name': sg_name,
                                    'resource_type': 'security_group',
                                    'region': region,
                                    'severity': 'critical',
                                    'issue': 'SSH port 22 open to internet (0.0.0.0/0)',
                                    'recommendation': 'Restrict SSH access to specific IP addresses',
                                    'remediation': f'Modify security group {sg_id} to limit SSH access',
                                    'category': 'network_security'
                                })
                            
                            # RDP (3389)
                            if from_port <= 3389 <= to_port:
                                findings.append({
                                    'resource_id': sg_id,
                                    'resource_name': sg_name,
                                    'resource_type': 'security_group',
                                    'region': region,
                                    'severity': 'critical',
                                    'issue': 'RDP port 3389 open to internet (0.0.0.0/0)',
                                    'recommendation': 'Restrict RDP access to specific IP addresses',
                                    'remediation': f'Modify security group {sg_id} to limit RDP access',
                                    'category': 'network_security'
                                })
                            
                            # All ports
                            if from_port == 0 and to_port == 65535:
                                findings.append({
                                    'resource_id': sg_id,
                                    'resource_name': sg_name,
                                    'resource_type': 'security_group',
                                    'region': region,
                                    'severity': 'critical',
                                    'issue': 'All ports open to internet (0.0.0.0/0)',
                                    'recommendation': 'Restrict access to only required ports',
                                    'remediation': f'Modify security group {sg_id} to limit port access',
                                    'category': 'network_security'
                                })
        
        except Exception as e:
            logger.error(f"Error checking security groups in {region}: {e}")
        
        return findings
    
    def _check_s3_buckets(self) -> List[Dict[str, Any]]:
        """Check for publicly accessible S3 buckets."""
        findings = []
        
        try:
            s3 = self.aws_client.session.client('s3')
            
            response = s3.list_buckets()
            
            for bucket in response['Buckets']:
                bucket_name = bucket['Name']
                
                try:
                    # Check bucket ACL
                    acl = s3.get_bucket_acl(Bucket=bucket_name)
                    
                    for grant in acl.get('Grants', []):
                        grantee = grant.get('Grantee', {})
                        permission = grant.get('Permission', '')
                        
                        # Check for public access
                        if grantee.get('Type') == 'Group':
                            uri = grantee.get('URI', '')
                            if 'AllUsers' in uri or 'AuthenticatedUsers' in uri:
                                findings.append({
                                    'resource_id': bucket_name,
                                    'resource_type': 's3_bucket',
                                    'region': 'global',
                                    'severity': 'critical',
                                    'issue': f'S3 bucket is publicly accessible ({permission})',
                                    'recommendation': 'Remove public access unless absolutely necessary',
                                    'remediation': f'Update bucket {bucket_name} ACL to remove public access',
                                    'category': 'data_security'
                                })
                                break
                    
                    # Check bucket policy for public access
                    try:
                        policy = s3.get_bucket_policy(Bucket=bucket_name)
                        policy_doc = policy.get('Policy', '')
                        
                        if '"Principal":"*"' in policy_doc or '"Principal":{"AWS":"*"}' in policy_doc:
                            findings.append({
                                'resource_id': bucket_name,
                                'resource_type': 's3_bucket',
                                'region': 'global',
                                'severity': 'high',
                                'issue': 'S3 bucket policy allows public access',
                                'recommendation': 'Review and restrict bucket policy',
                                'remediation': f'Update bucket {bucket_name} policy to remove public access',
                                'category': 'data_security'
                            })
                    
                    except s3.exceptions.from_code('NoSuchBucketPolicy'):
                        pass
                    
                    # Check encryption
                    try:
                        s3.get_bucket_encryption(Bucket=bucket_name)
                        # Encryption is enabled - good
                    except s3.exceptions.from_code('ServerSideEncryptionConfigurationNotFoundError'):
                        findings.append({
                            'resource_id': bucket_name,
                            'resource_type': 's3_bucket',
                            'region': 'global',
                            'severity': 'medium',
                            'issue': 'S3 bucket encryption not enabled',
                            'recommendation': 'Enable default encryption (AES-256 or KMS)',
                            'remediation': f'Enable encryption on bucket {bucket_name}',
                            'category': 'data_security'
                        })
                
                except Exception as e:
                    logger.debug(f"Error checking bucket {bucket_name}: {e}")
        
        except Exception as e:
            logger.error(f"Error checking S3 buckets: {e}")
        
        return findings
    
    def _check_ebs_encryption(self, region: str) -> List[Dict[str, Any]]:
        """Check for unencrypted EBS volumes."""
        findings = []
        
        try:
            ec2 = self.aws_client.session.client('ec2', region_name=region)
            
            response = ec2.describe_volumes()
            
            for volume in response['Volumes']:
                volume_id = volume['VolumeId']
                encrypted = volume.get('Encrypted', False)
                
                if not encrypted:
                    # Check if attached to instance
                    attached = len(volume.get('Attachments', [])) > 0
                    attached_to = volume['Attachments'][0]['InstanceId'] if attached else 'N/A'
                    
                    findings.append({
                        'resource_id': volume_id,
                        'resource_type': 'ebs_volume',
                        'region': region,
                        'severity': 'high' if attached else 'medium',
                        'issue': 'EBS volume is not encrypted',
                        'recommendation': 'Enable encryption for data at rest',
                        'remediation': f'Create encrypted snapshot and replace volume {volume_id}',
                        'attached_to': attached_to,
                        'category': 'data_security'
                    })
        
        except Exception as e:
            logger.error(f"Error checking EBS encryption in {region}: {e}")
        
        return findings
    
    def _check_rds_public_access(self, region: str) -> List[Dict[str, Any]]:
        """Check for publicly accessible RDS instances."""
        findings = []
        
        try:
            rds = self.aws_client.session.client('rds', region_name=region)
            
            response = rds.describe_db_instances()
            
            for db in response['DBInstances']:
                db_id = db['DBInstanceIdentifier']
                publicly_accessible = db.get('PubliclyAccessible', False)
                
                if publicly_accessible:
                    findings.append({
                        'resource_id': db_id,
                        'resource_type': 'rds_instance',
                        'region': region,
                        'severity': 'critical',
                        'issue': 'RDS database is publicly accessible',
                        'recommendation': 'Disable public access unless absolutely required',
                        'remediation': f'Modify RDS instance {db_id} to disable public accessibility',
                        'category': 'data_security'
                    })
                
                # Check encryption
                encrypted = db.get('StorageEncrypted', False)
                if not encrypted:
                    findings.append({
                        'resource_id': db_id,
                        'resource_type': 'rds_instance',
                        'region': region,
                        'severity': 'high',
                        'issue': 'RDS database storage not encrypted',
                        'recommendation': 'Enable storage encryption',
                        'remediation': f'Create encrypted snapshot and restore to new instance',
                        'category': 'data_security'
                    })
        
        except Exception as e:
            logger.error(f"Error checking RDS public access in {region}: {e}")
        
        return findings
    
    def _check_iam_security(self) -> List[Dict[str, Any]]:
        """Check IAM security settings."""
        findings = []
        
        try:
            iam = self.aws_client.session.client('iam')
            
            # Check for old access keys
            try:
                users = iam.list_users()
                
                for user in users['Users']:
                    username = user['UserName']
                    
                    # Get access keys
                    keys = iam.list_access_keys(UserName=username)
                    
                    for key in keys['AccessKeyMetadata']:
                        key_id = key['AccessKeyId']
                        create_date = key['CreateDate']
                        age_days = (datetime.now(create_date.tzinfo) - create_date).days
                        
                        if age_days > 90:
                            findings.append({
                                'resource_id': key_id,
                                'resource_type': 'iam_access_key',
                                'region': 'global',
                                'severity': 'medium',
                                'issue': f'Access key is {age_days} days old (recommended: rotate every 90 days)',
                                'recommendation': 'Rotate access keys regularly',
                                'remediation': f'Create new access key for user {username} and deactivate {key_id}',
                                'user': username,
                                'age_days': age_days,
                                'category': 'access_management'
                            })
            
            except Exception as e:
                logger.debug(f"Error checking IAM users: {e}")
            
            # Check password policy
            try:
                policy = iam.get_account_password_policy()
                pwd_policy = policy['PasswordPolicy']
                
                if not pwd_policy.get('RequireUppercaseCharacters', False):
                    findings.append({
                        'resource_type': 'iam_password_policy',
                        'region': 'global',
                        'severity': 'medium',
                        'issue': 'Password policy does not require uppercase characters',
                        'recommendation': 'Enable uppercase character requirement',
                        'remediation': 'Update account password policy',
                        'category': 'access_management'
                    })
                
                if not pwd_policy.get('RequireSymbols', False):
                    findings.append({
                        'resource_type': 'iam_password_policy',
                        'region': 'global',
                        'severity': 'medium',
                        'issue': 'Password policy does not require symbols',
                        'recommendation': 'Enable symbol requirement',
                        'remediation': 'Update account password policy',
                        'category': 'access_management'
                    })
                
                min_length = pwd_policy.get('MinimumPasswordLength', 0)
                if min_length < 14:
                    findings.append({
                        'resource_type': 'iam_password_policy',
                        'region': 'global',
                        'severity': 'low',
                        'issue': f'Minimum password length is {min_length} (recommended: 14+)',
                        'recommendation': 'Increase minimum password length to 14 characters',
                        'remediation': 'Update account password policy',
                        'category': 'access_management'
                    })
            
            except iam.exceptions.NoSuchEntityException:
                findings.append({
                    'resource_type': 'iam_password_policy',
                    'region': 'global',
                    'severity': 'high',
                    'issue': 'No password policy configured',
                    'recommendation': 'Create strong password policy',
                    'remediation': 'Configure account password policy with strong requirements',
                    'category': 'access_management'
                })
        
        except Exception as e:
            logger.error(f"Error checking IAM security: {e}")
        
        return findings
    
    def _check_cloudtrail(self) -> List[Dict[str, Any]]:
        """Check if CloudTrail is enabled."""
        findings = []
        
        try:
            cloudtrail = self.aws_client.session.client('cloudtrail')
            
            response = cloudtrail.describe_trails()
            
            if not response['trailList']:
                findings.append({
                    'resource_type': 'cloudtrail',
                    'region': 'global',
                    'severity': 'high',
                    'issue': 'CloudTrail is not enabled',
                    'recommendation': 'Enable CloudTrail for audit logging',
                    'remediation': 'Create CloudTrail trail with logging to S3',
                    'category': 'audit_logging'
                })
            else:
                # Check if trails are actually logging
                for trail in response['trailList']:
                    trail_name = trail['Name']
                    
                    status = cloudtrail.get_trail_status(Name=trail_name)
                    
                    if not status.get('IsLogging', False):
                        findings.append({
                            'resource_id': trail_name,
                            'resource_type': 'cloudtrail',
                            'region': 'global',
                            'severity': 'high',
                            'issue': f'CloudTrail {trail_name} is not actively logging',
                            'recommendation': 'Start CloudTrail logging',
                            'remediation': f'Enable logging for trail {trail_name}',
                            'category': 'audit_logging'
                        })
        
        except Exception as e:
            logger.error(f"Error checking CloudTrail: {e}")
        
        return findings


# Global auditor instance
security_auditor = SecurityAuditor()
