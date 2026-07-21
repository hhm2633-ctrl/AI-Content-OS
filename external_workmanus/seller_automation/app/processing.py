"""
데이터 가공 모듈.
- 가격/마진 계산: 도매가(원가) → 판매가 (마진율, 배송비, 결제수수료, 100원단위 반올림 등)
- 상품명 가공: 말머리/말꼬리 추가, 금지어 제거, 공백 정리, 길이 제한
- 도매 상품이 국내 한국어이므로 번역은 기본 비활성(옵션으로 둠)

모든 규칙은 ProcessingConfig로 조정 가능하며, 최종 패키지에서 사용자가 UI로 설정.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import math
import re


@dataclass
class PricingConfig:
    margin_rate: float = 0.30          # 마진율 30%
    payment_fee_rate: float = 0.035    # 결제/판매 수수료 3.5%
    add_shipping_fee: int = 0          # 판매가에 포함할 배송비(묶음배송이면 0)
    extra_fixed: int = 0               # 고정 추가금(포장비 등)
    round_unit: int = 100              # 100원 단위 반올림
    round_mode: str = "ceil"           # ceil/round/floor
    min_price: int = 0                 # 최소 판매가 하한
    vat_included: bool = True          # 원가에 부가세 포함 여부(표시용)


@dataclass
class NamingConfig:
    prefix: str = ""                   # 말머리 (예: "[당일발송]")
    suffix: str = ""                   # 말꼬리 (예: "무료배송")
    banned_words: List[str] = field(default_factory=list)  # 금지어 제거
    max_length: int = 100              # 네이버 상품명 권장 길이
    collapse_spaces: bool = True
    remove_brackets_dup: bool = True   # 중복 대괄호 정리


def calc_sale_price(cost: int, cfg: PricingConfig) -> int:
    """원가(도매가) -> 판매가 계산."""
    if cost <= 0:
        return max(cfg.min_price, 0)
    # 마진 + 수수료를 역마진 방식으로 반영:
    #   판매가 = (원가 + 고정비 + 배송비) / (1 - 수수료율) * (1 + 마진율)
    base = cost + cfg.extra_fixed + cfg.add_shipping_fee
    denom = max(1e-6, (1.0 - cfg.payment_fee_rate))
    price = base / denom * (1.0 + cfg.margin_rate)

    unit = max(1, cfg.round_unit)
    if cfg.round_mode == "ceil":
        price = math.ceil(price / unit) * unit
    elif cfg.round_mode == "floor":
        price = math.floor(price / unit) * unit
    else:
        price = round(price / unit) * unit

    price = int(price)
    if cfg.min_price:
        price = max(price, cfg.min_price)
    return price


def process_name(title: str, cfg: NamingConfig) -> str:
    """상품명 가공."""
    name = title or ""

    # 금지어 제거
    for w in cfg.banned_words:
        if w:
            name = name.replace(w, "")

    # 중복 대괄호/공백 정리
    if cfg.remove_brackets_dup:
        name = re.sub(r"\[\s*\]", "", name)        # 빈 대괄호
        name = re.sub(r"\]\s*\[", "][", name)        # 대괄호 사이 공백

    if cfg.collapse_spaces:
        name = re.sub(r"\s+", " ", name).strip()

    # 말머리/말꼬리
    parts = []
    if cfg.prefix:
        parts.append(cfg.prefix.strip())
    parts.append(name)
    if cfg.suffix:
        parts.append(cfg.suffix.strip())
    name = " ".join(p for p in parts if p)

    # 길이 제한
    if cfg.max_length and len(name) > cfg.max_length:
        name = name[: cfg.max_length].rstrip()

    return name


@dataclass
class ProcessedResult:
    title: str
    sale_price: int
    cost_price: int


def process_product(title: str, cost_price: int,
                    pricing: PricingConfig, naming: NamingConfig) -> ProcessedResult:
    return ProcessedResult(
        title=process_name(title, naming),
        sale_price=calc_sale_price(cost_price, pricing),
        cost_price=cost_price,
    )
