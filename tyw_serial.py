# -*- coding: utf-8 -*-
"""
@Author     : 王舒 (修改：增强版)
@Company    : 黑龙江天有为科技有限公司
@Date       : 2025-05-09 (修改：2025-05-10)
@Version    : 1.2.0
@Python     : 3.10
依赖库:
    - pyserial PyQt5

增强功能：
    - 支持多条报文同时定时发送
    - 每条报文可设置独立的发送周期
    - 解决同时发送的冲突问题
    - 统一的日志显示区域，同时显示发送/接收/系统日志
    - 可选择是否显示十六进制内容
"""
import sys
import os
import time
import configparser
import importlib.util
from collections import deque
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QTextEdit, QLineEdit,
                             QGridLayout, QGroupBox, QCheckBox, QSpinBox, QSplitter,
                             QTabWidget, QFileDialog, QMessageBox, QStatusBar, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView, QDialog,
                             QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QMutex, QObject
from PyQt5.QtGui import QTextCursor, QColor, QBrush, QTextCharFormat, QFont
import serial
import serial.tools.list_ports
import json


class MessageSender(QObject):
    """报文发送管理器"""

    message_sent = pyqtSignal(bytes)  # 报文发送完成信号

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

    def add_message(self, message):
        """添加报文到发送队列"""
        if not self.serial or not self.serial.isOpen():
            return False

        self.mutex.lock()
        self.queue.append(message)
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
        message = self.queue.popleft()
        self.mutex.unlock()

        try:
            # 发送报文
            self.serial.write(message)

            # 发送完成信号
            self.message_sent.emit(message)
        except Exception as e:
            print(f"发送报文失败: {str(e)}")

        self.processing = False


