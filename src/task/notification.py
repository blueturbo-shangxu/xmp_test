"""
Notification Service
通知服务，处理任务失败等通知
"""
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """通知类型"""
    TASK_FAILED = "task_failed"
    TASK_RETRY_EXCEEDED = "task_retry_exceeded"
    SYSTEM_ERROR = "system_error"


class NotificationChannel(ABC):
    """
    通知渠道抽象基类

    后续可以实现不同的通知渠道:
    - FeishuChannel: 飞书通知
    - EmailChannel: 邮件通知
    - DingTalkChannel: 钉钉通知
    - SlackChannel: Slack通知
    """

    @abstractmethod
    def send(
        self,
        notification_type: NotificationType,
        title: str,
        content: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送通知

        Args:
            notification_type: 通知类型
            title: 通知标题
            content: 通知内容
            extra_data: 额外数据

        Returns:
            bool: 是否发送成功
        """
        pass


class LogNotificationChannel(NotificationChannel):
    """
    日志通知渠道（默认实现）

    仅将通知内容记录到日志
    """

    def send(
        self,
        notification_type: NotificationType,
        title: str,
        content: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        logger.warning(
            f"[NOTIFICATION] Type: {notification_type.value}, "
            f"Title: {title}, Content: {content}, Extra: {extra_data}"
        )
        return True


class FeishuNotificationChannel(NotificationChannel):
    """
    飞书通知渠道（占位实现）

    TODO: 实现飞书 Webhook 或 Bot 消息推送
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    def send(
        self,
        notification_type: NotificationType,
        title: str,
        content: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        # TODO: 实现飞书通知
        # 可以使用飞书开放平台的 Webhook 或 Bot API
        logger.info(
            f"[FEISHU] Would send notification: {title} - {content}"
        )
        return True


class EmailNotificationChannel(NotificationChannel):
    """
    邮件通知渠道（占位实现）

    TODO: 实现邮件发送
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    def send(
        self,
        notification_type: NotificationType,
        title: str,
        content: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        # TODO: 实现邮件发送
        logger.info(
            f"[EMAIL] Would send notification: {title} - {content}"
        )
        return True


class NotificationService:
    """
    通知服务

    管理多个通知渠道，支持同时发送到多个渠道
    """

    def __init__(self):
        self._channels: Dict[str, NotificationChannel] = {}
        # 默认添加日志渠道
        self.add_channel("log", LogNotificationChannel())

    def add_channel(self, name: str, channel: NotificationChannel):
        """
        添加通知渠道

        Args:
            name: 渠道名称
            channel: 渠道实例
        """
        self._channels[name] = channel
        logger.info(f"Added notification channel: {name}")

    def remove_channel(self, name: str):
        """移除通知渠道"""
        if name in self._channels:
            del self._channels[name]
            logger.info(f"Removed notification channel: {name}")

    def send(
        self,
        notification_type: NotificationType,
        title: str,
        content: str,
        extra_data: Optional[Dict[str, Any]] = None,
        channels: Optional[list] = None
    ) -> Dict[str, bool]:
        """
        发送通知到所有/指定渠道

        Args:
            notification_type: 通知类型
            title: 标题
            content: 内容
            extra_data: 额外数据
            channels: 指定渠道列表，None表示所有渠道

        Returns:
            Dict[str, bool]: 各渠道发送结果
        """
        results = {}
        target_channels = channels or list(self._channels.keys())

        for channel_name in target_channels:
            channel = self._channels.get(channel_name)
            if channel:
                try:
                    results[channel_name] = channel.send(
                        notification_type, title, content, extra_data
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to send notification via {channel_name}: {e}"
                    )
                    results[channel_name] = False

        return results

    # ==================== 便捷方法 ====================

    def notify_task_failed(
        self,
        task_id: int,
        error_message: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        通知任务失败

        Args:
            task_id: 任务ID
            error_message: 错误信息
            extra_data: 额外数据

        Returns:
            Dict[str, bool]: 发送结果
        """
        title = f"任务执行失败 - Task #{task_id}"
        content = f"任务 {task_id} 执行失败"
        if error_message:
            content += f"\n错误信息: {error_message}"

        data = {"task_id": task_id}
        if extra_data:
            data.update(extra_data)

        return self.send(
            NotificationType.TASK_FAILED,
            title,
            content,
            data
        )

    def notify_retry_exceeded(
        self,
        task_id: int,
        retry_count: int,
        max_retry: int,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        通知重试次数超限

        Args:
            task_id: 任务ID
            retry_count: 当前重试次数
            max_retry: 最大重试次数
            extra_data: 额外数据

        Returns:
            Dict[str, bool]: 发送结果
        """
        title = f"任务重试超限 - Task #{task_id}"
        content = f"任务 {task_id} 重试次数已达上限 ({retry_count}/{max_retry})"

        data = {
            "task_id": task_id,
            "retry_count": retry_count,
            "max_retry": max_retry
        }
        if extra_data:
            data.update(extra_data)

        return self.send(
            NotificationType.TASK_RETRY_EXCEEDED,
            title,
            content,
            data
        )

    def notify_system_error(
        self,
        error_message: str,
        error_traceback: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        通知系统错误

        Args:
            error_message: 错误信息
            error_traceback: 错误堆栈
            extra_data: 额外数据

        Returns:
            Dict[str, bool]: 发送结果
        """
        title = "系统错误通知"
        content = f"系统发生错误:\n{error_message}"
        if error_traceback:
            content += f"\n\n堆栈信息:\n{error_traceback[:500]}"  # 截断堆栈

        data = {"error": error_message}
        if extra_data:
            data.update(extra_data)

        return self.send(
            NotificationType.SYSTEM_ERROR,
            title,
            content,
            data
        )
