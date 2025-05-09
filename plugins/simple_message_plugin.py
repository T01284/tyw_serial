# -*- coding: utf-8 -*-
"""
简单报文生成插件
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox,
                             QGroupBox, QSpinBox, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal


class MessagePlugin:
    """简单报文生成插件类"""

    def __init__(self):
        self.name = "简单报文插件"
        self.description = "用于生成简单报文的插件"
        self.app = None  # 主应用程序引用
        self.serial = None  # 串口引用
        self.widget = None  # 插件UI

    def set_app(self, app):
        """设置应用程序引用"""
        self.app = app

    def set_serial(self, serial):
        """设置串口引用"""
        self.serial = serial
        # 更新UI上的串口状态
        if self.widget:
            self.widget.update_serial_status(serial is not None and serial.isOpen())

    def on_data_received(self, data):
        """处理接收到的数据"""
        # 这里可以处理接收到的数据，例如更新UI
        if self.widget:
            self.widget.append_received_data(data)

    def create_ui(self):
        """创建插件UI"""
        self.widget = SimpleMessageWidget(self)
        return self.widget

    def generate_message(self, header, command, data):
        """生成报文

        Args:
            header (str): 报文头
            command (str): 命令字
            data (str): 数据

        Returns:
            bytes: 生成的报文
        """
        try:
            # 移除所有空格
            header = header.replace(" ", "")
            command = command.replace(" ", "")
            data = data.replace(" ", "")

            # 构建报文
            message = bytes.fromhex(f"{header}{command}{data}")
            return message
        except Exception as e:
            print(f"生成报文错误: {str(e)}")
            if self.app:
                self.app.add_to_receive(f"生成报文错误: {str(e)}\n", True)
            return None

    def send_message(self, message):
        """发送报文到串口

        Args:
            message (bytes): 要发送的报文

        Returns:
            bool: 是否发送成功
        """
        if self.app and message:
            try:
                self.app.send_data(message)
                return True
            except Exception as e:
                self.app.add_to_receive(f"发送报文错误: {str(e)}\n", True)
        return False

class SimpleMessageWidget(QWidget):
    send_signal = pyqtSignal(bytes)

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 添加报文生成区域
        message_group = QGroupBox("报文生成")
        message_layout = QGridLayout(message_group)
        main_layout.addWidget(message_group)

        # 报文头
        message_layout.addWidget(QLabel("报文头:"), 0, 0)
        self.header_edit = QLineEdit("01")
        self.header_edit.setPlaceholderText("报文头 (hex)")
        message_layout.addWidget(self.header_edit, 0, 1)

        # 命令字
        message_layout.addWidget(QLabel("命令字:"), 1, 0)
        self.command_edit = QLineEdit("02")
        self.command_edit.setPlaceholderText("命令字 (hex)")
        message_layout.addWidget(self.command_edit, 1, 1)

        # 数据区
        message_layout.addWidget(QLabel("数据区:"), 2, 0)
        self.data_edit = QLineEdit("0304")
        self.data_edit.setPlaceholderText("数据 (hex)")
        message_layout.addWidget(self.data_edit, 2, 1)

        # 常用命令选择
        message_layout.addWidget(QLabel("常用命令:"), 3, 0)
        self.command_combo = QComboBox()
        self.command_combo.addItems([
            "自定义",
            "查询状态 (01)",
            "复位 (02)",
            "启动 (03)",
            "停止 (04)"
        ])
        self.command_combo.currentIndexChanged.connect(self.on_command_selected)
        message_layout.addWidget(self.command_combo, 3, 1)

        # 生成报文按钮
        button_layout = QHBoxLayout()
        message_layout.addLayout(button_layout, 4, 0, 1, 2)

        self.generate_btn = QPushButton("生成报文")
        self.generate_btn.clicked.connect(self.on_generate_clicked)
        button_layout.addWidget(self.generate_btn)

        self.send_btn = QPushButton("发送报文")
        self.send_btn.clicked.connect(self.on_send_clicked)
        button_layout.addWidget(self.send_btn)

        # 添加预览区域
        preview_group = QGroupBox("报文预览")
        preview_layout = QVBoxLayout(preview_group)
        main_layout.addWidget(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)

        # 添加接收数据显示区域
        receive_group = QGroupBox("接收数据解析")
        receive_layout = QVBoxLayout(receive_group)
        main_layout.addWidget(receive_group)

        self.receive_text = QTextEdit()
        self.receive_text.setReadOnly(True)
        receive_layout.addWidget(self.receive_text)

        # 设置串口状态指示
        self.serial_status = QLabel("串口状态: 未连接")
        main_layout.addWidget(self.serial_status)

        # 初始化串口状态
        self.update_serial_status(False)

    def on_command_selected(self, index):
        """命令选择改变时的处理"""
        if index == 0:  # 自定义
            return

        # 预设命令
        commands = {
            1: {"command": "01", "data": "00"},  # 查询状态
            2: {"command": "02", "data": "00"},  # 复位
            3: {"command": "03", "data": "01"},  # 启动
            4: {"command": "04", "data": "00"},  # 停止
        }

        if index in commands:
            self.command_edit.setText(commands[index]["command"])
            self.data_edit.setText(commands[index]["data"])

    def on_generate_clicked(self):
        """生成报文按钮点击处理"""
        header = self.header_edit.text()
        command = self.command_edit.text()
        data = self.data_edit.text()

        message = self.plugin.generate_message(header, command, data)
        if message:
            # 更新预览
            hex_str = ' '.join([f"{b:02X}" for b in message])
            self.preview_text.setText(f"报文内容 (HEX): {hex_str}\n")
            self.preview_text.append(f"报文长度: {len(message)} 字节")

            # 如果插件有app引用，将报文显示在发送区
            if self.plugin.app:
                self.plugin.app.send_text.setText(hex_str)
                self.plugin.app.hex_send.setChecked(True)

    def on_send_clicked(self):
        """发送报文按钮点击处理"""
        header = self.header_edit.text()
        command = self.command_edit.text()
        data = self.data_edit.text()

        message = self.plugin.generate_message(header, command, data)
        if message:
            # 如果插件有app引用，发送报文
            if self.plugin.app:
                self.plugin.send_message(message)

    def update_serial_status(self, is_connected):
        """更新串口状态显示"""
        if is_connected:
            self.serial_status.setText("串口状态: 已连接")
            self.serial_status.setStyleSheet("color: green")
            self.send_btn.setEnabled(True)
        else:
            self.serial_status.setText("串口状态: 未连接")
            self.serial_status.setStyleSheet("color: red")
            self.send_btn.setEnabled(False)

    def append_received_data(self, data):
        """添加接收到的数据到解析区域"""
        try:
            # 简单的解析逻辑
            if len(data) >= 3:  # 至少包含头、命令和数据
                header = data[0]
                command = data[1]
                data_bytes = data[2:]

                self.receive_text.append(f"收到报文:")
                self.receive_text.append(f"  报文头: {header:02X}")
                self.receive_text.append(f"  命令字: {command:02X}")

                hex_data = ' '.join([f"{b:02X}" for b in data_bytes])
                self.receive_text.append(f"  数据区: {hex_data}")
                self.receive_text.append(f"  总字节数: {len(data)}")
                self.receive_text.append("------------------------")
        except Exception as e:
            self.receive_text.append(f"解析数据错误: {str(e)}")