class TimedMessage:
    """定时发送报文"""

    def __init__(self, name="", message=bytes(), interval=1000, enabled=False):
        self.name = name  # 报文名称
        self.message = message  # 报文内容
        self.interval = interval  # 发送间隔(ms)
        self.enabled = enabled  # 是否启用
        self.last_sent = 0  # 上次发送时间
        self.timer_id = None  # 定时器ID

    def to_dict(self):
        """转换为字典，用于保存配置"""
        return {
            "name": self.name,
            "message": " ".join([f"{b:02X}" for b in self.message]),
            "interval": self.interval,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建报文，用于加载配置"""
        try:
            # 将十六进制字符串转换为字节
            message_str = data.get("message", "")
            message_bytes = bytes.fromhex(message_str.replace(" ", ""))

            return cls(
                name=data.get("name", ""),
                message=message_bytes,
                interval=int(data.get("interval", 1000)),
                enabled=bool(data.get("enabled", False))
            )
        except Exception as e:
            print(f"加载定时报文错误: {str(e)}")
            return cls()


class TimedMessageDialog(QDialog):
    """定时报文编辑对话框"""

    def __init__(self, parent=None, timed_message=None):
        super().__init__(parent)
        self.setWindowTitle("定时报文设置")
        self.resize(500, 300)

        self.timed_message = timed_message or TimedMessage()

        # 创建布局
        layout = QVBoxLayout(self)

        # 创建表单
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # 报文名称
        self.name_edit = QLineEdit(self.timed_message.name)
        form_layout.addRow("报文名称:", self.name_edit)

        # 报文内容
        self.message_edit = QTextEdit()
        if self.timed_message.message:
            hex_text = ' '.join([f"{b:02X}" for b in self.timed_message.message])
            self.message_edit.setPlainText(hex_text)
        form_layout.addRow("报文内容(十六进制):", self.message_edit)

        # 发送间隔
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(10, 60000)  # 10ms到60s
        self.interval_spinbox.setValue(self.timed_message.interval)
        self.interval_spinbox.setSuffix(" ms")
        form_layout.addRow("发送间隔:", self.interval_spinbox)

        # 是否启用
        self.enabled_checkbox = QCheckBox("启用定时发送")
        self.enabled_checkbox.setChecked(self.timed_message.enabled)
        form_layout.addRow("", self.enabled_checkbox)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        """确认按钮点击事件"""
        # 验证输入
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "报文名称不能为空!")
            return

        # 获取报文内容
        message_text = self.message_edit.toPlainText().strip()
        try:
            # 移除空格和换行
            message_text = message_text.replace(" ", "").replace("\n", "").replace("\r", "")
            message = bytes.fromhex(message_text)
            if not message:
                QMessageBox.warning(self, "错误", "报文内容不能为空!")
                return
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无效的十六进制报文: {str(e)}")
            return

        # 更新报文对象
        self.timed_message.name = name
        self.timed_message.message = message
        self.timed_message.interval = self.interval_spinbox.value()
        self.timed_message.enabled = self.enabled_checkbox.isChecked()

        super().accept()


class TimedMessagesManager(QWidget):
    """定时报文管理器"""

    send_message_signal = pyqtSignal(bytes, str)  # 发送报文信号，包含报文名称

    def __init__(self, parent=None):
        super().__init__(parent)

        self.timed_messages = []  # 定时报文列表
        self.message_sender = MessageSender()  # 报文发送管理器
        self.timer = QTimer()  # 用于检查报文发送时间
        self.timer.timeout.connect(self.check_messages)

        # 创建布局
        layout = QVBoxLayout(self)

        # 创建报文列表
        self.message_table = QTableWidget(0, 5)
        self.message_table.setHorizontalHeaderLabels(["名称", "内容", "间隔(ms)", "状态", "操作"])
        self.message_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.message_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.message_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.message_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.message_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.message_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.message_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.message_table)

        # 创建按钮布局
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        # 添加报文按钮
        self.add_button = QPushButton("添加报文")
        self.add_button.clicked.connect(self.add_message)
        button_layout.addWidget(self.add_button)

        # 导入插件报文按钮
        self.import_button = QPushButton("导入插件报文")
        self.import_button.clicked.connect(self.import_from_plugin)
        button_layout.addWidget(self.import_button)

        # 全部启用/禁用按钮
        self.enable_all_button = QPushButton("全部启用")
        self.enable_all_button.clicked.connect(self.enable_all)
        button_layout.addWidget(self.enable_all_button)

        self.disable_all_button = QPushButton("全部禁用")
        self.disable_all_button.clicked.connect(self.disable_all)
        button_layout.addWidget(self.disable_all_button)

        # 保存/加载配置按钮
        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)

        self.load_button = QPushButton("加载配置")
        self.load_button.clicked.connect(self.load_config)
        button_layout.addWidget(self.load_button)

        # 连接信号
        self.message_sender.message_sent.connect(self.on_message_sent)

    def set_serial(self, serial):
        """设置串口对象"""
        self.message_sender.set_serial(serial)

        # 如果串口已打开，启动定时器
        if serial and serial.isOpen():
            # 每10ms检查一次是否有报文需要发送
            self.timer.start(10)
        else:
            self.timer.stop()
            self.update_table()  # 更新表格状态显示

    def add_message(self):
        """添加定时报文"""
        dialog = TimedMessageDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 添加到列表
            self.timed_messages.append(dialog.timed_message)
            # 更新表格
            self.update_table()

    def import_from_plugin(self):
        """从插件导入报文"""
        # 获取主窗口
        main_window = self.window()

        # 检查是否有已加载的插件
        if not hasattr(main_window, 'current_plugin') or not main_window.current_plugin:
            QMessageBox.warning(self, "错误", "请先加载报文插件!")
            return

        plugin = main_window.current_plugin

        # 检查插件是否支持生成报文
        if not hasattr(plugin, 'generate_message'):
            QMessageBox.warning(self, "错误", "当前插件不支持生成报文!")
            return

        try:
            # 生成报文
            message = plugin.generate_message()
            if not message:
                QMessageBox.warning(self, "错误", "插件未生成有效报文!")
                return

            # 创建定时报文
            timed_message = TimedMessage(
                name=f"Plugin_{datetime.now().strftime('%H%M%S')}",
                message=message,
                interval=1000,
                enabled=False
            )

            # 打开编辑对话框
            dialog = TimedMessageDialog(self, timed_message)
            if dialog.exec_() == QDialog.Accepted:
                # 添加到列表
                self.timed_messages.append(dialog.timed_message)
                # 更新表格
                self.update_table()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入报文失败: {str(e)}")

    def edit_message(self, row):
        """编辑定时报文"""
        if row < 0 or row >= len(self.timed_messages):
            return

        dialog = TimedMessageDialog(self, self.timed_messages[row])
        if dialog.exec_() == QDialog.Accepted:
            # 更新表格
            self.update_table()

    def remove_message(self, row):
        """删除定时报文"""
        if row < 0 or row >= len(self.timed_messages):
            return

        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除 '{self.timed_messages[row].name}' 吗?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 删除报文
            del self.timed_messages[row]
            # 更新表格
            self.update_table()

    def toggle_message(self, row):
        """切换定时报文启用状态"""
        if row < 0 or row >= len(self.timed_messages):
            return

        # 切换状态
        self.timed_messages[row].enabled = not self.timed_messages[row].enabled
        # 更新表格
        self.update_table()

    def enable_all(self):
        """启用所有定时报文"""
        for message in self.timed_messages:
            message.enabled = True
        self.update_table()

    def disable_all(self):
        """禁用所有定时报文"""
        for message in self.timed_messages:
            message.enabled = False
        self.update_table()

    def update_table(self):
        """更新报文表格"""
        # 设置行数
        self.message_table.setRowCount(len(self.timed_messages))

        for row, message in enumerate(self.timed_messages):
            # 名称
            name_item = QTableWidgetItem(message.name)
            self.message_table.setItem(row, 0, name_item)

            # 内容
            content = " ".join([f"{b:02X}" for b in message.message])
            if len(content) > 30:
                content = content[:30] + "..."
            content_item = QTableWidgetItem(content)
            self.message_table.setItem(row, 1, content_item)

            # 间隔
            interval_item = QTableWidgetItem(f"{message.interval}")
            self.message_table.setItem(row, 2, interval_item)

            # 状态
            status_text = "启用" if message.enabled else "禁用"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QBrush(QColor("green" if message.enabled else "red")))
            self.message_table.setItem(row, 3, status_item)

            # 操作按钮
            operation_widget = QWidget()
            operation_layout = QHBoxLayout(operation_widget)
            operation_layout.setContentsMargins(0, 0, 0, 0)

            # 编辑按钮
            edit_button = QPushButton("编辑")
            edit_button.clicked.connect(lambda checked, r=row: self.edit_message(r))
            operation_layout.addWidget(edit_button)

            # 启用/禁用按钮
            toggle_button = QPushButton("禁用" if message.enabled else "启用")
            toggle_button.clicked.connect(lambda checked, r=row: self.toggle_message(r))
            operation_layout.addWidget(toggle_button)

            # 删除按钮
            delete_button = QPushButton("删除")
            delete_button.clicked.connect(lambda checked, r=row: self.remove_message(r))
            operation_layout.addWidget(delete_button)

            self.message_table.setCellWidget(row, 4, operation_widget)

    def check_messages(self):
        """检查并发送定时报文"""
        current_time = int(time.time() * 1000)  # 当前时间(毫秒)

        for message in self.timed_messages:
            if not message.enabled:
                continue

            # 计算下次发送时间
            if message.last_sent == 0:  # 首次发送
                message.last_sent = current_time
                self.send_message(message)
            elif current_time - message.last_sent >= message.interval:
                message.last_sent = current_time
                self.send_message(message)

    def send_message(self, message):
        """发送报文"""
        success = self.message_sender.add_message(message.message)
        if success:
            # 发送报文信号，包含报文名称
            self.send_message_signal.emit(message.message, message.name)
        elif message.enabled:
            # 如果发送失败，禁用该报文
            message.enabled = False
            self.update_table()

            # 获取主窗口
            main_window = self.window()
            if hasattr(main_window, 'add_log_message'):
                main_window.add_log_message(f"错误: 无法发送报文 '{message.name}', 已禁用", "error")

    def on_message_sent(self, message):
        """报文发送完成处理"""
        pass  # 已通过send_message_signal处理

    def save_config(self):
        """保存定时报文配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存定时报文配置", "", "JSON文件 (*.json);;所有文件 (*.*)")

        if not file_path:
            return

        try:
            # 转换为json格式
            config = {
                "timed_messages": [message.to_dict() for message in self.timed_messages]
            }

            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            # 获取主窗口
            main_window = self.window()
            if hasattr(main_window, 'add_log_message'):
                main_window.add_log_message(f"定时报文配置已保存到 {file_path}", "system")
            else:
                QMessageBox.information(self, "保存成功", f"定时报文配置已保存到 {file_path}")
        except Exception as e:
            # 获取主窗口
            main_window = self.window()
            if hasattr(main_window, 'add_log_message'):
                main_window.add_log_message(f"保存配置失败: {str(e)}", "error")
            else:
                QMessageBox.critical(self, "保存失败", f"保存配置失败: {str(e)}")

    def load_config(self):
        """加载定时报文配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载定时报文配置", "", "JSON文件 (*.json);;所有文件 (*.*)")

        if not file_path:
            return

        try:
            # 从文件加载
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 转换为报文对象
            messages = []
            for message_dict in config.get("timed_messages", []):
                message = TimedMessage.from_dict(message_dict)
                messages.append(message)

            # 更新列表
            self.timed_messages = messages

            # 更新表格
            self.update_table()

            # 获取主窗口
            main_window = self.window()
            if hasattr(main_window, 'add_log_message'):
                main_window.add_log_message(f"已加载 {len(self.timed_messages)} 个定时报文", "system")
            else:
                QMessageBox.information(self, "加载成功", f"已加载 {len(self.timed_messages)} 个定时报文")
        except Exception as e:
            # 获取主窗口
            main_window = self.window()
            if hasattr(main_window, 'add_log_message'):
                main_window.add_log_message(f"加载配置失败: {str(e)}", "error")
            else:
                QMessageBox.critical(self, "加载失败", f"加载配置失败: {str(e)}")


class SerialReceiveThread(QThread):
    """串口接收线程"""
    receive_signal = pyqtSignal(bytes)

    def __init__(self, serial_port):
        super().__init__()
        self.serial = serial_port
        self.is_running = True

    def run(self):
        while self.is_running and self.serial and self.serial.isOpen():
            try:
                # 检查是否有可读取的数据
                if self.serial.in_waiting:
                    data = self.serial.read(self.serial.in_waiting)
                    if data:
                        self.receive_signal.emit(data)
            except Exception as e:
                print(f"接收数据错误: {str(e)}")

            # 防止CPU占用过高
            self.msleep(10)

    def stop(self):
        self.is_running = False
        self.wait()


class SerialToolUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("串口通信工具 - 增强版")
        self.resize(1200, 800)  # 设置初始窗口大小

        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # 在状态栏添加串口状态信息
        self.statusLabel = QLabel("串口: 未连接")
        self.statusBar.addPermanentWidget(self.statusLabel)

        # 添加接收和发送计数器到状态栏
        self.receivedCountLabel = QLabel("接收: 0 字节")
        self.sentCountLabel = QLabel("发送: 0 字节")
        self.statusBar.addPermanentWidget(self.receivedCountLabel)
        self.statusBar.addPermanentWidget(self.sentCountLabel)

        # 添加重置计数器按钮到状态栏
        self.resetCounterBtn = QPushButton("计数器清零")
        self.resetCounterBtn.setFixedWidth(100)
        self.statusBar.addPermanentWidget(self.resetCounterBtn)

        # 创建主窗口部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 创建左右分割区域
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        # ========== 左侧区域（串口设置、发送、接收）==========
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        main_splitter.addWidget(left_widget)

        # ========== 右侧区域（报文生成区）==========
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        main_splitter.addWidget(right_widget)

        # 设置左右分割比例 (1:1)
        main_splitter.setSizes([600, 600])

        # ========== 左侧顶部：串口设置 ==========
        serial_config_group = QGroupBox("串口设置")
        serial_config_layout = QGridLayout(serial_config_group)
        left_layout.addWidget(serial_config_group)

        # 串口检测按钮
        self.detect_serial_btn = QPushButton("检测串口")
        serial_config_layout.addWidget(self.detect_serial_btn, 0, 0, 1, 2)

        # 串口选择
        serial_config_layout.addWidget(QLabel("串口选择:"), 1, 0)
        self.serial_port_combo = QComboBox()
        serial_config_layout.addWidget(self.serial_port_combo, 1, 1)

        # 波特率
        serial_config_layout.addWidget(QLabel("波特率:"), 2, 0)
        self.baud_rate_combo = QComboBox()
        self.baud_rate_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_rate_combo.setCurrentText("115200")  # 默认值
        serial_config_layout.addWidget(self.baud_rate_combo, 2, 1)

        # 数据位
        serial_config_layout.addWidget(QLabel("数据位:"), 3, 0)
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(["5", "6", "7", "8"])
        self.data_bits_combo.setCurrentText("8")  # 默认值
        serial_config_layout.addWidget(self.data_bits_combo, 3, 1)

        # 校验位
        serial_config_layout.addWidget(QLabel("校验位:"), 4, 0)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["N", "E", "O", "M", "S"])
        self.parity_combo.setCurrentText("N")  # 默认值
        serial_config_layout.addWidget(self.parity_combo, 4, 1)

        # 停止位
        serial_config_layout.addWidget(QLabel("停止位:"), 5, 0)
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(["1", "1.5", "2"])
        self.stop_bits_combo.setCurrentText("1")  # 默认值
        serial_config_layout.addWidget(self.stop_bits_combo, 5, 1)

        # 打开/关闭串口按钮
        self.open_serial_btn = QPushButton("打开串口")
        self.close_serial_btn = QPushButton("关闭串口")
        self.close_serial_btn.setEnabled(False)  # 初始时关闭按钮不可用
        serial_config_layout.addWidget(self.open_serial_btn, 6, 0)
        serial_config_layout.addWidget(self.close_serial_btn, 6, 1)

        # ========== 左侧中部：快速发送区 ==========
        quick_send_group = QGroupBox("快速发送")
        quick_send_layout = QVBoxLayout(quick_send_group)
        left_layout.addWidget(quick_send_group)

        # 发送内容输入框
        quick_send_layout.addWidget(QLabel("发送内容(十六进制):"))
        self.quick_send_text = QLineEdit()
        quick_send_layout.addWidget(self.quick_send_text)

        # 发送按钮区域
        quick_send_buttons = QHBoxLayout()
        quick_send_layout.addLayout(quick_send_buttons)

        # 发送按钮
        self.quick_send_btn = QPushButton("发送")
        self.quick_send_btn.clicked.connect(self.send_quick_data)
        quick_send_buttons.addWidget(self.quick_send_btn)

        # ========== 多报文定时发送区 ==========
        # 使用选项卡分为手动发送和定时发送两个部分
        send_tabs = QTabWidget()
        # 定时任务部分
        timed_send_tab = QWidget()
        timed_layout = QVBoxLayout(timed_send_tab)

        # 创建定时发送管理器
        self.timed_messages_manager = TimedMessagesManager()
        timed_layout.addWidget(self.timed_messages_manager)

        # 将定时发送管理器发送的报文连接到日志
        self.timed_messages_manager.send_message_signal.connect(self.on_timed_message_sent)

        # 添加到选项卡
        send_tabs.addTab(timed_send_tab, "定时任务")
        left_layout.addWidget(send_tabs)

        # ========== 日志显示区 ==========
        log_group = QGroupBox("通信日志")
        log_layout = QVBoxLayout(log_group)
        left_layout.addWidget(log_group)

        # 日志显示框
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        log_layout.addWidget(self.log_display)

        # 日志控制区域
        log_control_layout = QHBoxLayout()
        log_layout.addLayout(log_control_layout)

        # 显示十六进制选项
        self.show_hex = QCheckBox("显示十六进制")
        self.show_hex.setChecked(True)
        log_control_layout.addWidget(self.show_hex)

        # 显示时间选项
        self.show_time = QCheckBox("显示时间")
        self.show_time.setChecked(True)
        log_control_layout.addWidget(self.show_time)

        # 自动滚动选项
        self.auto_scroll = QCheckBox("自动滚动")
        self.auto_scroll.setChecked(True)
        log_control_layout.addWidget(self.auto_scroll)

        # 清空日志按钮
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_control_layout.addWidget(self.clear_log_btn)

        # 保存日志按钮
        self.save_log_btn = QPushButton("保存日志")
        self.save_log_btn.clicked.connect(self.save_log)
        log_control_layout.addWidget(self.save_log_btn)

        # ========== 右侧：用户报文生成区 ==========
        # 添加配置文件选择区域
        config_group = QGroupBox("报文插件配置")
        config_layout = QVBoxLayout(config_group)
        right_layout.addWidget(config_group)

        # 设置报文插件配置区域的固定高度为70像素
        config_group.setFixedHeight(100)

        config_select_layout = QHBoxLayout()
        config_layout.addLayout(config_select_layout)

        config_select_layout.addWidget(QLabel("配置文件:"))
        self.config_path = QLineEdit()
        self.config_path.setReadOnly(True)
        config_select_layout.addWidget(self.config_path)

        self.browse_config_btn = QPushButton("浏览...")
        config_select_layout.addWidget(self.browse_config_btn)

        self.load_config_btn = QPushButton("加载配置")
        config_select_layout.addWidget(self.load_config_btn)

        # 插件选择下拉框
        plugin_layout = QHBoxLayout()
        config_layout.addLayout(plugin_layout)

        plugin_layout.addWidget(QLabel("已加载插件:"))
        self.plugin_combo = QComboBox()
        plugin_layout.addWidget(self.plugin_combo)

        self.load_plugin_btn = QPushButton("加载插件")
        plugin_layout.addWidget(self.load_plugin_btn)

        # 添加插件容器区域
        self.plugin_container = QGroupBox("插件界面区")
        self.plugin_container_layout = QVBoxLayout(self.plugin_container)
        right_layout.addWidget(self.plugin_container)

        # 初始化变量
        self.serial = None
        self.receive_thread = None
        self.message_plugins = {}
        self.current_plugin = None
        self.current_plugin_widget = None
        self.received_count = 0
        self.sent_count = 0
        self.send_queue = MessageSender()

        # 初始化串口列表
        self.update_serial_ports()

        # 连接信号和槽
        self.detect_serial_btn.clicked.connect(self.update_serial_ports)
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.save_log_btn.clicked.connect(self.save_log)
        self.resetCounterBtn.clicked.connect(self.reset_counters)
        self.open_serial_btn.clicked.connect(self.open_serial)
        self.close_serial_btn.clicked.connect(self.close_serial)
        self.quick_send_btn.clicked.connect(self.send_quick_data)
        self.browse_config_btn.clicked.connect(self.browse_config)
        self.load_config_btn.clicked.connect(self.load_config)
        self.load_plugin_btn.clicked.connect(self.load_selected_plugin)
        self.plugin_combo.currentIndexChanged.connect(self.plugin_selected)
        self.send_queue.message_sent.connect(self.on_message_sent)

        # 添加日志显示颜色格式
        self.log_formats = {
            "send": QTextCharFormat(),  # 发送数据颜色
            "receive": QTextCharFormat(),  # 接收数据颜色
            "system": QTextCharFormat(),  # 系统信息颜色
            "error": QTextCharFormat()  # 错误信息颜色
        }

        # 设置不同消息类型的颜色
        self.log_formats["send"].setForeground(QBrush(QColor("blue")))
        self.log_formats["receive"].setForeground(QBrush(QColor("green")))
        self.log_formats["system"].setForeground(QBrush(QColor("gray")))
        self.log_formats["error"].setForeground(QBrush(QColor("red")))

        # 设置系统消息为粗体
        font = QFont()
        font.setBold(True)
        self.log_formats["system"].setFont(font)
        self.log_formats["error"].setFont(font)

    def update_serial_ports(self):
        """更新可用的串口列表"""
        self.serial_port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if ports:
            self.serial_port_combo.addItems(ports)
        else:
            self.serial_port_combo.addItem("无可用串口")

    def clear_log(self):
        """清空日志区域"""
        self.log_display.clear()

    def save_log(self):
        """保存日志到文件"""
        # 弹出保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "", "文本文件 (*.txt);;所有文件 (*.*)")

        if not file_path:
            return

        try:
            # 获取日志文本
            text = self.log_display.toPlainText()

            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)

            self.add_log_message(f"日志已保存到 {file_path}", "system")
        except Exception as e:
            self.add_log_message(f"保存日志失败: {str(e)}", "error")

    def reset_counters(self):
        """重置计数器"""
        self.received_count = 0
        self.sent_count = 0
        self.update_status_counters()
        self.add_log_message("计数器已重置", "system")

    def update_status_counters(self):
        """更新状态栏中的计数器显示"""
        self.receivedCountLabel.setText(f"接收: {self.received_count} 字节")
        self.sentCountLabel.setText(f"发送: {self.sent_count} 字节")

    def open_serial(self):
        """打开串口"""
        try:
            port = self.serial_port_combo.currentText()
            baud_rate = int(self.baud_rate_combo.currentText())
            data_bits = int(self.data_bits_combo.currentText())

            # 设置校验位
            parity_dict = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN,
                           'O': serial.PARITY_ODD, 'M': serial.PARITY_MARK,
                           'S': serial.PARITY_SPACE}
            parity = parity_dict[self.parity_combo.currentText()]

            # 设置停止位
            stop_bits_dict = {'1': serial.STOPBITS_ONE, '1.5': serial.STOPBITS_ONE_POINT_FIVE,
                              '2': serial.STOPBITS_TWO}
            stop_bits = stop_bits_dict[self.stop_bits_combo.currentText()]

            self.serial = serial.Serial(port, baud_rate, bytesize=data_bits,
                                        parity=parity, stopbits=stop_bits, timeout=0.1)

            if self.serial.isOpen():
                self.open_serial_btn.setEnabled(False)
                self.close_serial_btn.setEnabled(True)

                # 添加日志
                self.add_log_message("串口已打开", "system")

                # 更新状态栏
                self.statusLabel.setText(
                    f"串口: {port} ({baud_rate},{data_bits},{self.parity_combo.currentText()},{self.stop_bits_combo.currentText()})")

                # 启动接收线程
                self.receive_thread = SerialReceiveThread(self.serial)
                self.receive_thread.receive_signal.connect(self.process_received_data)
                self.receive_thread.start()

                # 设置定时发送管理器的串口
                self.timed_messages_manager.set_serial(self.serial)

                # 设置发送队列的串口
                self.send_queue.set_serial(self.serial)

                # 如果有活动的插件，通知它串口状态
                if self.current_plugin and hasattr(self.current_plugin, 'set_serial'):
                    self.current_plugin.set_serial(self.serial)
        except Exception as e:
            self.add_log_message(f"打开串口失败: {str(e)}", "error")
            self.statusLabel.setText(f"串口: 连接失败 - {str(e)}")

    def close_serial(self):
        """关闭串口"""
        if self.receive_thread:
            self.receive_thread.stop()
            self.receive_thread = None

        if self.serial and self.serial.isOpen():
            self.serial.close()
            self.open_serial_btn.setEnabled(True)
            self.close_serial_btn.setEnabled(False)
            self.add_log_message("串口已关闭", "system")
            self.statusLabel.setText("串口: 已关闭")

            # 通知定时发送管理器
            self.timed_messages_manager.set_serial(None)

            # 通知发送队列
            self.send_queue.set_serial(None)

            # 如果有活动的插件，通知它串口状态
            if self.current_plugin and hasattr(self.current_plugin, 'set_serial'):
                self.current_plugin.set_serial(None)

    def process_received_data(self, data):
        """处理接收到的数据"""
        try:
            # 更新接收计数
            self.received_count += len(data)
            self.update_status_counters()

            # 添加到日志（包含ASCII和HEX）
            try:
                ascii_text = data.decode('utf-8', errors='replace')
                hex_text = ' '.join([f"{b:02X}" for b in data])

                # 创建日志内容
                log_content = ascii_text
                if self.show_hex.isChecked():
                    log_content += f" [HEX: {hex_text}]"

                # 添加到日志
                self.add_log_message(log_content, "receive")
            except Exception as e:
                self.add_log_message(f"处理接收数据错误: {str(e)}", "error")

            # 如果有活动的插件，通知它接收到的数据
            if self.current_plugin and hasattr(self.current_plugin, 'on_data_received'):
                self.current_plugin.on_data_received(data)

        except Exception as e:
            self.add_log_message(f"处理接收数据错误: {str(e)}", "error")

    def add_log_message(self, message, message_type="system"):
        """添加消息到日志区域

        Args:
            message (str): 日志消息内容
            message_type (str): 消息类型（"send"/"receive"/"system"/"error"）
        """
        # 获取当前光标
        cursor = self.log_display.textCursor()

        # 移动到文档末尾
        cursor.movePosition(QTextCursor.End)

        # 添加时间戳（如果需要）
        if self.show_time.isChecked():
            timestamp = datetime.now().strftime('[%H:%M:%S.%f]')
            cursor.insertText(timestamp + " ")

        # 添加消息类型标签
        type_labels = {
            "send": "[发送] ",
            "receive": "[接收] ",
            "system": "[系统] ",
            "error": "[错误] "
        }

        # 设置消息格式
        cursor.setCharFormat(self.log_formats[message_type])

        # 插入消息类型标签
        cursor.insertText(type_labels.get(message_type, ""))

        # 插入消息内容
        cursor.insertText(message)

        # 添加换行
        cursor.insertText("\n")

        # 如果启用了自动滚动，滚动到底部
        if self.auto_scroll.isChecked():
            self.log_display.setTextCursor(cursor)
            self.log_display.ensureCursorVisible()

    def send_quick_data(self):
        """发送快速发送区域的数据"""
        if not self.serial or not self.serial.isOpen():
            self.add_log_message("串口未打开，无法发送数据", "error")
            return

        try:
            # 从快速发送区获取数据
            send_text = self.quick_send_text.text().strip()
            if not send_text:
                return

            # 移除所有空格
            send_text = send_text.replace(" ", "")

            # 尝试转换十六进制字符串为字节
            try:
                send_bytes = bytes.fromhex(send_text)
            except ValueError:
                self.add_log_message("无效的十六进制数据", "error")
                return

            # 添加到发送队列
            self.send_queue.add_message(send_bytes)

        except Exception as e:
            self.add_log_message(f"发送失败: {str(e)}", "error")

    def on_message_sent(self, message):
        """报文发送完成处理"""
        # 更新发送计数
        self.sent_count += len(message)
        self.update_status_counters()

        # 记录发送信息
        hex_text = ' '.join([f"{b:02X}" for b in message])

        try:
            # 尝试将字节转换为ASCII
            ascii_text = message.decode('utf-8', errors='replace')
            log_content = ascii_text
        except:
            # 如果无法转换，只显示十六进制
            log_content = ""

        # 如果需要显示十六进制，添加到日志内容
        if self.show_hex.isChecked() or not log_content:
            if log_content:
                log_content += f" [HEX: {hex_text}]"
            else:
                log_content = f"HEX: {hex_text}"

        # 添加到日志
        self.add_log_message(log_content, "send")

    def on_timed_message_sent(self, message, name):
        """定时报文发送完成处理"""
        # 更新发送计数
        self.sent_count += len(message)
        self.update_status_counters()

        # 记录发送信息
        hex_text = ' '.join([f"{b:02X}" for b in message])

        try:
            # 尝试将字节转换为ASCII
            ascii_text = message.decode('utf-8', errors='replace')
            log_content = f"{name}: {ascii_text}"
        except:
            # 如果无法转换，只显示十六进制
            log_content = f"{name}"

        # 如果需要显示十六进制，添加到日志内容
        if self.show_hex.isChecked() or not log_content:
            if log_content:
                log_content += f" [HEX: {hex_text}]"
            else:
                log_content = f"{name} [HEX: {hex_text}]"

        # 添加到日志
        self.add_log_message(log_content, "send")

    def browse_config(self):
        """浏览并选择配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择配置文件", "", "INI文件 (*.ini);;所有文件 (*.*)")
        if file_path:
            self.config_path.setText(file_path)

    def load_config(self):
        """加载配置文件并初始化插件列表"""
        config_path = self.config_path.text()
        if not config_path or not os.path.exists(config_path):
            QMessageBox.warning(self, "错误", "请选择有效的配置文件!")
            return

        try:
            # 清空现有插件列表
            self.message_plugins.clear()
            self.plugin_combo.clear()

            # 解析配置文件
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')

            # 获取插件目录
            plugins_dir = config.get('General', 'PluginsDir', fallback='plugins')
            # 确保插件目录是绝对路径
            if not os.path.isabs(plugins_dir):
                base_dir = os.path.dirname(os.path.abspath(config_path))
                plugins_dir = os.path.join(base_dir, plugins_dir)

            # 获取所有可用的插件
            for section in config.sections():
                if section != 'General':
                    plugin_name = section
                    plugin_file = config.get(section, 'File', fallback=None)

                    if plugin_file:
                        # 构建插件的完整路径
                        plugin_path = os.path.join(plugins_dir, plugin_file)

                        if os.path.exists(plugin_path):
                            # 记录插件信息
                            self.message_plugins[plugin_name] = {
                                'path': plugin_path,
                                'module': None,
                                'instance': None
                            }

                            # 添加到下拉菜单
                            self.plugin_combo.addItem(plugin_name)
                        else:
                            self.add_log_message(f"警告: 插件文件不存在: {plugin_path}", "error")

            if self.plugin_combo.count() > 0:
                self.add_log_message(f"成功加载配置文件: {config_path}", "system")
                self.statusBar.showMessage(f"已加载 {self.plugin_combo.count()} 个报文插件", 3000)
            else:
                self.add_log_message(f"警告: 未找到有效的插件配置", "error")
                self.statusBar.showMessage("未找到有效的报文插件", 3000)

        except Exception as e:
            self.add_log_message(f"加载配置文件失败: {str(e)}", "error")
            self.statusBar.showMessage(f"加载配置文件失败: {str(e)}", 3000)

    def plugin_selected(self, index):
        """插件选择改变时的处理"""
        # 仅更新下拉框选择，不加载插件
        pass

    def load_selected_plugin(self):
        """加载选中的插件"""
        # 如果没有选择插件则返回
        if self.plugin_combo.count() == 0:
            return

        # 获取选中的插件名称
        plugin_name = self.plugin_combo.currentText()
        if not plugin_name or plugin_name not in self.message_plugins:
            return

        # 加载插件模块
        try:
            # 清除当前插件界面
            if self.current_plugin_widget:
                self.current_plugin_widget.setParent(None)
                self.current_plugin_widget = None

            plugin_info = self.message_plugins[plugin_name]

            # 如果模块尚未加载，则加载它
            if not plugin_info['module']:
                spec = importlib.util.spec_from_file_location("plugin_module", plugin_info['path'])
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                plugin_info['module'] = module

                # 创建插件实例
                if hasattr(module, 'MessagePlugin'):
                    plugin_info['instance'] = module.MessagePlugin()

                    # 添加对该应用的引用
                    if hasattr(plugin_info['instance'], 'set_app'):
                        plugin_info['instance'].set_app(self)
                else:
                    self.add_log_message(f"错误: 插件 {plugin_name} 缺少 MessagePlugin 类", "error")
                    return

            # 获取插件实例
            self.current_plugin = plugin_info['instance']

            # 如果插件有创建UI的方法，调用它
            if hasattr(self.current_plugin, 'create_ui'):
                self.current_plugin_widget = self.current_plugin.create_ui()
                if self.current_plugin_widget:
                    # 删除所有现有的小部件
                    while self.plugin_container_layout.count():
                        item = self.plugin_container_layout.takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()

                    # 添加新的插件UI
                    self.plugin_container_layout.addWidget(self.current_plugin_widget)

                    # 如果串口已打开，通知插件
                    if self.serial and self.serial.isOpen() and hasattr(self.current_plugin, 'set_serial'):
                        self.current_plugin.set_serial(self.serial)

                    self.add_log_message(f"已加载插件: {plugin_name}", "system")
                    self.statusBar.showMessage(f"已加载插件: {plugin_name}", 3000)
                else:
                    self.add_log_message(f"错误: 插件 {plugin_name} 的create_ui方法未返回有效的Widget", "error")
            else:
                self.add_log_message(f"错误: 插件 {plugin_name} 缺少create_ui方法", "error")

        except Exception as e:
            self.add_log_message(f"加载插件失败: {str(e)}", "error")
            self.statusBar.showMessage(f"加载插件失败: {str(e)}", 3000)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格以获得更好的跨平台外观

    window = SerialToolUI()
    window.show()

    # 创建插件目录（如果不存在）
    plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plugins')
    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)

    # 创建示例配置文件
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'YD-G392.ini')
    if not os.path.exists(config_path):
        create_example_config(config_path)

    sys.exit(app.exec_())


def create_example_config(file_path):
    """创建示例配置文件

    Args:
        file_path (str): 配置文件路径
    """
    config = configparser.ConfigParser()

    # 通用设置
    config['General'] = {
        'PluginsDir': 'plugins'
    }

    # 简单报文插件
    config['简单报文插件'] = {
        'File': 'simple_message_plugin.py'
    }

    # 心跳报文插件
    config['心跳报文插件'] = {
        'File': 'heartbeat_plugin.py'
    }

    # RS485 ICM报文插件
    config['RS485 ICM报文插件'] = {
        'File': 'rs485_icm_message_plugin.py'
    }

    # 通用命令插件
    config['通用命令插件'] = {
        'File': 'command_plugin.py'
    }

    # 写入配置文件
    with open(file_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)


if __name__ == "__main__":
    main()