"""
관리자 상품 관리 API

관리자가 상품을 생성, 수정, 삭제하고 재고를 관리할 수 있는 API 엔드포인트
"""

from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from src.models.product import Product, ProductStatus
from src.models.base import get_db
from src.middleware.authorization import require_permission, Permission
from src.services.product_service import ProductService


router = APIRouter(prefix="/v1/admin/products", tags=["Admin - Products"])


# ===== Request/Response 스키마 =====


class ProductCreateRequest(BaseModel):
    """상품 생성 요청"""

    name: str = Field(..., min_length=1, max_length=255, description="상품명")
    description: Optional[str] = Field(None, description="상품 설명")
    price: Decimal = Field(..., gt=0, description="가격 (양수)")
    stock_quantity: int = Field(..., ge=0, description="재고 수량 (0 이상)")
    category: str = Field(..., min_length=1, max_length=100, description="카테고리")
    image_url: Optional[str] = Field(None, max_length=500, description="이미지 URL")
    status: ProductStatus = Field(
        default=ProductStatus.AVAILABLE, description="상품 상태"
    )

    @validator("price")
    def validate_price(cls, v):
        """가격이 너무 크지 않은지 검증"""
        if v > Decimal("99999999.99"):
            raise ValueError("가격은 99,999,999.99를 초과할 수 없습니다.")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "무선 이어폰",
                "description": "고음질 블루투스 무선 이어폰",
                "price": 89000,
                "stock_quantity": 100,
                "category": "전자기기",
                "image_url": "https://example.com/images/earphone.jpg",
                "status": "available",
            }
        }


