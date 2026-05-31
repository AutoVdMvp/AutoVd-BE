"""
공통 API 응답 스키마 모듈

모든 API 응답에서 일관된 JSON 구조를 보장하기 위한
제네릭 래퍼 스키마를 정의합니다.

응답 예시:
    {
        "status": 200,
        "message": "데이터를 성공적으로 가져왔습니다.",
        "data": { ... }
    }
"""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

# data 필드에 들어갈 타입을 동적으로 지정하기 위한 TypeVar
T = TypeVar("T")


class CommonResponse(BaseModel, Generic[T]):
    """
    모든 API 엔드포인트에서 사용하는 공통 응답 래퍼 스키마.

    TypeVar T를 활용하여 data 필드의 타입을 엔드포인트별로 지정합니다.

    Attributes:
        status:  HTTP 상태 코드와 동일한 값 (200, 400, 500 등)
        message: 사람이 읽을 수 있는 처리 결과 메시지
        data:    실제 응답 데이터 (없을 경우 None)

    Usage:
        return CommonResponse(
            status=200,
            message="영상 생성을 시작했습니다.",
            data=RemakeVideoResponse(project_id="...", task_id="..."),
        )
    """

    status: int
    message: str
    data: Optional[T] = None
