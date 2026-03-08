"""
Logging configuration module for XMP Auth Server
日志配置模块，提供接口服务和离线任务服务两种不同的日志配置
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from enum import Enum

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class LoggerType(str, Enum):
    """日志类型枚举"""
    API = "api"           # 接口服务
    WORKER = "worker"     # 离线任务服务


# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# 日志格式
# 接口服务格式：时间 - 名称 - 级别 - 消息
API_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# 离线任务服务格式：时间 - 线程名 - 名称 - 级别 - 消息
WORKER_LOG_FORMAT = '%(asctime)s - [%(threadName)s] - %(name)s - %(levelname)s - %(message)s'

# 日志文件名
API_LOG_FILE = 'logs/api.log'
WORKER_LOG_FILE = 'logs/worker.log'

# 是否已初始化标志
_initialized = False


def setup_logging(logger_type: LoggerType = LoggerType.API) -> logging.Logger:
    """
    配置日志系统

    Args:
        logger_type: 日志类型，API 或 WORKER

    Returns:
        logging.Logger: 配置好的根日志器
    """
    global _initialized

    # 创建logs目录
    log_dir = BASE_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)

    # 配置根日志器
    root_logger = logging.getLogger()

    # 如果已经初始化过，先清除现有处理器
    if _initialized:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    root_logger.setLevel(getattr(logging, LOG_LEVEL.upper()))

    # 根据类型选择格式和文件
    if logger_type == LoggerType.WORKER:
        log_format = WORKER_LOG_FORMAT
        log_file = WORKER_LOG_FILE
    else:
        log_format = API_LOG_FORMAT
        log_file = API_LOG_FILE

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)

    # 文件处理器
    file_handler = RotatingFileHandler(
        BASE_DIR / log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)

    # 添加处理器
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    _initialized = True

    return root_logger


def setup_api_logging() -> logging.Logger:
    """
    配置接口服务日志

    Returns:
        logging.Logger: 配置好的根日志器
    """
    return setup_logging(LoggerType.API)


def setup_worker_logging() -> logging.Logger:
    """
    配置离线任务服务日志

    Returns:
        logging.Logger: 配置好的根日志器
    """
    return setup_logging(LoggerType.WORKER)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器

    Args:
        name: 日志器名称

    Returns:
        logging.Logger: 日志器实例
    """
    return logging.getLogger(name)
