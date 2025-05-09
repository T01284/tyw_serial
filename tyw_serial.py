# -*- coding: utf-8 -*-
"""
@Author     : 架构修改
@Company    : 黑龙江天有为科技有限公司
@Date       : 2025-05-10
@Python     : 3.10
@Description: 主程序入口，整合所有功能模块
"""

import sys
import os
import time
import json
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QTextEdit, QLineEdit,
                             QGridLayout, QGroupBox, QCheckBox, QSpinBox, QSplitter,
                             QTabWidget, QFileDialog, QMessageBox, QStatusBar, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView, QDialog)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QTextCharFormat, QFont, QIcon
import serial
import serial.tools.list_ports

# 导入自定义模块
from config_parser import ConfigParser
from protocol_ui_generator import ProtocolUIGenerator
from protocol_parser import ProtocolParser
from message_transceiver import MessageSender, MessageReceiver, TimedMessage


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

        # 导入协议报文按钮
        self.import_button = QPushButton("导入协议报文")
        self.import_button.clicked.connect(self.import_from_protocol)
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
        from message_dialog import TimedMessageDialog
        dialog = TimedMessageDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 添加到列表
            self.timed_messages.append(dialog.timed_message)
            # 更新表格
            self.update_table()

    def import_from_protocol(self):
        """从协议中导入报文"""
        # 获取主窗口
        main_window = self.window()

        # 检查是否有已加载的协议
        if not hasattr(main_window, 'protocol_parser') or not main_window.protocol_parser:
            QMessageBox.warning(self, "错误", "请先加载协议配置!")
            return

        # 弹出协议选择对话框
        from message_dialog import ProtocolSelectDialog
        dialog = ProtocolSelectDialog(main_window.config_parser.get_protocols(), self)
        if dialog.exec_() == QDialog.Accepted:
            protocol_id = dialog.selected_protocol
            protocol_data = main_window.config_parser.get_protocol(protocol_id)

            if protocol_id and protocol_data:
                # 创建报文编辑对话框
                from message_dialog import TimedMessageDialog
                message_dialog = TimedMessageDialog(self)

                # 设置协议相关信息
                message_dialog.set_protocol_info(protocol_id, protocol_data)

                if message_dialog.exec_() == QDialog.Accepted:
                    # 添加到列表
                    self.timed_messages.append(message_dialog.timed_message)
                    # 更新表格
                    self.update_table()

    def edit_message(self, row):
        """编辑定时报文"""
        if row < 0 or row >= len(self.timed_messages):
            return

        from message_dialog import TimedMessageDialog
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
            toggle_button =toggle_button = QPushButton("禁用" if message.enabled else "启用")
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
        success = self.message_sender.add_message(message.message, message.name)
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

    def on_message_sent(self, message, name):
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


