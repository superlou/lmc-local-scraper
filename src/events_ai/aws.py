import os
from pathlib import Path

import boto3


class AWS:
    def __init__(self):
        self.session = boto3.Session(
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name=os.environ["AWS_REGION"],
        )

    def upload_to_s3(self, source: Path, bucket: str, dest: str):
        s3_client = self.session.client("s3")

        extra_args = {"ACL": "public-read"}

        match source.suffix.lower():
            case ".json":
                extra_args["ContentType"] = "application/json"
            case ".jpg" | ".jpeg":
                extra_args["ContentType"] = "image/jpeg"
            case ".png":
                extra_args["ContentType"] = "image/png"
            case ".gif":
                extra_args["ContentType"] = "image/gif"

        s3_client.upload_file(source, bucket, dest, ExtraArgs=extra_args)
