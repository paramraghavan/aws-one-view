# s3_etl_library.py
"""
Enhanced S3 ETL Library with detailed logging and processing capabilities
"""

import boto3
import logging
import os
import hashlib
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional, Tuple
import mimetypes
import json
from pathlib import Path


class S3ETLProcessor:
    """
    Enhanced S3 processor with detailed ETL logging and file processing capabilities
    """

    def __init__(self, region_name: str = 'us-east-1', logger: Optional[logging.Logger] = None):
        """
        Initialize the S3 ETL Processor

        Args:
            region_name: AWS region name
            logger: Custom logger instance
        """
        self.region_name = region_name
        self.logger = logger or self._setup_logger()
        self.s3_client = None
        self._initialize_s3_client()

    def _setup_logger(self) -> logging.Logger:
        """Set up default logger"""
        logger = logging.getLogger('S3ETL')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _initialize_s3_client(self):
        """Initialize S3 client with error handling"""
        try:
            self.s3_client = boto3.client('s3', region_name=self.region_name)
            self.logger.info(f"S3 client initialized successfully for region: {self.region_name}")
        except NoCredentialsError:
            self.logger.error("AWS credentials not found. Please configure your credentials.")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            raise

    def calculate_file_hash(self, file_path: str, algorithm: str = 'md5') -> str:
        """
        Calculate file hash for integrity verification

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm (md5, sha256, etc.)

        Returns:
            Hexadecimal hash string
        """
        self.logger.info(f"Calculating {algorithm.upper()} hash for: {file_path}")

        hash_obj = hashlib.new(algorithm)

        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)

            file_hash = hash_obj.hexdigest()
            self.logger.info(f"File hash calculated: {file_hash}")
            return file_hash

        except Exception as e:
            self.logger.error(f"Error calculating file hash: {e}")
            raise

    def get_file_metadata(self, file_path: str) -> Dict:
        """
        Extract comprehensive file metadata

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing file metadata
        """
        self.logger.info(f"Extracting metadata for: {file_path}")

        try:
            file_stat = os.stat(file_path)
            path_obj = Path(file_path)

            metadata = {
                'filename': path_obj.name,
                'size_bytes': file_stat.st_size,
                'size_human': self._format_bytes(file_stat.st_size),
                'extension': path_obj.suffix.lower(),
                'mime_type': mimetypes.guess_type(file_path)[0] or 'application/octet-stream',
                'created_time': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'md5_hash': self.calculate_file_hash(file_path, 'md5'),
                'sha256_hash': self.calculate_file_hash(file_path, 'sha256')
            }

            self.logger.info(f"Metadata extracted: {metadata['filename']} ({metadata['size_human']})")
            return metadata

        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
            raise

    def validate_bucket_access(self, bucket_name: str) -> bool:
        """
        Validate bucket exists and is accessible

        Args:
            bucket_name: S3 bucket name

        Returns:
            True if bucket is accessible, False otherwise
        """
        self.logger.info(f"Validating access to bucket: {bucket_name}")

        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            self.logger.info(f"Bucket access validated: {bucket_name}")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self.logger.error(f"Bucket not found: {bucket_name}")
            elif error_code == '403':
                self.logger.error(f"Access denied to bucket: {bucket_name}")
            else:
                self.logger.error(f"Error accessing bucket {bucket_name}: {e}")
            return False

        except Exception as e:
            self.logger.error(f"Unexpected error validating bucket access: {e}")
            return False

    def check_object_exists(self, bucket_name: str, key: str) -> bool:
        """
        Check if object already exists in S3

        Args:
            bucket_name: S3 bucket name
            key: S3 object key

        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=bucket_name, Key=key)
            self.logger.info(f"Object exists: s3://{bucket_name}/{key}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.logger.info(f"Object does not exist: s3://{bucket_name}/{key}")
                return False
            else:
                self.logger.error(f"Error checking object existence: {e}")
                raise

    def upload_file_with_etl(self,
                             file_path: str,
                             bucket_name: str,
                             key: str = None,
                             overwrite: bool = False,
                             storage_class: str = 'STANDARD',
                             metadata: Dict = None,
                             tags: Dict = None) -> Dict:
        """
        Upload file to S3 with comprehensive ETL processing and logging

        Args:
            file_path: Local file path
            bucket_name: S3 bucket name
            key: S3 object key (defaults to filename)
            overwrite: Whether to overwrite existing objects
            storage_class: S3 storage class
            metadata: Additional metadata to attach
            tags: Tags to apply to the object

        Returns:
            Dictionary with upload results and metadata
        """

        # ETL Phase 1: Extract - File Analysis
        self.logger.info("=" * 60)
        self.logger.info("STARTING ETL PROCESS: EXTRACT PHASE")
        self.logger.info("=" * 60)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate key if not provided
        if not key:
            key = os.path.basename(file_path)
            self.logger.info(f"Generated S3 key: {key}")

        # Extract file metadata
        file_metadata = self.get_file_metadata(file_path)
        self.logger.info(f"File analysis complete: {file_metadata['filename']}")

        # ETL Phase 2: Transform - Preparation and Validation
        self.logger.info("=" * 60)
        self.logger.info("STARTING ETL PROCESS: TRANSFORM PHASE")
        self.logger.info("=" * 60)

        # Validate bucket access
        if not self.validate_bucket_access(bucket_name):
            raise Exception(f"Cannot access bucket: {bucket_name}")

        # Check if object exists
        object_exists = self.check_object_exists(bucket_name, key)
        if object_exists and not overwrite:
            self.logger.warning(f"Object already exists and overwrite=False: s3://{bucket_name}/{key}")
            return {
                'success': False,
                'reason': 'Object exists and overwrite not allowed',
                'metadata': file_metadata
            }

        # Prepare upload parameters
        upload_params = {
            'Bucket': bucket_name,
            'Key': key,
            'StorageClass': storage_class,
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'original-filename': file_metadata['filename'],
                'upload-timestamp': datetime.now().isoformat(),
                'file-size': str(file_metadata['size_bytes']),
                'md5-hash': file_metadata['md5_hash'],
                'sha256-hash': file_metadata['sha256_hash'],
                'mime-type': file_metadata['mime_type']
            }
        }

        # Add custom metadata if provided
        if metadata:
            upload_params['Metadata'].update(metadata)
            self.logger.info(f"Added custom metadata: {metadata}")

        # Add content type
        upload_params['ContentType'] = file_metadata['mime_type']

        self.logger.info(f"Upload parameters prepared for: s3://{bucket_name}/{key}")
        self.logger.info(f"Storage class: {storage_class}")
        self.logger.info(f"File size: {file_metadata['size_human']}")

        # ETL Phase 3: Load - Upload to S3
        self.logger.info("=" * 60)
        self.logger.info("STARTING ETL PROCESS: LOAD PHASE")
        self.logger.info("=" * 60)

        try:
            # Perform the upload
            self.logger.info(f"Beginning upload: {file_path} -> s3://{bucket_name}/{key}")
            upload_start = datetime.now()

            with open(file_path, 'rb') as f:
                self.s3_client.put_object(Body=f, **upload_params)

            upload_end = datetime.now()
            upload_duration = (upload_end - upload_start).total_seconds()

            # Calculate upload speed
            upload_speed = file_metadata['size_bytes'] / upload_duration if upload_duration > 0 else 0
            speed_human = self._format_bytes(upload_speed) + "/s"

            self.logger.info(f"Upload completed successfully in {upload_duration:.2f} seconds")
            self.logger.info(f"Upload speed: {speed_human}")

            # Apply tags if provided
            if tags:
                self._apply_object_tags(bucket_name, key, tags)

            # Verify upload integrity
            self.logger.info("Verifying upload integrity...")
            if self._verify_upload_integrity(bucket_name, key, file_metadata):
                self.logger.info("Upload integrity verification: PASSED")
            else:
                self.logger.warning("Upload integrity verification: FAILED")

            # Final ETL summary
            self.logger.info("=" * 60)
            self.logger.info("ETL PROCESS COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 60)
            self.logger.info(f"Source: {file_path}")
            self.logger.info(f"Destination: s3://{bucket_name}/{key}")
            self.logger.info(f"Size: {file_metadata['size_human']}")
            self.logger.info(f"Duration: {upload_duration:.2f} seconds")
            self.logger.info(f"Speed: {speed_human}")
            self.logger.info("=" * 60)

            return {
                'success': True,
                'bucket': bucket_name,
                'key': key,
                'metadata': file_metadata,
                'upload_duration': upload_duration,
                'upload_speed': upload_speed,
                'upload_speed_human': speed_human,
                's3_url': f"s3://{bucket_name}/{key}"
            }

        except ClientError as e:
            self.logger.error(f"AWS S3 error during upload: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e}")
            raise

    def _apply_object_tags(self, bucket_name: str, key: str, tags: Dict):
        """Apply tags to S3 object"""
        try:
            tag_set = [{'Key': k, 'Value': str(v)} for k, v in tags.items()]
            self.s3_client.put_object_tagging(
                Bucket=bucket_name,
                Key=key,
                Tagging={'TagSet': tag_set}
            )
            self.logger.info(f"Applied tags to s3://{bucket_name}/{key}: {tags}")
        except Exception as e:
            self.logger.error(f"Error applying tags: {e}")

    def _verify_upload_integrity(self, bucket_name: str, key: str, file_metadata: Dict) -> bool:
        """Verify upload integrity by comparing metadata"""
        try:
            response = self.s3_client.head_object(Bucket=bucket_name, Key=key)

            # Check file size
            s3_size = response['ContentLength']
            local_size = file_metadata['size_bytes']

            if s3_size != local_size:
                self.logger.error(f"Size mismatch: S3={s3_size}, Local={local_size}")
                return False

            # Check ETag (MD5 for simple uploads)
            s3_etag = response['ETag'].strip('"')
            local_md5 = file_metadata['md5_hash']

            if s3_etag != local_md5:
                self.logger.warning(f"ETag mismatch: S3={s3_etag}, Local={local_md5}")
                # Note: ETag may not match MD5 for multipart uploads

            return True

        except Exception as e:
            self.logger.error(f"Error verifying upload integrity: {e}")
            return False

    def _format_bytes(self, bytes_count: float, decimals: int = 2) -> str:
        """Format bytes to human readable string"""
        if bytes_count == 0:
            return "0 B"

        k = 1024
        sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        i = int(abs(bytes_count) // k) if bytes_count >= k else 0
        i = min(i, len(sizes) - 1)

        return f"{bytes_count / (k ** i):.{decimals}f} {sizes[i]}"

    def batch_upload(self, file_list: List[str], bucket_name: str,
                     prefix: str = "", **upload_kwargs) -> List[Dict]:
        """
        Upload multiple files with detailed ETL processing

        Args:
            file_list: List of file paths to upload
            bucket_name: S3 bucket name
            prefix: S3 key prefix for all files
            **upload_kwargs: Additional arguments for upload_file_with_etl

        Returns:
            List of upload results
        """
        self.logger.info(f"Starting batch upload of {len(file_list)} files to s3://{bucket_name}")

        results = []
        successful_uploads = 0
        failed_uploads = 0

        for i, file_path in enumerate(file_list, 1):
            self.logger.info(f"Processing file {i}/{len(file_list)}: {os.path.basename(file_path)}")

            try:
                # Generate S3 key with prefix
                filename = os.path.basename(file_path)
                key = f"{prefix.rstrip('/')}/{filename}" if prefix else filename

                result = self.upload_file_with_etl(
                    file_path=file_path,
                    bucket_name=bucket_name,
                    key=key,
                    **upload_kwargs
                )

                if result['success']:
                    successful_uploads += 1
                else:
                    failed_uploads += 1

                results.append(result)

            except Exception as e:
                self.logger.error(f"Failed to upload {file_path}: {e}")
                failed_uploads += 1
                results.append({
                    'success': False,
                    'file_path': file_path,
                    'error': str(e)
                })

        # Batch upload summary
        self.logger.info("=" * 60)
        self.logger.info("BATCH UPLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total files: {len(file_list)}")
        self.logger.info(f"Successful uploads: {successful_uploads}")
        self.logger.info(f"Failed uploads: {failed_uploads}")
        self.logger.info(f"Success rate: {(successful_uploads / len(file_list) * 100):.1f}%")
        self.logger.info("=" * 60)

        return results


# Example usage and integration with Flask app
def integrate_with_flask_app(file_paths: List[str], bucket_name: str, logger=None):
    """
    Example function showing how to integrate the S3 ETL library with the Flask app
    """
    processor = S3ETLProcessor(logger=logger)

    # Process each file with detailed ETL logging
    results = []
    for file_path in file_paths:
        try:
            result = processor.upload_file_with_etl(
                file_path=file_path,
                bucket_name=bucket_name,
                storage_class='STANDARD',
                tags={
                    'uploaded-by': 'flask-app',
                    'environment': 'production',
                    'department': 'data-engineering'
                },
                metadata={
                    'uploaded-via': 'web-interface',
                    'user-agent': 'flask-s3-manager'
                }
            )
            results.append(result)

        except Exception as e:
            logger.error(f"ETL process failed for {file_path}: {e}")
            results.append({
                'success': False,
                'file_path': file_path,
                'error': str(e)
            })

    return results


if __name__ == "__main__":
    # Example usage
    processor = S3ETLProcessor()

    # Single file upload
    result = processor.upload_file_with_etl(
        file_path="sample_data.csv",
        bucket_name="my-data-bucket",
        key="processed/sample_data_20231201.csv",
        storage_class="STANDARD_IA",
        tags={'project': 'data-migration', 'team': 'analytics'},
        metadata={'processed-by': 'etl-pipeline'}
    )

    print(json.dumps(result, indent=2))