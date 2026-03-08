"""
Task Worker
任务消费者启动脚本

用法:
    python -m src.task.worker

或:
    python src/task/worker.py
"""
import sys
import signal
import logging
import argparse
from pathlib import Path

# 确保项目根目录在 Python 路径中
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logging_config import setup_worker_logging
from src.task.consumer import TaskConsumer, DEFAULT_MAX_WORKERS
from src.task.checker import TaskChecker

logger = logging.getLogger(__name__)


def signal_handler(signum, frame, consumer: TaskConsumer, checker: TaskChecker):
    """信号处理函数"""
    logger.info(f"Received signal {signum}, stopping...")
    consumer.stop()
    checker.stop()
    sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Task Worker")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Maximum number of worker threads (default: {DEFAULT_MAX_WORKERS})"
    )
    parser.add_argument(
        "--no-checker",
        action="store_true",
        help="Disable task checker"
    )
    parser.add_argument(
        "--checker-interval",
        type=int,
        default=30,
        help="Task checker interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)"
    )
    args = parser.parse_args()

    # 设置Worker服务日志（包含线程名）
    setup_worker_logging()
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    logger.info("Starting Task Worker...")

    # 创建消费者（处理器已在模块加载时注册）
    consumer = TaskConsumer(max_workers=args.max_workers)

    # 创建检查器
    checker = TaskChecker(check_interval=args.checker_interval)

    # 注册信号处理
    def handle_signal(signum, frame):
        signal_handler(signum, frame, consumer, checker)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # 启动检查器
    if not args.no_checker:
        checker.start(daemon=True)
        logger.info("Task checker started")

    # 启动消费者（阻塞）
    logger.info(f"Task consumer starting with max_workers={args.max_workers}...")
    try:
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        consumer.stop()
        checker.stop()
        logger.info("Task Worker stopped")


if __name__ == "__main__":
    main()