class MessageDisplayManager(QTabWidget):
    """报文显示管理器，显示所有协议的接收报文"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.protocol_tabs = {}  # 协议标签页字典 {protocol_id: tab_widget}
        self.protocol_data = {}  # 协议数据字典 {protocol_id: protocol_data}
        self.received_messages = {}  # 接收到的报文字典 {protocol_id: [messages]}

    def setup_protocols(self, protocols):
        """
        设置协议信息

        Args:
            protocols (dict): 协议信息字典 {protocol_id: protocol_data}
        """
        # 清空现有标签页
        self.clear()
        self.protocol_tabs.clear()
        self.protocol_data.clear()
        self.received_messages.clear()

        # 添加通用接收标签页
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        # 创建通用接收列表
        self.general_list = QTableWidget(0, 3)
        self.general_list.setHorizontalHeaderLabels(["时间", "协议ID", "内容"])
        self.general_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.general_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.general_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.general_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.general_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        general_layout.addWidget(self.general_list)

        # 添加按钮区域
        button_layout = QHBoxLayout()
        general_layout.addLayout(button_layout)

        # 清空按钮
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_general_list)
        button_layout.addWidget(clear_btn)

        # 解析选中按钮
        parse_btn = QPushButton("解析选中")
        parse_btn.clicked.connect(self.parse_selected_message)
        button_layout.addWidget(parse_btn)

        # 导出按钮
        export_btn = QPushButton("导出日志")
        export_btn.clicked.connect(self.export_general_log)
        button_layout.addWidget(export_btn)

        self.addTab(general_tab, "通用接收")

        # 为每个协议创建标签页
        for protocol_id, protocol_data in protocols.items():
            self.protocol_data[protocol_id] = protocol_data
            self.received_messages[protocol_id] = []

            protocol_tab = QWidget()
            protocol_layout = QVBoxLayout(protocol_tab)

            # 创建协议接收列表
            protocol_list = QTableWidget(0, 4)
            protocol_list.setHorizontalHeaderLabels(["时间", "报文ID", "类型", "字段"])
            protocol_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
            protocol_list.setSelectionBehavior(QAbstractItemView.SelectRows)
            protocol_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            protocol_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            protocol_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            protocol_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
            protocol_layout.addWidget(protocol_list)

            # 添加按钮区域
            button_layout = QHBoxLayout()
            protocol_layout.addLayout(button_layout)

            # 清空按钮
            clear_btn = QPushButton("清空")
            clear_btn.clicked.connect(lambda checked, pid=protocol_id: self.clear_protocol_list(pid))
            button_layout.addWidget(clear_btn)

            # 详情按钮
            detail_btn = QPushButton("查看详情")
            detail_btn.clicked.connect(lambda checked, pid=protocol_id: self.show_message_detail(pid))
            button_layout.addWidget(detail_btn)

            # 复制到发送区按钮
            copy_btn = QPushButton("复制到发送区")
            copy_btn.clicked.connect(lambda checked, pid=protocol_id: self.copy_to_send_area(pid))
            button_layout.addWidget(copy_btn)

            # 导出按钮
            export_btn = QPushButton("导出日志")
            export_btn.clicked.connect(lambda checked, pid=protocol_id: self.export_protocol_log(pid))
            button_layout.addWidget(export_btn)

            # 添加标签页
            protocol_name = protocol_data.get('protocol_name', protocol_id)
            self.addTab(protocol_tab, f"{protocol_id} - {protocol_name}")

            # 保存标签页引用
            self.protocol_tabs[protocol_id] = protocol_list

    def add_general_message(self, timestamp, protocol_id, message_bytes):
        """
        添加通用接收报文

        Args:
            timestamp (str): 时间戳
            protocol_id (str): 协议ID
            message_bytes (bytes): 报文数据
        """
        row = self.general_list.rowCount()
        self.general_list.insertRow(row)

        # 设置时间
        self.general_list.setItem(row, 0, QTableWidgetItem(timestamp))

        # 设置协议ID
        protocol_name = ""
        if protocol_id in self.protocol_data:
            protocol_name = self.protocol_data[protocol_id].get('protocol_name', '')

        protocol_item = QTableWidgetItem(f"{protocol_id}")
        if protocol_name:
            protocol_item.setToolTip(protocol_name)
        self.general_list.setItem(row, 1, protocol_item)

        # 设置内容
        content = " ".join([f"{b:02X}" for b in message_bytes])
        self.general_list.setItem(row, 2, QTableWidgetItem(content))

        # 滚动到最新行
        self.general_list.scrollToBottom()

    def add_protocol_message(self, protocol_id, message_data):
        """
        添加协议解析后的报文

        Args:
            protocol_id (str): 协议ID
            message_data (dict): 解析后的报文数据
        """
        if protocol_id not in self.protocol_tabs:
            return

        # 保存报文数据
        self.received_messages[protocol_id].append(message_data)

        # 获取协议标签页
        protocol_list = self.protocol_tabs[protocol_id]

        # 添加新行
        row = protocol_list.rowCount()
        protocol_list.insertRow(row)

        # 设置时间
        timestamp = message_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        protocol_list.setItem(row, 0, QTableWidgetItem(timestamp))

        # 设置报文ID
        message_id = message_data.get('message_id', '')
        protocol_list.setItem(row, 1, QTableWidgetItem(message_id))

        # 设置类型
        message_type = message_data.get('message_type', '')
        protocol_list.setItem(row, 2, QTableWidgetItem(message_type))

        # 设置字段
        fields = message_data.get('fields', {})
        field_text = ""
        for field_id, field_info in fields.items():
            field_name = field_info.get('name', field_id)
            field_value = field_info.get('value', '')
            description = field_info.get('description', '')

            if description:
                field_text += f"{field_name}: {field_value} ({description}), "
            else:
                field_text += f"{field_name}: {field_value}, "

        if field_text:
            field_text = field_text[:-2]  # 去掉最后的逗号和空格

        protocol_list.setItem(row, 3, QTableWidgetItem(field_text))

        # 滚动到最新行
        protocol_list.scrollToBottom()

        # 高亮显示标签页
        for i in range(self.count()):
            if self.tabText(i).startswith(protocol_id):
                # 如果当前不是这个标签页，设置字体为粗体
                if self.currentIndex() != i:
                    tab_text = self.tabText(i)
                    self.setTabText(i, "* " + tab_text.lstrip("* "))
                break

    def clear_general_list(self):
        """清空通用接收列表"""
        self.general_list.setRowCount(0)

    def clear_protocol_list(self, protocol_id):
        """
        清空指定协议的接收列表

        Args:
            protocol_id (str): 协议ID
        """
        if protocol_id in self.protocol_tabs:
            self.protocol_tabs[protocol_id].setRowCount(0)
            self.received_messages[protocol_id].clear()

    def parse_selected_message(self):
        """解析选中的通用接收报文"""
        selected_rows = self.general_list.selectedItems()
        if not selected_rows:
            return

        # 获取选中行
        row = selected_rows[0].row()

        # 获取报文内容
        content_item = self.general_list.item(row, 2)
        if not content_item:
            return

        try:
            # 将十六进制字符串转换为字节
            hex_content = content_item.text().replace(" ", "")
            message_bytes = bytes.fromhex(hex_content)

            # 解析报文
            main_window = self.window()
            if hasattr(main_window, 'protocol_parser') and main_window.protocol_parser:
                protocol_id, parsed_data = main_window.protocol_parser.parse_message(message_bytes)

                if protocol_id and parsed_data:
                    # 显示解析结果
                    from message_dialog import MessageDetailDialog
                    dialog = MessageDetailDialog(parsed_data, self)
                    dialog.exec_()
                else:
                    QMessageBox.information(self, "解析结果", "无法解析报文，请检查报文格式或加载相应的协议。")
        except Exception as e:
            QMessageBox.warning(self, "解析错误", f"解析报文时出错: {str(e)}")

    def show_message_detail(self, protocol_id):
        """
        显示指定协议报文的详情

        Args:
            protocol_id (str): 协议ID
        """
        if protocol_id not in self.protocol_tabs:
            return

        protocol_list = self.protocol_tabs[protocol_id]
        selected_items = protocol_list.selectedItems()

        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择一条报文记录。")
            return

        # 获取选中行
        row = selected_items[0].row()

        # 获取对应的报文数据
        if row < len(self.received_messages[protocol_id]):
            message_data = self.received_messages[protocol_id][row]

            # 显示详情对话框
            from message_dialog import MessageDetailDialog
            dialog = MessageDetailDialog(message_data, self)
            dialog.exec_()

    def copy_to_send_area(self, protocol_id):
        """
        将选中的报文复制到发送区

        Args:
            protocol_id (str): 协议ID
        """
        if protocol_id not in self.protocol_tabs:
            return

        protocol_list = self.protocol_tabs[protocol_id]
        selected_items = protocol_list.selectedItems()

        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择一条报文记录。")
            return

        # 获取选中行
        row = selected_items[0].row()

        # 获取对应的报文数据
        if row < len(self.received_messages[protocol_id]):
            message_data = self.received_messages[protocol_id][row]

            # 提取原始报文
            raw_message = message_data.get('raw_message', '')

            # 复制到快速发送区
            main_window = self.window()
            if hasattr(main_window, 'quick_send_text'):
                main_window.quick_send_text.setText(raw_message.replace(" ", ""))

                # 添加日志
                if hasattr(main_window, 'add_log_message'):
                    main_window.add_log_message("报文已复制到快速发送区", "system")
            else:
                QMessageBox.information(self, "提示", f"报文已复制，但未找到快速发送区。\n\n报文内容：{raw_message}")

    def export_general_log(self):
        """导出通用接收日志"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出接收日志", "", "文本文件 (*.txt);;CSV文件 (*.csv);;所有文件 (*.*)")

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入标题
                if file_path.lower().endswith('.csv'):
                    f.write("时间,协议ID,内容\n")
                else:
                    f.write("时间\t协议ID\t内容\n")

                # 写入数据
                for row in range(self.general_list.rowCount()):
                    time_item = self.general_list.item(row, 0)
                    protocol_item = self.general_list.item(row, 1)
                    content_item = self.general_list.item(row, 2)

                    if time_item and protocol_item and content_item:
                        if file_path.lower().endswith('.csv'):
                            f.write(f"{time_item.text()},{protocol_item.text()},{content_item.text()}\n")
                        else:
                            f.write(f"{time_item.text()}\t{protocol_item.text()}\t{content_item.text()}\n")

            QMessageBox.information(self, "导出成功", f"日志已导出到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出日志失败: {str(e)}")

    def export_protocol_log(self, protocol_id):
        """
        导出指定协议的接收日志

        Args:
            protocol_id (str): 协议ID
        """
        if protocol_id not in self.protocol_tabs:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, f"导出 {protocol_id} 接收日志", "", "文本文件 (*.txt);;CSV文件 (*.csv);;所有文件 (*.*)")

        if not file_path:
            return

        try:
            protocol_list = self.protocol_tabs[protocol_id]

            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入标题
                if file_path.lower().endswith('.csv'):
                    f.write("时间,报文ID,类型,字段\n")
                else:
                    f.write("时间\t报文ID\t类型\t字段\n")

                # 写入数据
                for row in range(protocol_list.rowCount()):
                    time_item = protocol_list.item(row, 0)
                    message_id_item = protocol_list.item(row, 1)
                    type_item = protocol_list.item(row, 2)
                    fields_item = protocol_list.item(row, 3)

                    if time_item and message_id_item and type_item and fields_item:
                        if file_path.lower().endswith('.csv'):
                            f.write(f"{time_item.text()},{message_id_item.text()},{type_item.text()},\"{fields_item.text()}\"\n")
                        else:
                            f.write(f"{time_item.text()}\t{message_id_item.text()}\t{type_item.text()}\t{fields_item.text()}\n")

            QMessageBox.information(self, "导出成功", f"日志已导出到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出日志失败: {str(e)}")

    def tabChanged(self, index):
        """
        标签页切换事件

        Args:
            index (int): 新的标签页索引
        """
        # 获取当前标签页的标题
        tab_text = self.tabText(index)

        # 去掉提醒标记
        if tab_text.startswith("* "):
            clean_text = tab_text[2:]
            self.setTabText(index, clean_text)
