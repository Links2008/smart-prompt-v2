from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from enum import Enum, auto


class ErrorCode(Enum):
    """错误代码枚举"""
    # 网络与请求错误
    NETWORK_TIMEOUT = auto()
    NETWORK_CONNECTION_FAILED = auto()
    NETWORK_RATE_LIMITED = auto()
    NETWORK_PAGE_PRIVATE = auto()
    NETWORK_PAGE_STRUCTURE_CHANGED = auto()

    # 数据解析错误
    PARSE_MISSING_FIELD = auto()
    PARSE_INVALID_JSON = auto()
    PARSE_STRUCTURE_CHANGED = auto()
    PARSE_FAILED = auto()

    # 匹配失败错误
    MATCH_NO_COPYRIGHT = auto()
    MATCH_VERSION_MISMATCH = auto()
    MATCH_TRANSLATION_MISMATCH = auto()
    MATCH_INSUFFICIENT_SCORE = auto()
    MATCH_FAILED = auto()

    # Apple Music 授权错误
    APPLE_AUTH_FAILED = auto()
    APPLE_PERMISSION_DENIED = auto()
    APPLE_REGION_MISMATCH = auto()
    APPLE_RATE_LIMITED = auto()
    APPLE_API_ERROR = auto()

    # 批量写入错误
    BATCH_SIZE_EXCEEDED = auto()
    BATCH_SONG_INVALID = auto()
    BATCH_PARTIAL_FAILURE = auto()
    BATCH_NETWORK_INTERRUPTED = auto()

    # 系统性错误
    SYSTEM_OUT_OF_MEMORY = auto()
    SYSTEM_INTERNAL_ERROR = auto()
    SYSTEM_CORRUPTED_STATE = auto()


@dataclass
class ErrorResult:
    """统一错误结果结构"""
    success: bool
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    error_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"success": self.success}
        if self.error_code:
            result["error_code"] = self.error_code
        if self.error_msg:
            result["error_msg"] = self.error_msg
        if self.error_data:
            result["error_data"] = self.error_data
        return result

    @classmethod
    def success(cls, data: Optional[Dict[str, Any]] = None) -> "ErrorResult":
        return cls(success=True, error_data=data)

    @classmethod
    def failure(cls, error_code: ErrorCode, error_msg: str, error_data: Optional[Dict[str, Any]] = None) -> "ErrorResult":
        return cls(
            success=False,
            error_code=error_code.name.lower(),
            error_msg=error_msg,
            error_data=error_data
        )
