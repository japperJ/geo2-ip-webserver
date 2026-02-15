import logging
import uuid
from typing import Optional, List
from pathlib import Path
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class ContentFile:
    def __init__(self, key: str, filename: str, content_type: str, size: int, uploaded_at: datetime):
        self.key = key
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.uploaded_at = uploaded_at


class ContentService:
    def __init__(self):
        self.bucket = "site-content"

    async def upload_file(
        self,
        site_id: str,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> ContentFile:
        """Upload a file to site content storage."""
        try:
            import aiobotocore.session
            import aiobotocore.config
            
            session = aiobotocore.session.get_session()
            config = aiobotocore.config.AioConfig(
                signature_version='s3v4',
                retries={'max_attempts': 3}
            )
            
            # Generate unique key
            ext = Path(filename).suffix
            key = f"sites/{site_id}/{uuid.uuid4().hex}{ext}"
            
            async with session.create_client(
                's3',
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                config=config,
                use_ssl=settings.S3_SECURE,
            ) as client:
                # Ensure bucket exists
                try:
                    await client.head_bucket(Bucket=self.bucket)
                except:
                    await client.create_bucket(Bucket=self.bucket)
                
                # Upload
                await client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=file_data,
                    ContentType=content_type
                )
                
                logger.info(f"Uploaded file {filename} to {key}")
                
                return ContentFile(
                    key=key,
                    filename=filename,
                    content_type=content_type,
                    size=len(file_data),
                    uploaded_at=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Content upload failed: {e}")
            raise

    async def list_files(self, site_id: str) -> List[ContentFile]:
        """List all files for a site."""
        try:
            import aiobotocore.session
            import aiobotocore.config
            
            session = aiobotocore.session.get_session()
            config = aiobotocore.config.AioConfig(signature_version='s3v4')
            
            files = []
            
            async with session.create_client(
                's3',
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                config=config,
                use_ssl=settings.S3_SECURE,
            ) as client:
                try:
                    response = await client.list_objects_v2(
                        Bucket=self.bucket,
                        Prefix=f"sites/{site_id}/"
                    )
                    
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            key = obj['Key']
                            filename = key.split('/')[-1]
                            # Extract original filename if stored in metadata
                            files.append(ContentFile(
                                key=key,
                                filename=filename,
                                content_type=self._guess_content_type(filename),
                                size=obj['Size'],
                                uploaded_at=obj['LastModified']
                            ))
                            
                except Exception as e:
                    logger.warning(f"Could not list files: {e}")
                    
            return files
            
        except Exception as e:
            logger.error(f"Content list failed: {e}")
            return []

    async def get_file(self, site_id: str, filename: str) -> Optional[tuple[bytes, str]]:
        """Get a file from site content storage."""
        try:
            import aiobotocore.session
            import aiobotocore.config
            
            session = aiobotocore.session.get_session()
            config = aiobotocore.config.AioConfig(signature_version='s3v4')
            
            # Find the file by prefix
            prefix = f"sites/{site_id}/"
            
            async with session.create_client(
                's3',
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                config=config,
                use_ssl=settings.S3_SECURE,
            ) as client:
                # List objects to find matching file
                response = await client.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=prefix
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        fname = key.split('/')[-1]
                        # Match by filename (could be UUID-based internally)
                        if filename in key or fname == filename:
                            # Get the file
                            file_response = await client.get_object(
                                Bucket=self.bucket,
                                Key=key
                            )
                            async with file_response['Body'] as stream:
                                data = await stream.read()
                            
                            content_type = self._guess_content_type(key)
                            return data, content_type
                    
            return None
            
        except Exception as e:
            logger.error(f"Content download failed: {e}")
            return None

    async def delete_file(self, site_id: str, key: str) -> bool:
        """Delete a file from site content storage."""
        try:
            import aiobotocore.session
            import aiobotocore.config
            
            session = aiobotocore.session.get_session()
            config = aiobotocore.config.AioConfig(signature_version='s3v4')
            
            async with session.create_client(
                's3',
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                config=config,
                use_ssl=settings.S3_SECURE,
            ) as client:
                await client.delete_object(
                    Bucket=self.bucket,
                    Key=key
                )
                logger.info(f"Deleted file {key}")
                return True
                
        except Exception as e:
            logger.error(f"Content delete failed: {e}")
            return False

    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename."""
        ext = Path(filename).suffix.lower()
        types = {
            '.html': 'text/html',
            '.htm': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.xml': 'application/xml',
        }
        return types.get(ext, 'application/octet-stream')


content_service = ContentService()
