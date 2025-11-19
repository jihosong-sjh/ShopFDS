"""
이미지 업로드 유틸리티

S3/R2 또는 로컬 저장소에 이미지를 업로드합니다.
"""

import os
import uuid
from typing import Optional
from fastapi import UploadFile


async def upload_image(file: UploadFile, folder: str = "reviews") -> str:
    """
    이미지 업로드

    Args:
        file: 업로드할 파일
        folder: 저장 폴더 (기본값: "reviews")

    Returns:
        업로드된 이미지 URL

    Note:
        현재는 간단한 로컬 저장소 구현입니다.
        프로덕션에서는 S3/R2/CDN을 사용해야 합니다.
    """
    # 파일 확장자 추출
    file_extension = os.path.splitext(file.filename)[1]

    # 고유 파일명 생성
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"

    # 저장 경로 생성
    upload_dir = os.path.join("uploads", folder)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_filename)

    # 파일 저장
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # URL 반환 (실제로는 CDN URL을 반환해야 함)
    return f"/uploads/{folder}/{unique_filename}"


async def upload_multiple_images(
    files: list[UploadFile], folder: str = "reviews", max_count: int = 3
) -> list[str]:
    """
    여러 이미지 업로드

    Args:
        files: 업로드할 파일 목록
        folder: 저장 폴더
        max_count: 최대 업로드 개수

    Returns:
        업로드된 이미지 URL 목록

    Raises:
        ValueError: 최대 개수 초과
    """
    if len(files) > max_count:
        raise ValueError(f"이미지는 최대 {max_count}장까지 업로드할 수 있습니다")

    urls = []
    for file in files:
        url = await upload_image(file, folder)
        urls.append(url)

    return urls


def validate_image_file(file: UploadFile) -> bool:
    """
    이미지 파일 유효성 검증

    Args:
        file: 업로드할 파일

    Returns:
        유효 여부

    Note:
        MIME 타입과 파일 확장자를 검증합니다.
    """
    allowed_mime_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    allowed_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]

    # MIME 타입 검증
    if file.content_type not in allowed_mime_types:
        return False

    # 파일 확장자 검증
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        return False

    return True


def validate_image_size(file: UploadFile, max_size_mb: int = 5) -> bool:
    """
    이미지 파일 크기 검증

    Args:
        file: 업로드할 파일
        max_size_mb: 최대 파일 크기 (MB)

    Returns:
        유효 여부
    """
    # 파일 크기를 읽어서 확인 (단위: 바이트)
    max_size_bytes = max_size_mb * 1024 * 1024

    # FastAPI의 UploadFile은 파일 크기를 직접 제공하지 않으므로
    # 실제 구현에서는 파일을 읽으면서 크기를 확인해야 합니다.
    # 여기서는 간단한 구현만 제공합니다.

    return True  # 실제로는 파일 크기 검증 로직 구현 필요


# S3/R2 업로드 함수 (프로덕션용)
async def upload_to_s3(
    file: UploadFile, bucket: str, folder: str = "reviews"
) -> str:
    """
    S3/R2에 이미지 업로드 (구현 예정)

    Args:
        file: 업로드할 파일
        bucket: S3 버킷 이름
        folder: 저장 폴더

    Returns:
        S3 URL

    Note:
        boto3 라이브러리를 사용하여 구현합니다.
        환경 변수에서 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY를 읽어야 합니다.
    """
    # TODO: boto3를 사용한 S3 업로드 구현
    # import boto3
    # s3_client = boto3.client('s3')
    # ...

    raise NotImplementedError("S3 업로드 기능은 아직 구현되지 않았습니다")