class SerialToolUI(QMainWindow):
    """串口通信工具主窗口"""

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
        self.resetCounterBtn.clicked.connect(self.reset_counters)
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
        left_widget.setFixedWidth(500)  # 设置左侧区域固定宽度为400px
        left_layout = QVBoxLayout(left_widget)
        main_splitter.addWidget(left_widget)

        # ========== 右侧区域（协议生成区）==========
        right_widget = QWidget()
        # 右侧区域不设置固定宽度，让它自动填充剩余空间
        right_layout = QVBoxLayout(right_widget)
        main_splitter.addWidget(right_widget)

        # 设置左右分割比例 - 不再需要明确设置，因为左侧已固定宽度
        # main_splitter.setSizes([400, 800])  # 左侧400px，右侧800px

        # 禁用分割器移动 - 可选，如果要保持左侧宽度完全固定
        main_splitter.setCollapsible(0, False)  # 禁止左侧区域收缩

        # ========== 左侧顶部：串口设置 ==========
        serial_config_group = QGroupBox("串口设置")
        serial_config_layout = QGridLayout(serial_config_group)
        left_layout.addWidget(serial_config_group)

        # 串口检测按钮
        self.detect_serial_btn = QPushButton("检测串口")
        self.detect_serial_btn.clicked.connect(self.update_serial_ports)
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
        self.open_serial_btn.clicked.connect(self.open_serial)
        self.close_serial_btn = QPushButton("关闭串口")
        self.close_serial_btn.clicked.connect(self.close_serial)
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

        # ========== 右侧：协议配置区 ==========
        # 添加配置文件选择区域
        config_group = QGroupBox("协议配置")
        config_layout = QVBoxLayout(config_group)
        right_layout.addWidget(config_group)

        # 设置协议配置区域的固定高度
        config_group.setFixedHeight(100)

        # 配置文件选择区域
        config_select_layout = QHBoxLayout()
        config_layout.addLayout(config_select_layout)

        config_select_layout.addWidget(QLabel("配置文件:"))
        self.config_path = QLineEdit()
        self.config_path.setReadOnly(True)
        config_select_layout.addWidget(self.config_path)

        self.browse_config_btn = QPushButton("浏览...")
        self.browse_config_btn.clicked.connect(self.browse_config)
        config_select_layout.addWidget(self.browse_config_btn)

        self.load_config_btn = QPushButton("加载配置")
        self.load_config_btn.clicked.connect(self.load_config)
        config_select_layout.addWidget(self.load_config_btn)

        # 协议信息区域
        protocol_info_layout = QHBoxLayout()
        config_layout.addLayout(protocol_info_layout)

        protocol_info_layout.addWidget(QLabel("已加载协议:"))
        self.protocol_count_label = QLabel("0")
        protocol_info_layout.addWidget(self.protocol_count_label)

        protocol_info_layout.addWidget(QLabel("支持报文ID:"))
        self.message_ids_label = QLabel("")
        protocol_info_layout.addWidget(self.message_ids_label)
        protocol_info_layout.addStretch()

        # ========== 协议生成与接收区 ==========
        # 使用选项卡分离生成和接收
        self.protocol_tabs = QTabWidget()
        right_layout.addWidget(self.protocol_tabs)

        # 创建生成选项卡
        self.generate_tab = QTabWidget()
        self.protocol_tabs.addTab(self.generate_tab, "报文生成")

        # 创建接收选项卡
        self.message_display_manager = MessageDisplayManager()
        self.message_display_manager.currentChanged.connect(self.message_display_manager.tabChanged)
        self.protocol_tabs.addTab(self.message_display_manager, "报文接收")

        # 初始化变量
        self.serial = None
        self.receive_thread = None
        self.config_parser = ConfigParser()
        self.protocol_ui_generator = ProtocolUIGenerator()
        self.protocol_parser = ProtocolParser()
        self.message_receiver = MessageReceiver()
        self.received_count = 0
        self.sent_count = 0
        self.send_queue = MessageSender()
        self.protocol_widgets = {}  # 协议生成界面 {protocol_id: widget}

        # 初始化串口列表
        self.update_serial_ports()

        # 连接信号和槽
        self.send_queue.message_sent.connect(self.on_message_sent)
        self.message_receiver.message_received.connect(self.on_message_received)
        self.protocol_parser.message_parsed.connect(self.on_message_parsed)


    def update_serial_ports(self):
        """更新可用的串口列表"""
        self.serial_port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if ports:
            self.serial_port_combo.addItems(ports)
        else:
            self.serial_port_combo.addItem("无可用串口")


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


    def browse_config(self):
        """浏览并选择配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择配置文件", "", "INI文件 (*.ini);;所有文件 (*.*)")
        if file_path:
            self.config_path.setText(file_path)


    def load_config(self):
        """加载配置文件和协议"""
        config_path = self.config_path.text()
        if not config_path or not os.path.exists(config_path):
            QMessageBox.warning(self, "错误", "请选择有效的配置文件!")
            return

        try:
            # 加载配置
            success = self.config_parser.load_config(config_path)
            if not success:
                QMessageBox.warning(self, "错误", "加载配置文件失败!")
                return

            # 获取协议
            protocols = self.config_parser.get_protocols()
            if not protocols:
                QMessageBox.warning(self, "错误", "未找到有效的协议配置!")
                return

            # 清空现有协议界面
            self.clear_protocols()

            # 设置协议解析器
            self.protocol_parser.set_protocols(protocols)

            # 设置报文显示管理器
            self.message_display_manager.setup_protocols(protocols)

            # 为每个协议创建界面
            for protocol_id, protocol_data in protocols.items():
                # 创建协议界面
                protocol_widget = self.protocol_ui_generator.generate_protocol_widget(protocol_data)
                if protocol_widget:
                    # 添加到生成选项卡
                    self.generate_tab.addTab(protocol_widget, protocol_id)

                    # 保存界面引用
                    self.protocol_widgets[protocol_id] = protocol_widget

                    # 连接界面上的按钮
                    self.connect_protocol_buttons(protocol_widget, protocol_id)

            # 更新协议信息
            self.protocol_count_label.setText(str(len(protocols)))
            message_ids = ", ".join([protocol_data.get('message_id', '') for protocol_data in protocols.values()])
            self.message_ids_label.setText(message_ids)

            # 添加日志
            self.add_log_message(f"已加载 {len(protocols)} 个协议", "system")
           # self.statusBar().showMessage(f"已加载 {len(protocols)} 个协议", 3000)

        except Exception as e:
            self.add_log_message(f"加载配置文件失败: {str(e)}", "error")
            self.statusBar().showMessage(f"加载配置文件失败: {str(e)}", 3000)


    def clear_protocols(self):
        """清空所有协议界面"""
        # 清空生成选项卡
        while self.generate_tab.count() > 0:
            self.generate_tab.removeTab(0)

        # 清空界面引用
        self.protocol_widgets.clear()


    def connect_protocol_buttons(self, protocol_widget, protocol_id):
        """
        连接协议界面上的按钮事件

        Args:
            protocol_widget (QWidget): 协议界面
            protocol_id (str): 协议ID
        """
        # 查找生成报文按钮
        generate_btn = protocol_widget.findChild(QPushButton, "generate_btn")
        if not generate_btn:
            # 查找所有按钮
            buttons = protocol_widget.findChildren(QPushButton)
            for btn in buttons:
                if btn.text() == "生成报文":
                    generate_btn = btn
                    break

        if generate_btn:
            generate_btn.clicked.connect(lambda: self.generate_protocol_message(protocol_id))

        # 查找复制到发送区按钮
        copy_to_send_btn = protocol_widget.findChild(QPushButton, "copy_to_send_btn")
        if not copy_to_send_btn:
            # 查找所有按钮
            buttons = protocol_widget.findChildren(QPushButton)
            for btn in buttons:
                if btn.text() == "复制到发送区":
                    copy_to_send_btn = btn
                    break

        if copy_to_send_btn:
            copy_to_send_btn.clicked.connect(lambda: self.copy_to_send_area(protocol_id))

        # 查找保存配置按钮
        save_config_btn = protocol_widget.findChild(QPushButton, "save_config_btn")
        if not save_config_btn:
            # 查找所有按钮
            buttons = protocol_widget.findChildren(QPushButton)
            for btn in buttons:
                if btn.text() == "保存配置":
                    save_config_btn = btn
                    break

        if save_config_btn:
            save_config_btn.clicked.connect(lambda: self.save_protocol_config(protocol_id))

        # 查找加载配置按钮
        load_config_btn = protocol_widget.findChild(QPushButton, "load_config_btn")
        if not load_config_btn:
            # 查找所有按钮
            buttons = protocol_widget.findChildren(QPushButton)
            for btn in buttons:
                if btn.text() == "加载配置":
                    load_config_btn = btn
                    break

        if load_config_btn:
            load_config_btn.clicked.connect(lambda: self.load_protocol_config(protocol_id))


    def generate_protocol_message(self, protocol_id):
        """
        生成协议报文

        Args:
            protocol_id (str): 协议ID
        """
        try:
            # 获取字段值
            field_values = self.protocol_ui_generator.get_field_values()

            # 生成报文
            message = self.protocol_parser.generate_message(protocol_id, field_values)

            if message:
                # 弹出报文预览对话框
                from message_dialog import MessagePreviewDialog
                dialog = MessagePreviewDialog(message, protocol_id, self)
                if dialog.exec_() == QDialog.Accepted:
                    # 发送报文
                    self.send_message(message, f"{protocol_id}报文")
                    self.add_log_message(f"已发送{protocol_id}报文", "system")
            else:
                QMessageBox.warning(self, "错误", "生成报文失败，请检查字段值!")
        except Exception as e:
            self.add_log_message(f"生成报文错误: {str(e)}", "error")


    def copy_to_send_area(self, protocol_id):
        """
        将协议报文复制到发送区

        Args:
            protocol_id (str): 协议ID
        """
        try:
            # 获取字段值
            field_values = self.protocol_ui_generator.get_field_values()

            # 生成报文
            message = self.protocol_parser.generate_message(protocol_id, field_values)

            if message:
                # 转换为十六进制字符串
                hex_str = ''.join([f"{b:02X}" for b in message])

                # 复制到快速发送区
                self.quick_send_text.setText(hex_str)

                # 添加日志
                self.add_log_message("报文已复制到快速发送区", "system")
            else:
                QMessageBox.warning(self, "错误", "生成报文失败，请检查字段值!")
        except Exception as e:
            self.add_log_message(f"复制报文错误: {str(e)}", "error")


    def save_protocol_config(self, protocol_id):
        """
        保存协议配置

        Args:
            protocol_id (str): 协议ID
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"保存 {protocol_id} 配置", "", "JSON文件 (*.json);;所有文件 (*.*)")

        if not file_path:
            return

        try:
            # 获取字段值
            field_values = self.protocol_ui_generator.get_field_values()

            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(field_values, f, indent=4, ensure_ascii=False)

            self.add_log_message(f"{protocol_id}配置已保存到 {file_path}", "system")
        except Exception as e:
            self.add_log_message(f"保存配置失败: {str(e)}", "error")


    def load_protocol_config(self, protocol_id):
        """
        加载协议配置

        Args:
            protocol_id (str): 协议ID
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"加载 {protocol_id} 配置", "", "JSON文件 (*.json);;所有文件 (*.*)")

        if not file_path:
            return

        try:
            # 从文件加载
            with open(file_path, 'r', encoding='utf-8') as f:
                field_values = json.load(f)

            # 设置字段值
            self.protocol_ui_generator.set_field_values(field_values)

            self.add_log_message(f"已加载 {protocol_id} 配置", "system")
        except Exception as e:
            self.add_log_message(f"加载配置失败: {str(e)}", "error")


    def process_received_data(self, data):
        """
        处理接收到的数据

        Args:
            data (bytes): 接收到的数据
        """
        # 更新接收计数
        self.received_count += len(data)
        self.update_status_counters()

        # 添加到日志
        try:
            # 尝试转换为ASCII
            ascii_text = data.decode('utf-8', errors='replace')
            # 十六进制表示
            hex_text = ' '.join([f"{b:02X}" for b in data])

            # 创建日志内容
            log_content = ascii_text
            if self.show_hex.isChecked():
                log_content += f" [HEX: {hex_text}]"

            # 添加到日志
            self.add_log_message(log_content, "receive")
        except Exception as e:
            self.add_log_message(f"处理接收数据错误: {str(e)}", "error")

        # 交给报文接收器处理
        self.message_receiver.process_data(data)


    def on_message_received(self, message):
        """
        报文接收完成处理

        Args:
            message (bytes): 接收到的完整报文
        """
        # 尝试解析报文
        protocol_id, parsed_data = self.protocol_parser.parse_message(message)

        # 添加到通用接收列表
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        self.message_display_manager.add_general_message(timestamp, protocol_id or "未知", message)


    def on_message_parsed(self, protocol_id, parsed_data):
        """
        报文解析完成处理

        Args:
            protocol_id (str): 协议ID
            parsed_data (dict): 解析后的报文数据
        """
        # 添加到协议接收列表
        self.message_display_manager.add_protocol_message(protocol_id, parsed_data)

        # 添加日志
        message_id = parsed_data.get('message_id', '')
        message_type = parsed_data.get('message_type', '')
        self.add_log_message(f"接收到 {protocol_id} 报文 - ID: {message_id}, 类型: {message_type}", "system")


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

            # 发送数据
            self.send_message(send_bytes, "快速发送")

        except Exception as e:
            self.add_log_message(f"发送失败: {str(e)}", "error")


    def send_message(self, message, name=''):
        """
        发送报文

        Args:
            message (bytes): 要发送的报文
            name (str): 报文名称
        """
        self.send_queue.add_message(message, name)


    def on_message_sent(self, message, name):
        """
        报文发送完成处理

        Args:
            message (bytes): 发送的报文
            name (str): 报文名称
        """
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
        if self.show_hex.isChecked():
            log_content += f" [HEX: {hex_text}]"

        # 添加到日志
        self.add_log_message(log_content, "send")


    def on_timed_message_sent(self, message, name):
        """
        定时报文发送完成处理

        Args:
            message (bytes): 发送的报文
            name (str): 报文名称
        """
        # 直接调用通用发送完成处理
        self.on_message_sent(message, name)


    def add_log_message(self, message, message_type="system"):
        """
        添加消息到日志区域

        Args:
            message (str): 日志消息内容
            message_type (str): 消息类型（"send"/"receive"/"system"/"error"）
        """
        # 获取当前光标
        cursor = self.log_display.textCursor()

        # 移动到文档末尾
        #cursor.movePosition(QTextCursor.End)

        # 添加时间戳（如果需要）
        if self.show_time.isChecked():
            timestamp = datetime.now().strftime('[%H:%M:%S.%f]')[:-3]
            cursor.insertText(timestamp + " ")

        # 添加消息类型标签
        type_labels = {
            "send": "[发送] ",
            "receive": "[接收] ",
            "system": "[系统] ",
            "error": "[错误] "
        }

        # 创建消息格式
        format = QTextCharFormat()

        # 设置不同消息类型的颜色
        if message_type == "send":
            format.setForeground(QBrush(QColor("blue")))
        elif message_type == "receive":
            format.setForeground(QBrush(QColor("green")))
        elif message_type == "system":
            format.setForeground(QBrush(QColor("gray")))

            # 系统消息使用粗体
            font = QFont()
            font.setBold(True)
            format.setFont(font)
        elif message_type == "error":
            format.setForeground(QBrush(QColor("red")))

            # 错误消息使用粗体
            font = QFont()
            font.setBold(True)
            format.setFont(font)

        # 插入消息类型标签
        cursor.setCharFormat(format)
        cursor.insertText(type_labels.get(message_type, ""))

        # 插入消息内容
        cursor.insertText(message)

        # 添加换行
        cursor.insertText("\n")

        # 如果启用了自动滚动，滚动到底部
        if self.auto_scroll.isChecked():
            self.log_display.setTextCursor(cursor)
            self.log_display.ensureCursorVisible()


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


    def closeEvent(self, event):
        """关闭窗口事件处理"""
        # 关闭串口
        self.close_serial()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格以获得更好的跨平台外观

    window = SerialToolUI()
    window.show()

    # 创建示例配置文件
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'YD-G392.ini')
    if not os.path.exists(config_path):
        create_example_config(config_path)

    sys.exit(app.exec_())


def create_example_config(file_path):
    """
    创建示例配置文件

    Args:
        file_path (str): 配置文件路径
    """
    config = configparser.ConfigParser()

    # 通用设置
    config['General'] = {
        'pluginsdir': 'plugins'
    }

    # D0h报文协议
    config['D0h'] = {
        'file': 'yd_g392_d0h.json'
    }

    # D1h报文协议
    config['D1h'] = {
        'file': 'yd_g392_d1h.json'
    }

    # 写入配置文件
    with open(file_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)


if __name__ == "__main__":
    main()