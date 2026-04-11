"""
连线日志模块 - 用于记录 XSwiftBus 和 FSD 连接的详细日志
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

# 全局日志配置
_connection_logger: Optional[logging.Logger] = None
_logging_enabled = False


def setup_connection_logging(enabled: bool = True, max_bytes: int = 5*1024*1024, backup_count: int = 3,
                              clear_on_startup: bool = True) -> logging.Logger:
    """
    设置连线日志
    
    Args:
        enabled: 是否启用日志
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的备份文件数量
        clear_on_startup: 启动时是否清空日志文件
    
    Returns:
        配置好的日志记录器
    """
    global _connection_logger, _logging_enabled
    
    # 创建日志记录器
    logger = logging.getLogger('ISFP-Connect.Connection')
    logger.setLevel(logging.DEBUG if enabled else logging.WARNING)
    
    # 清除现有的处理器
    logger.handlers.clear()
    
    if not enabled:
        _logging_enabled = False
        return logger
    
    # 确保日志目录存在
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    log_file = os.path.join(logs_dir, 'connect.log')
    
    # 启动时清空日志文件
    if clear_on_startup and os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('')  # 清空文件
    
    # 创建 RotatingFileHandler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 设置日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    _connection_logger = logger
    _logging_enabled = True
    
    logger.info("=" * 80)
    logger.info("连线日志系统启动")
    logger.info(f"日志文件: {log_file}")
    logger.info("=" * 80)
    
    return logger


def get_connection_logger() -> logging.Logger:
    """获取连线日志记录器"""
    global _connection_logger
    if _connection_logger is None:
        _connection_logger = setup_connection_logging(_logging_enabled)
    return _connection_logger


def enable_connection_logging():
    """启用连线日志"""
    global _logging_enabled
    _logging_enabled = True
    setup_connection_logging(True)
    get_connection_logger().info("连线日志已启用")


def disable_connection_logging():
    """禁用连线日志"""
    global _logging_enabled
    _logging_enabled = False
    logger = get_connection_logger()
    logger.info("连线日志已禁用")
    logger.setLevel(logging.WARNING)
    # 清除处理器
    logger.handlers.clear()


def is_logging_enabled() -> bool:
    """检查日志是否已启用"""
    return _logging_enabled


def log_fsd_message(direction: str, message: str):
    """
    记录 FSD 消息
    
    Args:
        direction: 方向 ('SEND' 或 'RECV')
        message: 消息内容
    """
    if not _logging_enabled:
        return
    
    logger = get_connection_logger()
    # 截断过长的消息
    msg_display = message[:200] + "..." if len(message) > 200 else message
    logger.debug(f"[FSD {direction}] {msg_display}")


def log_xswiftbus_message(direction: str, interface: str, method: str, args: str = ""):
    """
    记录 XSwiftBus 消息
    
    Args:
        direction: 方向 ('SEND' 或 'RECV')
        interface: DBus 接口
        method: 方法名
        args: 参数
    """
    if not _logging_enabled:
        return
    
    logger = get_connection_logger()
    logger.debug(f"[XSwiftBus {direction}] {interface}.{method}({args})")


def log_connection_event(connector_type: str, event: str, details: str = ""):
    """
    记录连接事件
    
    Args:
        connector_type: 连接器类型 ('FSD' 或 'XSwiftBus')
        event: 事件名称
        details: 详细信息
    """
    if not _logging_enabled:
        return
    
    logger = get_connection_logger()
    if details:
        logger.info(f"[{connector_type}] {event}: {details}")
    else:
        logger.info(f"[{connector_type}] {event}")


def log_connection_error(connector_type: str, error: str, exception: Exception = None):
    """
    记录连接错误
    
    Args:
        connector_type: 连接器类型 ('FSD' 或 'XSwiftBus')
        error: 错误信息
        exception: 异常对象
    """
    if not _logging_enabled:
        return
    
    logger = get_connection_logger()
    if exception:
        logger.error(f"[{connector_type}] {error}", exc_info=exception)
    else:
        logger.error(f"[{connector_type}] {error}")


class ConnectionLogMixin:
    """连接日志混入类，可以添加到 FSDClient 和 XPlaneConnector"""
    
    def _log_send(self, message: str):
        """记录发送的消息"""
        log_fsd_message('SEND', message)
    
    def _log_recv(self, message: str):
        """记录接收的消息"""
        log_fsd_message('RECV', message)
    
    def _log_event(self, event: str, details: str = ""):
        """记录事件"""
        connector_type = self.__class__.__name__
        log_connection_event(connector_type, event, details)
    
    def _log_error(self, error: str, exception: Exception = None):
        """记录错误"""
        connector_type = self.__class__.__name__
        log_connection_error(connector_type, error, exception)
