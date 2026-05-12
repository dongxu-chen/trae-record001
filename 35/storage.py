import os
import io
import uuid
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

class S3Storage:
    def __init__(self):
        self.bucket_name = os.getenv('AWS_S3_BUCKET', 'image-processing-bucket')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.endpoint_url = os.getenv('AWS_S3_ENDPOINT_URL')
        
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=self.region,
            endpoint_url=self.endpoint_url
        )

    def upload_file(self, file_data, filename, content_type='image/jpeg'):
        if not file_data:
            raise ValueError('File data is required')

        file_ext = os.path.splitext(filename)[1].lower() or '.jpg'
        key = f'processed/{uuid.uuid4()}{file_ext}'

        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type,
                ACL='public-read'
            )

            if self.endpoint_url:
                url = f'{self.endpoint_url}/{self.bucket_name}/{key}'
            else:
                url = f'https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}'

            return {
                'url': url,
                'key': key,
                'bucket': self.bucket_name
            }
        except ClientError as e:
            raise Exception(f'Failed to upload to S3: {str(e)}')

    def upload_image(self, image, format='JPEG', quality=85):
        buffer = io.BytesIO()
        image.save(buffer, format=format, quality=quality, optimize=True)
        buffer.seek(0)

        content_type = f'image/{format.lower()}'
        filename = f'image.{format.lower()}'

        return self.upload_file(buffer.getvalue(), filename, content_type)

    def delete_file(self, key):
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            raise Exception(f'Failed to delete from S3: {str(e)}')

    def get_file_url(self, key, expires_in=3600):
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            raise Exception(f'Failed to generate presigned URL: {str(e)}')

storage = S3Storage()
