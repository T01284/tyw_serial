# -*- coding: utf-8 -*-
"""
@Author     : T01284
@Date       : 2025-05-10
@Python     : 3.10
@Description: 报文收发模块，负责报文的收发管理
"""

import time
from collections import deque
from datetime import datetime
from PyQt5.QtCore import QObject, QTimer, QMutex, pyqtSignal


class MessageSender(QObject):
    """报文发送管理器"""

    message_sent = pyqtSignal(bytes, str)  # 报文发送完成信号 (message, name)

    def __init__(self):
        super().__init__()
        self.queue = deque()
        self.mutex = QMutex()
        self.processing = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_queue)
        self.timer.setInterval(10)
        self.serial = None

    def set_serial(self, serial):
        """设置串口对象"""
        self.serial = serial

        # 如果串口已关闭，停止定时器
        if not serial or not serial.isOpen():
            self.timer.stop()
            self.queue.clear()
            self.processing = False

    def add_message(self, message, name=''):
        """
        添加报文到发送队列

        Args:
            message (bytes): 要发送的报文
            name (str): 报文名称

        Returns:
            bool: 是否成功添加到队列
        """
        if not self.serial or not self.serial.isOpen():
            return False

        self.mutex.lock()
        self.queue.append((message, name))
        self.mutex.unlock()

        # 如果定时器未启动，启动定时器
        if not self.timer.isActive():
            self.timer.start()

        return True

    def process_queue(self):
        """处理报文发送队列"""
        if self.processing or not self.serial or not self.serial.isOpen():
            return

        self.mutex.lock()
        if not self.queue:
            self.mutex.unlock()
            self.timer.stop()
            return

        self.processing = True
        message, name = self.queue.popleft()
        self.mutex.unlock()

        try:
            # 发送报文
            self.serial.write(message)

            # 发送完成信号
            self.message_sent.emit(message, name)
        except Exception as e:
            print(f"发送报文失败: {str(e)}")

        self.processing = False


class TimedMessage:
    """定时发送报文"""

    def __init__(self, name="", message=bytes(), interval=1000, enabled=False, protocol_id=""):
        self.name = name  # 报文名称
        self.message = message  # 报文内容
        self.interval = interval  # 发送间隔(ms)
        self.enabled = enabled  # 是否启用
        self.last_sent = 0  # 上次发送时间
        self.protocol_id = protocol_id  # 协议ID

    def to_dict(self):
        """
        转换为字典，用于保存配置

        Returns:
            dict: 配置字典
        """
        return {
            "name": self.name,
            "message": " ".join([f"{b:02X}" for b in self.message]),
            "interval": self.interval,
            "enabled": self.enabled,
            "protocol_id": self.protocol_id
        }

    @classmethod
    def from_dict(cls, data):
        """
        从字典创建报文对象

        Args:
            data (dict): 配置字典

        Returns:
            TimedMessage: 报文对象
        """
        try:
            # 将十六进制字符串转换为字节
            message_str = data.get("message", "")
            message_bytes = bytes.fromhex(message_str.replace(" ", ""))

            return cls(
                name=data.get("name", ""),
                message=message_bytes,
                interval=int(data.get("interval", 1000)),
                enabled=bool(data.get("enabled", False)),
                protocol_id=data.get("protocol_id", "")
            )
        except Exception as e:
            print(f"加载定时报文错误: {str(e)}")
            return cls()


class MessageReceiver(QObject):
    """报文接收处理器"""

    message_received = pyqtSignal(bytes)  # 报文接收信号

    def __init__(self):
        super().__init__()
        self.buffer = bytearray()
        self.max_buffer_size = 4096  # 最大缓冲区大小
        self.use_two_byte_length = True  # 新增：是否使用两字节长度（小端格式）

    def set_length_format(self, use_two_bytes=True):
        """
        设置数据长度字段格式

        Args:
            use_two_bytes (bool): 是否使用两字节长度
        """
        self.use_two_byte_length = use_two_bytes

    def process_data(self, data):
        """
        处理接收到的数据

        Args:
            data (bytes): 接收到的数据
        """
        # 添加数据到缓冲区
        self.buffer.extend(data)

        # 限制缓冲区大小
        if len(self.buffer) > self.max_buffer_size:
            self.buffer = self.buffer[-self.max_buffer_size:]

        # 尝试提取完整报文
        self.extract_messages()

    def extract_messages(self):
        """提取完整报文"""
        # 查找报文头
        start_index = self.buffer.find(b'\x59\x44')

        while start_index != -1:
            # 根据使用的长度字段格式决定处理方式
            if self.use_two_byte_length:
                # 两字节长度格式（小端）
                # 检查缓冲区是否足够长，至少包含报文头、ID、长度字段(2字节)
                if start_index + 5 > len(self.buffer):
                    break

                # 获取报文ID和长度
                message_id = self.buffer[start_index + 2]
                # 小端格式：低字节在前，高字节在后
                data_length = self.buffer[start_index + 3] + (self.buffer[start_index + 4] << 8)

                # 计算完整报文长度：报文头(2) + ID(1) + 长度(2) + 数据(n) + CRC(2) + 报文尾(2)
                total_length = 2 + 1 + 2 + data_length + 2 + 2
            else:
                # 单字节长度格式
                # 检查缓冲区是否足够长，至少包含报文头、ID、长度字段
                if start_index + 4 > len(self.buffer):
                    break

                # 获取报文长度
                message_id = self.buffer[start_index + 2]
                data_length = self.buffer[start_index + 3]

                # 计算完整报文长度：报文头(2) + ID(1) + 长度(1) + 数据(n) + CRC(2) + 报文尾(2)
                total_length = 2 + 1 + 1 + data_length + 2 + 2

            # 检查缓冲区是否包含完整报文
            if start_index + total_length <= len(self.buffer):
                # 检查报文尾
                if self.buffer[start_index + total_length - 2:start_index + total_length] == b'\x4B\x4A':
                    # 提取完整报文
                    message = bytes(self.buffer[start_index:start_index + total_length])

                    # 发送报文接收信号
                    self.message_received.emit(message)

                    # 从缓冲区中删除已处理的报文
                    self.buffer = self.buffer[start_index + total_length:]

                    # 继续查找下一个报文头
                    start_index = self.buffer.find(b'\x59\x44')
                else:
                    # 报文尾不匹配，从下一个位置继续查找报文头
                    start_index = self.buffer.find(b'\x59\x44', start_index + 1)
            else:
                # 报文不完整，等待更多数据
                break

        # 如果没有找到报文头或报文不完整，保留缓冲区
        if start_index == -1:
            # 清空缓冲区，但保留最后几个字节（可能是报文头的一部分）
            if len(self.buffer) > 10:
                self.buffer = self.buffer[-10:]