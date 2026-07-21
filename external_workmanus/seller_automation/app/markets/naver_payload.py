"""
네이버 커머스 API 상품등록 payload 빌더.
캄파(OSSA) ProdCU_Payload_Create 분석 기반으로, 우리 NormalizedProduct -> 네이버 originProduct 변환.

식품 카테고리 필수 사항:
- productInfoProvidedNotice (상품정보제공고시) : 가공식품/농수산물 타입
- originAreaInfo (원산지)

이미지는 representativeImage.url 에 '네이버에 업로드된 URL'이 들어가야 하므로
naver_client.upload_image() 로 먼저 올린 결과 URL을 주입하는 구조.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class NaverProductInput:
    """payload 빌더 입력 (가공 완료된 값)."""
    name: str
    leaf_category_id: str
    sale_price: int
    stock_quantity: int
    representative_image_url: str            # 네이버 업로드 후 URL
    optional_image_urls: List[str] = field(default_factory=list)
    detail_content_html: str = ""
    origin: str = "기타 (상세설명 참조)"
    # 상품정보제공고시 (식품 기본 템플릿)
    notice_type: str = "FOOD"                # FOOD / PROCESSED_FOOD 등
    notice_fields: Dict[str, str] = field(default_factory=dict)
    # 옵션 (단순/조합형)
    option_combinations: List[Dict[str, Any]] = field(default_factory=list)
    # 배송
    delivery_fee: int = 0                    # 0이면 무료
    seller_product_code: str = ""            # 판매자상품코드(원본 매핑용)
    after_service_phone: str = ""
    after_service_guide: str = "상품 문의는 스토어 톡톡으로 부탁드립니다."
    minor_purchasable: bool = True


def _origin_area_info(origin: str) -> Dict[str, Any]:
    """원산지 정보. 국내산 식품 기본 처리."""
    text = origin or ""
    if any(k in text for k in ["국내", "대한민국", "한국"]):
        return {"originAreaCode": "00", "content": "국내산", "plural": False, "importer": ""}
    # 그 외에는 '기타'로 두고 상세 표기
    return {"originAreaCode": "04", "content": text or "상세설명 참조", "plural": False, "importer": ""}


def _product_info_notice(name: str, ni: NaverProductInput) -> Dict[str, Any]:
    """상품정보제공고시. 가공식품 기본 템플릿(미입력시 '상세페이지 참조')."""
    f = ni.notice_fields or {}
    default = "상세페이지 참조"
    # 네이버 가공식품(FOOD) 고시 표준 필드
    return {
        "productInfoProvidedNoticeType": ni.notice_type,
        "foodType": {
            "productName": f.get("productName", name),
            "foodType": f.get("foodType", default),
            "producerAndLocation": f.get("producerAndLocation", _origin_area_info(ni.origin)["content"]),
            "manufactureDate": f.get("manufactureDate", default),
            "shelfLifeOrUseByDate": f.get("shelfLifeOrUseByDate", default),
            "capacityAndQuantityAndWeight": f.get("capacityAndQuantityAndWeight", default),
            "ingredientsAndContent": f.get("ingredientsAndContent", default),
            "nutritionFacts": f.get("nutritionFacts", default),
            "geneticallyModified": f.get("geneticallyModified", default),
            "precautionWhenEatingOrCooking": f.get("precautionWhenEatingOrCooking", default),
            "importDeclaration": f.get("importDeclaration", "해당사항 없음"),
            "customerServicePhoneNumber": f.get(
                "customerServicePhoneNumber", ni.after_service_phone or default),
        },
    }


def build_origin_product(ni: NaverProductInput) -> Dict[str, Any]:
    """originProduct 본문 생성."""
    images: Dict[str, Any] = {
        "representativeImage": {"url": ni.representative_image_url},
    }
    if ni.optional_image_urls:
        images["optionalImages"] = [{"url": u} for u in ni.optional_image_urls[:9]]

    detail_attribute: Dict[str, Any] = {
        "naverShoppingSearchInfo": {
            "manufacturerName": "",
            "brandName": "",
        },
        "afterServiceInfo": {
            "afterServiceTelephoneNumber": ni.after_service_phone or "0000000000",
            "afterServiceGuideContent": ni.after_service_guide,
        },
        "originAreaInfo": _origin_area_info(ni.origin),
        "productInfoProvidedNotice": _product_info_notice(ni.name, ni),
        "minorPurchasable": ni.minor_purchasable,
        "seoInfo": {
            "sellerTags": [],
        },
    }

    # 옵션 (조합형) - 있으면 추가
    if ni.option_combinations:
        detail_attribute["optionInfo"] = {
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": {
                "optionGroupName1": "선택",
            },
            "optionCombinations": ni.option_combinations,
        }

    origin_product: Dict[str, Any] = {
        "statusType": "SALE",
        "saleType": "NEW",
        "leafCategoryId": str(ni.leaf_category_id),
        "name": ni.name,
        "detailContent": ni.detail_content_html or f"<div>{ni.name}</div>",
        "images": images,
        "salePrice": int(ni.sale_price),
        "stockQuantity": int(ni.stock_quantity),
        "deliveryInfo": {
            "deliveryType": "DELIVERY",
            "deliveryAttributeType": "NORMAL",
            "deliveryCompany": "CJGLS",
            "deliveryFee": {
                "deliveryFeeType": "FREE" if ni.delivery_fee == 0 else "PAID",
                "baseFee": int(ni.delivery_fee),
            },
            "claimDeliveryInfo": {
                "returnDeliveryFee": 3000,
                "exchangeDeliveryFee": 6000,
            },
        },
        "detailAttribute": detail_attribute,
    }
    if ni.seller_product_code:
        origin_product["sellerManagementCode"] = ni.seller_product_code
    return origin_product


def build_product_payload(ni: NaverProductInput) -> Dict[str, Any]:
    """네이버 상품등록 최종 payload."""
    return {
        "originProduct": build_origin_product(ni),
        "smartstoreChannelProduct": {
            "naverShoppingRegistration": True,
            "channelProductDisplayStatusType": "ON",
        },
    }
