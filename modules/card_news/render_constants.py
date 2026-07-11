from typing import Dict, Tuple

# CardNews Intelligence (Phase M8: Production Quality) - Renderer 상수 단일 진실
# 소스. card_news_module.py(실제 Pillow 렌더링)와 mobile_readability_checker.py
# (렌더링 결과 검증)가 각자 값을 복사해서 갖지 않고 이 모듈을 함께 참조한다 -
# 두 값이 서로 다른 복사본으로 몰래 어긋나는 것을 구조적으로 방지하기 위함이다.
# 여기 있는 숫자를 바꾸면 렌더링과 검사기 양쪽에 동시에 반영된다.

RENDERER_FONT_SIZES: Dict[str, int] = {"headline": 60, "body": 39, "small": 28, "brand": 26}
MIN_SAFE_FONT_SIZE = 24

BOX_MARGIN = 65
MIN_SAFE_MARGIN = 40

BOX_TOP_DEFAULT = 555
BOX_BOTTOM = 990

PALETTE_COMBINATIONS: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "dark": {
        "box_fill": (26, 26, 30),
        "headline_color": (245, 245, 245),
        "body_color": (210, 210, 210),
        "subtitle_color": (170, 170, 170),
    },
    "light": {
        "box_fill": (255, 255, 255),
        "headline_color": (18, 18, 18),
        "body_color": (45, 45, 45),
        # Phase M8 Contrast 수정: 기존 (120,120,120)은 흰 배경(255,255,255) 대비
        # 실측 대비비 4.42로 WCAG AA(4.5) 미달이었다. 큰 디자인 변경 없이 가장
        # 작은 수정으로 기준을 통과시키기 위해 (112,112,112)로 낮췄다
        # (실측 대비비 약 4.95) - 임계값을 낮추는 방식은 쓰지 않았다.
        "subtitle_color": (112, 112, 112),
    },
}

# WCAG AA 일반 텍스트 기준(4.5:1).
MIN_CONTRAST_RATIO = 4.5
