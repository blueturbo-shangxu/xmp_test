import logging
import typing
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Any
from src.core.jwt_handler import JwtError


logger = logging.getLogger("")


class RespStatus(str, Enum):
    SUCCESS = "success"
    FAIL = "fail"


class Pager(BaseModel):
    total_count: int = Field(default=0, description="总条数", examples=[1200])
    total_page: int = Field(default=0, description="总页数", examples=[54])
    page_index: int = Field(default=0, description="当前页码", examples=[2])
    page_size: int = Field(default=0, description="分页大小", examples=[10])


class RespCode(int, Enum):
    SUCCESS = 0  # 成功

    # [通用] 通用错误
    FAIL = 10001  # 系统内部错误
    DATABASE_ERROR = 10002  # 数据库错误
    PARAM_ERROR = 10003  # 请求参数错误
    RECORD_NOT_FOUND = 10004  # 数据不存在

    # [通用] 通用错误:鉴权类
    AUTH_FAIL = 10101  # token失效,鉴权失败
    SHARE_AUTH_FAIL = 10102  # 分享链接鉴权失败

    # [用户] 用户类错误
    LOGIN_ERROR = 20001  # 登录失败

    # [APP] APP类错误
    APP_NOT_FOUND = 30001  # APP不存在
    APP_RUN_ERR_APP_BIND_ERR = 30002  # APP::执行 错误，当前用户无此APP使用权限

    # [Workflow] 任务流相关错误
    WORKFLOW_NOT_FOUND = 40001  # 任务流不存在
    WORKFLOW_RUN_ERR_APP_BIND_ERR = (
        40002  # 任务流::执行 错误，当前任务流没有绑定在当前选定APP上
    )

    PGSQL_ERROR = 50001
    SYS_ERROR = 50002  # 系统异常


class BaseResponse(BaseModel):
    """
    基础返回结构
    """

    code: int = Field( default=0, description="返回状态码(0:成功, 其他：异常)",)
    status: RespStatus = Field( default=RespStatus.SUCCESS, description="接口调用状态信息")
    message: str = Field(default="", description="返回副加描述信息")
    message_en: Optional[str] = Field(default="", description="返回副加描述信息, 英文")

    # data: Any = Field(default=None, description="返回数据")

    @classmethod
    def with_code(cls, code: RespCode):
        return BaseResponse(
            code=code,
            status=RespStatus.SUCCESS if code == RespCode.SUCCESS else RespStatus.FAIL,
            message=RespMsg.get_message(code),
            message_en=RespMsg.get_message(code, lang="en"),
        )

    @classmethod
    def database_error(cls):
        code = RespCode.DATABASE_ERROR
        return cls.with_code(code)

    @classmethod
    def fail(cls, message: str, message_en: str = "", code=RespCode.FAIL):
        message_en = message_en or message
        return BaseResponse(code=code, status=RespStatus.FAIL, message=message, message_en=message_en)

    @classmethod
    def fail_400(cls, message: str, message_en: str = ""):
        message_en = message_en or message
        return BaseResponse(code=RespCode.PARAM_ERROR, status=RespStatus.FAIL, message=message, message_en=message_en)

    @classmethod
    def fail_404(cls, message: str, message_en: str = ""):
        message_en = message_en or message
        return BaseResponse(code=RespCode.RECORD_NOT_FOUND, status=RespStatus.FAIL, message=message, message_en=message_en)

    @classmethod
    def fail_500(cls, message: str, message_en: str = ""):
        message_en = message_en or message
        return BaseResponse(code=RespCode.SYS_ERROR, status=RespStatus.FAIL, message=message, message_en=message_en)

    @classmethod
    def exception(cls, err):
        error_str = str(err)
        error_list = error_str.split("\n\n")
        if len(error_list) > 1:
            error_str = error_list[0]
            error_en_str = error_list[1]
        else:
            error_en_str = error_str
        if isinstance(err, ValueError):
            return BaseResponse(code=RespCode.PARAM_ERROR, status=RespStatus.FAIL, message=error_str, message_en=error_en_str)
        if isinstance(err, SQLAlchemyError):
            return BaseResponse(code=RespCode.PGSQL_ERROR, status=RespStatus.FAIL, message=error_str, message_en=error_en_str)
        if isinstance(err, LookupError):
            return BaseResponse(code=RespCode.RECORD_NOT_FOUND, status=RespStatus.FAIL, message=error_str, message_en=error_en_str)
        if isinstance(err, SystemError):
            return BaseResponse(code=RespCode.SYS_ERROR, status=RespStatus.FAIL, message=error_str, message_en=error_en_str)
        if isinstance(err, JwtError):
            return BaseResponse(code=RespCode.AUTH_FAIL, status=RespStatus.FAIL, message=error_str, message_en=error_en_str)
        return BaseResponse(code=RespCode.SYS_ERROR, status=RespStatus.FAIL, message=error_str, message_en=error_en_str)

    @classmethod
    def success(cls):
        return cls.with_code(RespCode.SUCCESS)


class BaseResp(BaseResponse):
    data: typing.Any = Field(default=None, description="返回数据")



class RespMsg:
    """
    对应错误码前端展示消息
    """

    messages = {
        RespCode.SUCCESS: "操作成功",
        RespCode.FAIL: "系统内部错误",
        RespCode.DATABASE_ERROR: "数据库错误",
        RespCode.PARAM_ERROR: "请求参数错误",
        RespCode.RECORD_NOT_FOUND: "数据不存在",
        RespCode.LOGIN_ERROR: "登录失败",
        RespCode.APP_NOT_FOUND: "APP不存在",
        RespCode.APP_RUN_ERR_APP_BIND_ERR: "APP::执行 错误，当前用户无此APP使用权限",
        RespCode.WORKFLOW_NOT_FOUND: "任务流不存在",
        RespCode.WORKFLOW_RUN_ERR_APP_BIND_ERR: "任务流::执行 错误，当前任务流没有绑定在当前选定APP上",
        RespCode.SYS_ERROR: "系统异常",
        RespCode.PGSQL_ERROR: "pgsql错误",
    }

    messages_en = {
        RespCode.SUCCESS: "Operation successful",
        RespCode.FAIL: "Internal server error",
        RespCode.DATABASE_ERROR: "Database error",
        RespCode.PARAM_ERROR: "Request parameter error",
        RespCode.RECORD_NOT_FOUND: "Data not found",
        RespCode.LOGIN_ERROR: "Login failed",
        RespCode.APP_NOT_FOUND: "APP not found",
        RespCode.APP_RUN_ERR_APP_BIND_ERR: "APP::Execution error, current user does not have permission to use this APP",
        RespCode.WORKFLOW_NOT_FOUND: "Workflow not found",
        RespCode.WORKFLOW_RUN_ERR_APP_BIND_ERR: "Workflow::Execution error, current workflow is not bound to the currently selected APP",
        RespCode.SYS_ERROR: "System exception",
        RespCode.PGSQL_ERROR: "pgsql错误",
    }

    @classmethod
    def get_message(cls, code, lang: str = "zh") -> str:
        if lang == "en":
            return cls.messages_en.get(code, "Unknown error")
        else:
            return cls.messages.get(code, "未知错误")