class ProductUpdateRequest(BaseModel):
    """상품 수정 요청 (모든 필드 선택 사항)"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="상품명"
    )
    description: Optional[str] = Field(None, description="상품 설명")
    price: Optional[Decimal] = Field(None, gt=0, description="가격 (양수)")
    stock_quantity: Optional[int] = Field(None, ge=0, description="재고 수량 (0 이상)")
    category: Optional[str] = Field(
        None, min_length=1, max_length=100, description="카테고리"
    )
    image_url: Optional[str] = Field(None, max_length=500, description="이미지 URL")
    status: Optional[ProductStatus] = Field(None, description="상품 상태")

    @validator("price")
    def validate_price(cls, v):
        """가격이 너무 크지 않은지 검증"""
        if v is not None and v > Decimal("99999999.99"):
            raise ValueError("가격은 99,999,999.99를 초과할 수 없습니다.")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "무선 이어폰 Pro",
                "price": 129000,
                "stock_quantity": 50,
            }
        }


class StockUpdateRequest(BaseModel):
    """재고 수량 수정 요청"""

    stock_quantity: int = Field(..., ge=0, description="새로운 재고 수량 (0 이상)")

    class Config:
        json_schema_extra = {"example": {"stock_quantity": 150}}


class ProductResponse(BaseModel):
    """상품 응답"""

    id: str
    name: str
    description: Optional[str]
    price: Decimal
    stock_quantity: int
    category: str
    image_url: Optional[str]
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "무선 이어폰",
                "description": "고음질 블루투스 무선 이어폰",
                "price": "89000.00",
                "stock_quantity": 100,
                "category": "전자기기",
                "image_url": "https://example.com/images/earphone.jpg",
                "status": "available",
                "created_at": "2025-11-14T10:00:00",
                "updated_at": "2025-11-14T10:00:00",
            }
        }


# ===== API 엔드포인트 =====


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="상품 생성",
    description="관리자가 새로운 상품을 등록합니다.",
)
async def create_product(
    request: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission(Permission.PRODUCT_CREATE)),
):
    """
    새로운 상품을 생성합니다.

    **필요 권한**: PRODUCT_CREATE

    **입력**:
    - name: 상품명 (필수)
    - description: 상품 설명
    - price: 가격 (필수, 양수)
    - stock_quantity: 재고 수량 (필수, 0 이상)
    - category: 카테고리 (필수)
    - image_url: 이미지 URL
    - status: 상품 상태 (기본값: available)

    **반환**:
    - 생성된 상품 정보
    """
    # 새 상품 생성
    new_product = Product(
        name=request.name,
        description=request.description,
        price=request.price,
        stock_quantity=request.stock_quantity,
        category=request.category,
        image_url=request.image_url,
        status=request.status,
    )

    # 재고가 0이면 품절 상태로 자동 변경
    if new_product.stock_quantity == 0:
        new_product.status = ProductStatus.OUT_OF_STOCK

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    return ProductResponse(
        id=str(new_product.id),
        name=new_product.name,
        description=new_product.description,
        price=new_product.price,
        stock_quantity=new_product.stock_quantity,
        category=new_product.category,
        image_url=new_product.image_url,
        status=new_product.status.value,
        created_at=new_product.created_at.isoformat(),
        updated_at=new_product.updated_at.isoformat(),
    )


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="상품 수정",
    description="관리자가 기존 상품 정보를 수정합니다.",
)
async def update_product(
    product_id: str,
    request: ProductUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission(Permission.PRODUCT_UPDATE)),
):
    """
    기존 상품 정보를 수정합니다.

    **필요 권한**: PRODUCT_UPDATE

    **입력**:
    - 수정할 필드만 전송 (모든 필드 선택 사항)

    **반환**:
    - 수정된 상품 정보

    **에러**:
    - 404: 상품을 찾을 수 없음
    """
    # 상품 조회
    product_service = ProductService(db)
    product = await product_service.get_product_by_id(product_id)

    # 수정된 필드만 업데이트
    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(product, field, value)

    # 재고가 0이 되면 품절 상태로 자동 변경
    if product.stock_quantity == 0 and product.status == ProductStatus.AVAILABLE:
        product.status = ProductStatus.OUT_OF_STOCK
    # 재고가 다시 생기면 판매 가능 상태로 복원
    elif product.stock_quantity > 0 and product.status == ProductStatus.OUT_OF_STOCK:
        product.status = ProductStatus.AVAILABLE

    await db.commit()
    await db.refresh(product)

    return ProductResponse(
        id=str(product.id),
        name=product.name,
        description=product.description,
        price=product.price,
        stock_quantity=product.stock_quantity,
        category=product.category,
        image_url=product.image_url,
        status=product.status.value,
        created_at=product.created_at.isoformat(),
        updated_at=product.updated_at.isoformat(),
    )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="상품 삭제",
    description="관리자가 상품을 삭제합니다 (논리 삭제: DISCONTINUED 상태로 변경).",
)
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission(Permission.PRODUCT_DELETE)),
):
    """
    상품을 삭제합니다 (논리 삭제).

    **필요 권한**: PRODUCT_DELETE

    **동작**:
    - 실제로 데이터베이스에서 삭제하지 않고 상태를 DISCONTINUED로 변경
    - 이미 존재하는 주문의 무결성을 유지하기 위함

    **반환**:
    - 204 No Content

    **에러**:
    - 404: 상품을 찾을 수 없음
    """
    # 상품 조회
    product_service = ProductService(db)
    product = await product_service.get_product_by_id(product_id)

    # 논리 삭제: 상태를 DISCONTINUED로 변경
    product.status = ProductStatus.DISCONTINUED

    await db.commit()

    return None


@router.patch(
    "/{product_id}/stock",
    response_model=ProductResponse,
    summary="재고 수량 수정",
    description="관리자가 상품의 재고 수량을 직접 수정합니다.",
)
async def update_stock(
    product_id: str,
    request: StockUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission(Permission.PRODUCT_UPDATE)),
):
    """
    상품의 재고 수량을 수정합니다.

    **필요 권한**: PRODUCT_UPDATE

    **입력**:
    - stock_quantity: 새로운 재고 수량 (0 이상)

    **동작**:
    - 재고가 0이 되면 자동으로 OUT_OF_STOCK 상태로 변경
    - 재고가 다시 생기면 AVAILABLE 상태로 복원

    **반환**:
    - 수정된 상품 정보

    **에러**:
    - 404: 상품을 찾을 수 없음
    """
    # 상품 조회
    product_service = ProductService(db)
    product = await product_service.get_product_by_id(product_id)

    # 재고 수량 업데이트
    product.stock_quantity = request.stock_quantity

    # 재고가 0이 되면 품절 상태로 자동 변경
    if product.stock_quantity == 0 and product.status == ProductStatus.AVAILABLE:
        product.status = ProductStatus.OUT_OF_STOCK
    # 재고가 다시 생기면 판매 가능 상태로 복원 (중단된 상품 제외)
    elif product.stock_quantity > 0 and product.status == ProductStatus.OUT_OF_STOCK:
        product.status = ProductStatus.AVAILABLE

    await db.commit()
    await db.refresh(product)

    return ProductResponse(
        id=str(product.id),
        name=product.name,
        description=product.description,
        price=product.price,
        stock_quantity=product.stock_quantity,
        category=product.category,
        image_url=product.image_url,
        status=product.status.value,
        created_at=product.created_at.isoformat(),
        updated_at=product.updated_at.isoformat(),
    )
