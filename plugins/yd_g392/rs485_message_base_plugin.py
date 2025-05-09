# -*- coding: utf-8 -*-
"""
RS485基础报文插件
提供RS485报文插件的基础类，用于派生具体的报文插件
"""
import binascii
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox,
                             QGroupBox, QCheckBox, QSpinBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal


class RS485MessagePlugin:
    """RS485报文插件基类"""

    def __init__(self):
        self.name = "RS485基础报文插件"
        self.description = "提供RS485报文插件的基础类"
        self.app = None  # 主应用程序引用
        self.serial = None  # 串口对象

    def set_app(self, app):
        """设置应用程序引用"""
        self.app = app

    def set_serial(self, serial):
        """设置串口对象"""
        self.serial = serial
        if hasattr(self, 'widget') and hasattr(self.widget, 'set_serial'):
            self.widget.set_serial(serial)

    def create_ui(self):
        """创建插件UI"""
        return RS485MessageBaseWidget(self)

    def generate_message(self, params=None):
        """
        生成报文

        Args:
            params (dict): 报文参数

        Returns:
            bytes: 生成的报文
        """
        # 基类不实现具体生成逻辑，由子类重写
        return None

    def send_message(self, message):
        """
        发送报文

        Args:
            message (bytes): 要发送的报文

        Returns:
            bool: 是否发送成功
        """
        if not self.serial or not self.serial.isOpen():
            if self.app:
                self.app.add_log_message("串口未打开，无法发送数据", "error")
            return False

        try:
            self.serial.write(message)
            if self.app:
                # 显示发送数据
                hex_text = ' '.join([f"{b:02X}" for b in message])
                self.app.add_log_message(f"插件发送: {hex_text}", "send")
            return True
        except Exception as e:
            if self.app:
                self.app.add_log_message(f"发送报文失败: {str(e)}", "error")
            return False

    def on_data_received(self, data):
        """
        接收数据的处理函数

        Args:
            data (bytes): 接收到的数据
        """
        # 基类不实现具体接收逻辑，由子类重写
        pass

    def calculate_crc16(self, data):
        """
        计算CRC16校验值

        Args:
            data (bytes): 要计算校验值的数据

        Returns:
            int: 校验值
        """
        crc = 0xFFFF
        poly = 0xA001  # 多项式

        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ poly
                else:
                    crc >>= 1

        return crc


class RS485MessageBaseWidget(QWidget):
    """RS485报文插件基础UI"""

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 主布局
        self.main_layout = QVBoxLayout(self)

        # 通用参数区
        common_group = QGroupBox("通用参数")
        common_layout = QGridLayout(common_group)
        self.main_layout.addWidget(common_group)

        # 报文ID
        common_layout.addWidget(QLabel("报文ID:"), 0, 0)
        self.message_id_edit = QLineEdit("00h")
        common_layout.addWidget(self.message_id_edit, 0, 1)

        # 节点类型
        common_layout.addWidget(QLabel("节点类型:"), 1, 0)
        self.node_combo = QComboBox()
        self.node_combo.addItems(["IOT", "ALM", "MTR", "BMS", "IMCU", "RM"])
        common_layout.addWidget(self.node_combo, 1, 1)

        # 报文格式选项
        format_group = QGroupBox("报文格式")
        format_layout = QHBoxLayout(format_group)
        self.main_layout.addWidget(format_group)

        # 添加报文头
        self.add_header_check = QCheckBox("添加报文头(YD)")
        self.add_header_check.setChecked(True)
        format_layout.addWidget(self.add_header_check)

        # 添加CRC校验
        self.add_crc_check = QCheckBox("添加CRC校验")
        self.add_crc_check.setChecked(True)
        format_layout.addWidget(self.add_crc_check)

        # 添加报文尾
        self.add_footer_check = QCheckBox("添加报文尾(KJ)")
        self.add_footer_check.setChecked(True)
        format_layout.addWidget(self.add_footer_check)

        # 操作按钮区
        button_layout = QHBoxLayout()
        self.main_layout.addLayout(button_layout)

        # 生成报文按钮
        self.generate_btn = QPushButton("生成报文")
        self.generate_btn.clicked.connect(self.generate_message)
        button_layout.addWidget(self.generate_btn)

        # 发送报文按钮
        self.send_btn = QPushButton("发送报文")
        self.send_btn.clicked.connect(self.send_message)
        button_layout.addWidget(self.send_btn)

        # 复制到发送区按钮
        self.copy_to_send_btn = QPushButton("复制到发送区")
        self.copy_to_send_btn.clicked.connect(self.copy_to_send)
        button_layout.addWidget(self.copy_to_send_btn)

        # 报文显示区
        result_group = QGroupBox("报文内容")
        result_layout = QVBoxLayout(result_group)
        self.main_layout.addWidget(result_group)

        # 报文内容显示
        self.message_display = QLineEdit()
        self.message_display.setReadOnly(True)
        result_layout.addWidget(self.message_display)

    def set_serial(self, serial):
        """设置串口对象"""
        # 更新发送按钮状态
        self.send_btn.setEnabled(serial is not None and serial.isOpen())

    def generate_message(self):
        """生成报文"""
        try:
            # 获取参数
            params = self.get_parameters()

            # 使用插件生成报文
            message = self.plugin.generate_message(params)

            if message:
                # 显示报文内容
                hex_str = ' '.join([f"{b:02X}" for b in message])
                self.message_display.setText(hex_str)

                # 设置剪贴板
                #QApplication.clipboard().setText(hex_str)
            else:
                QMessageBox.warning(self, "错误", "生成报文失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成报文发生异常: {str(e)}")

    def send_message(self):
        """发送报文"""
        try:
            # 获取参数
            params = self.get_parameters()

            # 使用插件生成报文
            message = self.plugin.generate_message(params)

            if message:
                # 发送报文
                success = self.plugin.send_message(message)

                if not success:
                    QMessageBox.warning(self, "错误", "发送报文失败")
            else:
                QMessageBox.warning(self, "错误", "生成报文失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送报文发生异常: {str(e)}")

    def copy_to_send(self):
        """复制报文到发送区"""
        # 基类只获取报文内容，子类需要重写此方法以实现具体的复制逻辑
        text = self.message_display.text()
        if not text:
            # 尝试重新生成报文
            self.generate_message()
            text = self.message_display.text()

        if not text:
            QMessageBox.warning(self, "错误", "没有可复制的报文内容")
            return

        # 基类仅通知用户已复制
        QMessageBox.information(self, "提示", "报文内容已复制")

    def get_parameters(self):
        """
        获取UI上的参数

        Returns:
            dict: 参数字典
        """
        # 获取基础参数
        return {
            'add_header': self.add_header_check.isChecked(),
            'add_crc': self.add_crc_check.isChecked(),
            'add_footer': self.add_footer_check.isChecked()
        }