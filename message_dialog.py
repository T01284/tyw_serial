# -*- coding: utf-8 -*-
"""
@Author     : 架构修改
@Company    : 黑龙江天有为科技有限公司
@Date       : 2025-05-10
@Python     : 3.10
@Description: 消息对话框模块，包含各种用于报文处理的对话框
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox,
                             QGroupBox, QCheckBox, QSpinBox, QTextEdit, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QDialogButtonBox, QFormLayout, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QRegExpValidator, QIntValidator, QDoubleValidator, QColor, QBrush, QFont, QValidator
from message_transceiver import TimedMessage


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

    def set_protocol_info(self, protocol_id, protocol_data):
        """
        设置协议相关信息

        Args:
            protocol_id (str): 协议ID
            protocol_data (dict): 协议数据
        """
        # 设置报文名称
        protocol_name = protocol_data.get('protocol_name', '')
        message_id = protocol_data.get('message_id', '')
        self.name_edit.setText(f"{protocol_id} - {message_id} - {protocol_name}")

        # 保存协议ID
        self.timed_message.protocol_id = protocol_id

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


class MessageDetailDialog(QDialog):
    """报文详情对话框"""

    def __init__(self, message_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("报文详情")
        self.resize(700, 500)
        self.message_data = message_data
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 添加协议信息区域
        info_group = QGroupBox("协议信息")
        info_layout = QGridLayout(info_group)
        layout.addWidget(info_group)

        # 获取协议信息
        protocol_id = self.message_data.get('protocol_id', '')
        protocol_name = self.message_data.get('protocol_name', '')
        message_id = self.message_data.get('message_id', '')
        message_type = self.message_data.get('message_type', '')
        timestamp = self.message_data.get('timestamp', '')
        raw_message = self.message_data.get('raw_message', '')

        # 显示协议信息
        info_layout.addWidget(QLabel("协议ID:"), 0, 0)
        info_layout.addWidget(QLabel(protocol_id), 0, 1)
        info_layout.addWidget(QLabel("协议名称:"), 0, 2)
        info_layout.addWidget(QLabel(protocol_name), 0, 3)
        info_layout.addWidget(QLabel("报文ID:"), 1, 0)
        info_layout.addWidget(QLabel(message_id), 1, 1)
        info_layout.addWidget(QLabel("报文类型:"), 1, 2)
        info_layout.addWidget(QLabel(message_type), 1, 3)
        info_layout.addWidget(QLabel("接收时间:"), 2, 0)
        info_layout.addWidget(QLabel(timestamp), 2, 1)

        # 添加原始报文区域
        raw_group = QGroupBox("原始报文")
        raw_layout = QVBoxLayout(raw_group)
        layout.addWidget(raw_group)

        # 显示原始报文
        raw_text = QTextEdit()
        raw_text.setPlainText(raw_message)
        raw_text.setReadOnly(True)
        raw_layout.addWidget(raw_text)

        # 创建字段信息表格
        fields_group = QGroupBox("字段解析")
        fields_layout = QVBoxLayout(fields_group)
        layout.addWidget(fields_group)

        # 字段表格
        self.fields_table = QTableWidget(0, 5)
        self.fields_table.setHorizontalHeaderLabels(["字段ID", "字段名称", "值", "十六进制", "描述"])
        self.fields_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.fields_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.fields_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.fields_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.fields_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.fields_table.setAlternatingRowColors(True)
        fields_layout.addWidget(self.fields_table)

        # 填充字段表格
        self.fill_fields_table()

        # 按钮区域
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        # 复制按钮
        copy_btn = QPushButton("复制报文")
        copy_btn.clicked.connect(self.copy_message)
        button_layout.addWidget(copy_btn)

        # 导出按钮
        export_btn = QPushButton("导出详情")
        export_btn.clicked.connect(self.export_details)
        button_layout.addWidget(export_btn)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

    def fill_fields_table(self):
        """填充字段表格"""
        fields = self.message_data.get('fields', {})
        if not fields:
            return

        # 设置表格行数
        self.fields_table.setRowCount(len(fields))

        # 填充表格
        for i, (field_id, field_info) in enumerate(fields.items()):
            # 字段ID
            self.fields_table.setItem(i, 0, QTableWidgetItem(field_id))

            # 字段名称
            field_name = field_info.get('name', '')
            self.fields_table.setItem(i, 1, QTableWidgetItem(field_name))

            # 字段值
            field_value = field_info.get('value', '')
            self.fields_table.setItem(i, 2, QTableWidgetItem(str(field_value)))

            # 十六进制值
            hex_value = field_info.get('hex', '')
            self.fields_table.setItem(i, 3, QTableWidgetItem(hex_value))

            # 描述
            description = field_info.get('description', '')
            self.fields_table.setItem(i, 4, QTableWidgetItem(description))

    def copy_message(self):
        """复制报文到剪贴板"""
        raw_message = self.message_data.get('raw_message', '')
        if raw_message:
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(raw_message.replace(" ", ""))
            QMessageBox.information(self, "提示", "报文已复制到剪贴板")
        else:
            QMessageBox.warning(self, "错误", "无有效报文可复制")

    def export_details(self):
        """导出报文详情"""
        from PyQt5.QtWidgets import QFileDialog
        import json

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出报文详情", "", "JSON文件 (*.json);;文本文件 (*.txt);;所有文件 (*.*)")

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.message_data, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "成功", f"报文详情已导出到 {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


class MessagePreviewDialog(QDialog):
    """报文预览对话框"""

    def __init__(self, message, protocol_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{protocol_id}报文预览")
        self.resize(500, 300)
        self.message = message
        self.protocol_id = protocol_id
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 显示报文信息
        info_layout = QGridLayout()
        layout.addLayout(info_layout)

        info_layout.addWidget(QLabel("协议ID:"), 0, 0)
        info_layout.addWidget(QLabel(self.protocol_id), 0, 1)
        info_layout.addWidget(QLabel("报文长度:"), 0, 2)
        info_layout.addWidget(QLabel(str(len(self.message)) + " 字节"), 0, 3)

        # 报文内容
        layout.addWidget(QLabel("报文内容(十六进制):"))
        message_text = QTextEdit()
        hex_text = ' '.join([f"{b:02X}" for b in self.message])
        message_text.setPlainText(hex_text)
        message_text.setReadOnly(True)
        layout.addWidget(message_text)

        # 按钮区域
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        # 复制按钮
        copy_btn = QPushButton("复制报文")
        copy_btn.clicked.connect(self.copy_message)
        button_layout.addWidget(copy_btn)

        # 发送按钮
        send_btn = QPushButton("发送报文")
        send_btn.clicked.connect(self.accept)
        button_layout.addWidget(send_btn)

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

    def copy_message(self):
        """复制报文到剪贴板"""
        if self.message:
            from PyQt5.QtWidgets import QApplication
            hex_text = ''.join([f"{b:02X}" for b in self.message])
            QApplication.clipboard().setText(hex_text)
            QMessageBox.information(self, "提示", "报文已复制到剪贴板")


class ProtocolSelectDialog(QDialog):
    """协议选择对话框"""

    def __init__(self, protocols, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择协议")
        self.resize(400, 300)
        self.protocols = protocols
        self.selected_protocol = None
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 添加说明标签
        layout.addWidget(QLabel("请选择要导入的协议:"))

        # 协议列表
        self.protocol_list = QListWidget()
        for protocol_id, protocol_data in self.protocols.items():
            protocol_name = protocol_data.get('protocol_name', '')
            message_id = protocol_data.get('message_id', '')
            item = QListWidgetItem(f"{protocol_id} - {message_id} - {protocol_name}")
            item.setData(Qt.UserRole, protocol_id)
            self.protocol_list.addItem(item)
        layout.addWidget(self.protocol_list)

        # 设置默认选中第一项
        if self.protocol_list.count() > 0:
            self.protocol_list.setCurrentRow(0)

        # 按钮区域
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        def accept(self):
            """确认按钮点击事件"""
            current_item = self.protocol_list.currentItem()
            if current_item:
                self.selected_protocol = current_item.data(Qt.UserRole)
                super().accept()
            else:
                QMessageBox.warning(self, "错误", "请选择一个协议!")

    class HexValidator(QValidator):
        """十六进制字符串验证器"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.regex = QRegExp("^[0-9A-Fa-f\\s]*$")

        def validate(self, input_str, pos):
            """验证输入"""
            # 允许空字符串
            if not input_str:
                return QValidator.Acceptable, input_str, pos

            # 检查是否只包含十六进制字符和空格
            if self.regex.exactMatch(input_str):
                # 检查转换为字节是否有效
                try:
                    # 移除所有空格
                    hex_str = input_str.replace(" ", "")

                    # 如果长度为奇数，最后一个字符不完整
                    if len(hex_str) % 2 != 0 and pos == len(input_str):
                        return QValidator.Intermediate, input_str, pos

                    # 尝试转换为字节
                    bytes.fromhex(hex_str)
                    return QValidator.Acceptable, input_str, pos
                except:
                    return QValidator.Invalid, input_str, pos

            return QValidator.Invalid, input_str, pos

    class BatchMessagesDialog(QDialog):
        """批量报文导入对话框"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("批量导入报文")
            self.resize(700, 500)
            self.timed_messages = []
            self.init_ui()

        def init_ui(self):
            """初始化UI"""
            layout = QVBoxLayout(self)

            # 添加说明标签
            layout.addWidget(QLabel("请按行粘贴报文，每行一条报文，格式: 名称,报文内容(十六进制),间隔(ms),是否启用(0/1)"))

            # 文本编辑区域
            self.text_edit = QTextEdit()
            layout.addWidget(self.text_edit)

            # 示例按钮
            example_btn = QPushButton("插入示例")
            example_btn.clicked.connect(self.insert_example)
            layout.addWidget(example_btn)

            # 按钮区域
            button_layout = QHBoxLayout()
            layout.addLayout(button_layout)

            # 解析按钮
            parse_btn = QPushButton("解析报文")
            parse_btn.clicked.connect(self.parse_messages)
            button_layout.addWidget(parse_btn)

            # 导入按钮
            self.import_btn = QPushButton("导入")
            self.import_btn.setEnabled(False)
            self.import_btn.clicked.connect(self.accept)
            button_layout.addWidget(self.import_btn)

            # 取消按钮
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(cancel_btn)

            # 创建报文表格
            self.message_table = QTableWidget(0, 5)
            self.message_table.setHorizontalHeaderLabels(["名称", "内容", "间隔(ms)", "启用", "有效性"])
            self.message_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.message_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.message_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.message_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.message_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
            self.message_table.setAlternatingRowColors(True)
            layout.addWidget(self.message_table)

        def insert_example(self):
            """插入示例数据"""
            example_text = """报文1,59 44 D0 0E 00 00 00 00 00 00 E0 FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF,1000,1
        报文2,59 44 D4 0E 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00,2000,0"""
            self.text_edit.setPlainText(example_text)

        def parse_messages(self):
            """解析报文"""
            # 获取文本内容
            text = self.text_edit.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "错误", "请输入报文内容!")
                return

            # 清空报文列表和表格
            self.timed_messages.clear()
            self.message_table.setRowCount(0)

            # 按行解析
            lines = text.split('\n')
            valid_count = 0

            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                # 尝试解析
                parts = line.split(',')
                if len(parts) < 2:
                    self.add_message_row(i, line, None, None, None, "格式错误", False)
                    continue

                # 提取各部分
                name = parts[0].strip()
                hex_content = parts[1].strip()

                # 设置默认值
                interval = 1000
                enabled = False

                # 解析间隔
                if len(parts) >= 3:
                    try:
                        interval = int(parts[2].strip())
                        # 限制间隔范围
                        if interval < 10:
                            interval = 10
                        elif interval > 60000:
                            interval = 60000
                    except:
                        pass

                # 解析启用状态
                if len(parts) >= 4:
                    try:
                        enabled = bool(int(parts[3].strip()))
                    except:
                        pass

                # 解析报文内容
                try:
                    # 移除所有空格
                    hex_str = hex_content.replace(" ", "")
                    message = bytes.fromhex(hex_str)

                    # 创建定时报文对象
                    timed_message = TimedMessage(
                        name=name,
                        message=message,
                        interval=interval,
                        enabled=enabled
                    )

                    # 添加到列表
                    self.timed_messages.append(timed_message)

                    # 添加到表格
                    self.add_message_row(i, name, message, interval, enabled, "有效", True)
                    valid_count += 1
                except Exception as e:
                    self.add_message_row(i, name, None, interval, enabled, f"无效: {str(e)}", False)

            # 更新导入按钮状态
            self.import_btn.setEnabled(valid_count > 0)

            # 显示解析结果
            QMessageBox.information(self, "解析结果", f"共解析 {len(lines)} 行，有效报文 {valid_count} 条。")

        def add_message_row(self, row, name, message, interval, enabled, status, valid):
            """添加报文行到表格"""
            # 插入新行
            table_row = self.message_table.rowCount()
            self.message_table.insertRow(table_row)

            # 设置名称
            self.message_table.setItem(table_row, 0, QTableWidgetItem(name))

            # 设置内容
            if message:
                content = " ".join([f"{b:02X}" for b in message])
                if len(content) > 30:
                    content = content[:30] + "..."
                self.message_table.setItem(table_row, 1, QTableWidgetItem(content))
            else:
                self.message_table.setItem(table_row, 1, QTableWidgetItem("无效"))

            # 设置间隔
            if interval is not None:
                self.message_table.setItem(table_row, 2, QTableWidgetItem(str(interval)))
            else:
                self.message_table.setItem(table_row, 2, QTableWidgetItem(""))

            # 设置启用状态
            if enabled is not None:
                self.message_table.setItem(table_row, 3, QTableWidgetItem("是" if enabled else "否"))
            else:
                self.message_table.setItem(table_row, 3, QTableWidgetItem(""))

            # 设置有效性
            status_item = QTableWidgetItem(status)
            if valid:
                status_item.setForeground(QBrush(QColor("green")))
            else:
                status_item.setForeground(QBrush(QColor("red")))
            self.message_table.setItem(table_row, 4, status_item)