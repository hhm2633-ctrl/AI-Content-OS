from typing import Any, Dict, Optional

from modules.audit_engine.audit_storage import AuditStorage


class AuditInterface(object):
    """
    Content Audit Engine - Interface.

    다른 Engine(향후 Audit Engine 문서의 Competitor Comparison 등)이 최신 감사
    결과와 누적 통계를 조회할 수 있는 읽기 전용 API. 실패 시 빈 dict를 반환한다.
    """

    def __init__(self, storage: Optional[AuditStorage] = None):
        self.storage = storage or AuditStorage()

    def get_latest(self) -> Dict[str, Any]:
        try:
            return self.storage.load_latest()
        except Exception as error:
            print(f"Audit Interface get_latest Failed: {error}")
            return {}

    def get_statistics(self) -> Dict[str, Any]:
        try:
            return self.storage.load_statistics()
        except Exception as error:
            print(f"Audit Interface get_statistics Failed: {error}")
            return {}
