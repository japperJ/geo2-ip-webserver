import logging
import uuid
import asyncio
from typing import Optional
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class ScreenshotService:
    def __init__(self):
        self.enabled = settings.SCREENSHOT_ENABLED

    async def capture_block_page(
        self,
        site_id: str,
        client_ip: str,
        reason: str,
        block_page_url: str,
    ) -> Optional[str]:
        """
        Capture a screenshot of the block page using Playwright.
        Returns the S3 key/path to the screenshot.
        """
        if not self.enabled:
            logger.info("Screenshot capture is disabled")
            return None

        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                # Navigate to the block page
                await page.goto(block_page_url)
                
                # Wait for page to load
                await page.wait_for_load_state("networkidle")
                
                # Generate filename
                filename = f"{site_id}_{client_ip}_{uuid.uuid4().hex[:8]}.png"
                
                # Take screenshot
                screenshot_dir = Path("/tmp/screenshots")
                screenshot_dir.mkdir(exist_ok=True)
                screenshot_path = screenshot_dir / filename
                
                await page.screenshot(path=str(screenshot_path))
                await browser.close()
                
                # Upload to S3
                s3_key = await self._upload_to_s3(screenshot_path, filename)
                
                # Clean up local file
                screenshot_path.unlink(missing_ok=True)
                
                return s3_key
                
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    async def _upload_to_s3(self, file_path: Path, filename: str) -> Optional[str]:
        """Upload screenshot to S3/MinIO."""
        try:
            import aiobotocore.session
            import aiobotocore.config
            
            session = aiobotocore.session.get_session()
            config = aiobotocore.config.AioConfig(
                signature_version='s3v4',
                retries={'max_attempts': 3}
            )
            
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
                    await client.head_bucket(Bucket=settings.S3_BUCKET)
                except:
                    await client.create_bucket(Bucket=settings.S3_BUCKET)
                
                # Upload
                with open(file_path, 'rb') as f:
                    await client.put_object(
                        Bucket=settings.S3_BUCKET,
                        Key=f"screenshots/{filename}",
                        Body=f.read(),
                        ContentType='image/png'
                    )
                
                return f"screenshots/{filename}"
                
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return None

    async def get_screenshot(self, s3_key: str) -> Optional[bytes]:
        """Retrieve screenshot from S3."""
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
                response = await client.get_object(
                    Bucket=settings.S3_BUCKET,
                    Key=s3_key
                )
                async with response['Body'] as stream:
                    return await stream.read()
                    
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return None


screenshot_service = ScreenshotService()
