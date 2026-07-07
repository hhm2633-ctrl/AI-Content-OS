from typing import Any, Dict, Optional


class BaseModule:
    """
    AI-Content-OS 모든 모듈의 공통 부모 클래스

    역할:
    - config 저장
    - module_name 저장
    - 공통 로그 출력
    - 모든 모듈의 기본 구조 통일
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.module_name = self.__class__.__name__

    def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.module_name}은 run() 메서드를 반드시 구현해야 합니다."
        )

    def log_start(self) -> None:
        print(f"{self.module_name} Started")

    def log_finish(self) -> None:
        print(f"{self.module_name} Finished")

    def log(self, message: str) -> None:
        print(f"[{self.module_name}] {message}")

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)