# -*- coding: utf-8 -*-
"""
@Author     : 架构修改
@Company    : 黑龙江天有为科技有限公司
@Date       : 2025-05-10
@Python     : 3.10
@Description: 协议界面生成模块，根据JSON协议文件自动生成界面元素
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox,
                             QGroupBox, QCheckBox, QSpinBox, QTextEdit, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QDoubleSpinBox, QFrame, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QRegExp
from PyQt5.QtGui import QRegExpValidator, QIntValidator, QDoubleValidator, QColor, QBrush, QFont, QValidator



class FieldInputWidget(QWidget):
    """字段输入控件，根据字段类型生成相应的输入控件"""

    valueChanged = pyqtSignal(str, object)  # 值变更信号 (field_id, value)

    def __init__(self, field_info, parent=None):
        super().__init__(parent)
        self.field_info = field_info
        self.field_id = field_info.get('id', '')
        self.field_name = field_info.get('name', '')
        self.field_type = field_info.get('type', 'Unsigned')
        self.min_value = field_info.get('min_value', 0)
        self.max_value = field_info.get('max_value', 0)
        self.precision = field_info.get('precision', 1)
        self.offset = field_info.get('offset', 0)
        self.unit = field_info.get('unit', '')
        self.values = field_info.get('values', [])

        # 使用网格布局代替垂直布局，便于控制对齐
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)  # 减少间距
        self.layout.setVerticalSpacing(2)  # 减少垂直间距

        # 创建输入控件
        self.create_input_widget()

    def create_input_widget(self):
        """根据字段类型创建输入控件"""
        # 使用QLineEdit作为输入控件（统一使用QLineEdit替代ComboBox）
        self.input_widget = QLineEdit()
        self.input_widget.setMinimumWidth(150)  # 设置最小宽度
        self.input_widget.setFixedHeight(24)  # 固定高度
        # 添加16进制验证器，只允许输入16进制数值
        hex_regex = QRegExp("^0x[0-9A-Fa-f]+$|^[0-9A-Fa-f]+$")
        hex_validator = QRegExpValidator(hex_regex, self)
        self.input_widget.setValidator(hex_validator)

        # 添加输入控件到布局的第0行
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.addWidget(self.input_widget)

        # 添加单位标签（如果有）
        if self.unit and self.unit != '-':
            unit_label = QLabel(self.unit)
            input_layout.addWidget(unit_label)

        input_layout.addStretch()  # 添加弹性空间
        self.layout.addLayout(input_layout, 0, 0)

        # 如果有预定义值列表，添加注释标签
        if self.values:
            # 创建注释标签
            comment_label = QLabel()

            # 处理注释文本，将长文本分行显示
            comment_text = "可选值: "
            line_length = 0
            for i, value_info in enumerate(self.values):
                value = value_info.get('value', '')
                desc = value_info.get('description', '')
                item_text = f"{value}={desc}"

                # 检查当前行长度
                if line_length + len(item_text) + 2 > 60:  # 如果加上这个项会超过60个字符
                    comment_text += "\n        "  # 添加换行和缩进
                    line_length = 8  # 重置行长度计数，考虑缩进

                # 添加当前项
                comment_text += item_text

                # 如果不是最后一项，添加分隔符
                if i < len(self.values) - 1:
                    comment_text += ", "
                    line_length += len(item_text) + 2
                else:
                    line_length += len(item_text)

            # 设置注释标签样式
            comment_label.setText(comment_text)
            font = QFont()
            font.setItalic(True)
            comment_label.setFont(font)
            comment_label.setStyleSheet("color: gray; font-size: 9pt;")
            comment_label.setWordWrap(True)  # 启用自动换行

            # 添加到布局的第1行
            self.layout.addWidget(comment_label, 1, 0)

            # 设置默认值为第一个选项
            if self.values:
                default_value = self.values[0].get('value', '')
                self.input_widget.setText(default_value)

        # 数值类型
        if self.field_type in ['Unsigned', 'Signed']:
            # 设置校验器


            # 设置默认值
            default_value = self.min_value if self.min_value is not None else 0
            self.input_widget.setText(str(default_value))

            # 添加注释标签（如果没有预定义值列表）
            if not self.values:
                # 创建注释标签
                comment_label = QLabel()
                comment_text = f"范围: {self.min_value} ~ {self.max_value}"
                if self.precision != 1:
                    comment_text += f", 精度: {self.precision}"

                # 设置注释标签样式
                comment_label.setText(comment_text)
                font = QFont()
                font.setItalic(True)
                comment_label.setFont(font)
                comment_label.setStyleSheet("color: gray; font-size: 9pt;")
                comment_label.setWordWrap(True)  # 启用自动换行

                # 添加到布局的第1行
                self.layout.addWidget(comment_label, 1, 0)

        # 设置值变更信号
        self.input_widget.textChanged.connect(self.value_changed)

    def value_changed(self, value):
        """值变更处理函数"""
        self.valueChanged.emit(self.field_id, value)

    def get_value(self):
        """获取当前值"""
        if hasattr(self, 'input_widget'):
            if isinstance(self.input_widget, QLineEdit):
                return self.input_widget.text()
            elif isinstance(self.input_widget, (QSpinBox, QDoubleSpinBox)):
                return self.input_widget.value()
            elif isinstance(self.input_widget, QComboBox):
                return self.input_widget.currentText()

        return None

    def set_value(self, value):
        """设置当前值"""
        if hasattr(self, 'input_widget'):
            if isinstance(self.input_widget, QLineEdit):
                self.input_widget.setText(str(value))
            elif isinstance(self.input_widget, (QSpinBox, QDoubleSpinBox)):
                self.input_widget.setValue(float(value))
            elif isinstance(self.input_widget, QComboBox):
                index = self.input_widget.findText(str(value))
                if index >= 0:
                    self.input_widget.setCurrentIndex(index)


class ProtocolUIGenerator:
    """协议界面生成器，根据协议数据生成界面"""

    def __init__(self):
        self.field_widgets = {}  # 字段控件字典 {field_id: widget}

    def generate_protocol_widget(self, protocol_data):
        """
        生成协议界面

        Args:
            protocol_data (dict): 协议数据

        Returns:
            QWidget: 协议界面
        """
        if not protocol_data:
            return None

        # 创建主控件
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # 添加协议信息区域
        info_group = QGroupBox("协议信息")
        info_layout = QGridLayout(info_group)
        main_layout.addWidget(info_group)

        # 显示协议基本信息
        protocol_name = protocol_data.get('protocol_name', '未知协议')
        protocol_version = protocol_data.get('protocol_version', '未知版本')
        message_id = protocol_data.get('message_id', '未知ID')
        message_type = protocol_data.get('message_type', '未知类型')
        message_source = protocol_data.get('message_source', '未知来源')

        info_layout.addWidget(QLabel("协议名称:"), 0, 0)
        info_layout.addWidget(QLabel(protocol_name), 0, 1)
        info_layout.addWidget(QLabel("协议版本:"), 0, 2)
        info_layout.addWidget(QLabel(protocol_version), 0, 3)
        info_layout.addWidget(QLabel("报文ID:"), 1, 0)
        info_layout.addWidget(QLabel(message_id), 1, 1)
        info_layout.addWidget(QLabel("报文类型:"), 1, 2)
        info_layout.addWidget(QLabel(message_type), 1, 3)
        info_layout.addWidget(QLabel("报文来源:"), 2, 0)
        info_layout.addWidget(QLabel(message_source), 2, 1)

        # 清空之前的字段控件
        self.field_widgets.clear()

        # 创建字段分组 - 如果字段数量超过10个，则使用滚动区域
        fields = protocol_data.get('fields', [])

        fields_group = QGroupBox("报文字段")
        main_layout.addWidget(fields_group)

        if len(fields) > 10:
            # 使用滚动区域
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)

            fields_container = QWidget()
            fields_layout = QGridLayout(fields_container)
            fields_layout.setAlignment(Qt.AlignTop)

            scroll.setWidget(fields_container)
            fields_group_layout = QVBoxLayout(fields_group)
            fields_group_layout.addWidget(scroll)
        else:
            # 直接使用网格布局
            fields_layout = QGridLayout(fields_group)

        # 添加字段控件
        for i, field in enumerate(fields):
            field_name = field.get('name', f'字段{i}')
            field_id = field.get('id', f'B{i}')
            field_desc = field.get('description', '')

            # 创建标签
            label = QLabel(f"{field_name}:")
            if field_desc:
                label.setToolTip(field_desc)

            # 创建输入控件
            input_widget = FieldInputWidget(field)

            # 添加到布局
            fields_layout.addWidget(label, i, 0)
            fields_layout.addWidget(input_widget, i, 1)

            # 保存控件引用
            self.field_widgets[field_id] = input_widget

        # 添加操作按钮区域
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        # 生成报文按钮
        generate_btn = QPushButton("生成报文")
        generate_btn.setObjectName("generate_btn")
        generate_btn.setProperty("protocol_id", protocol_data.get('protocol_id', ''))
        button_layout.addWidget(generate_btn)

        # 复制到发送区按钮
        copy_to_send_btn = QPushButton("复制到发送区")
        copy_to_send_btn.setObjectName("copy_to_send_btn")
        copy_to_send_btn.setProperty("protocol_id", protocol_data.get('protocol_id', ''))
        button_layout.addWidget(copy_to_send_btn)

        # 保存配置按钮
        save_config_btn = QPushButton("保存配置")
        save_config_btn.setObjectName("save_config_btn")
        save_config_btn.setProperty("protocol_id", protocol_data.get('protocol_id', ''))
        button_layout.addWidget(save_config_btn)

        # 加载配置按钮
        load_config_btn = QPushButton("加载配置")
        load_config_btn.setObjectName("load_config_btn")
        load_config_btn.setProperty("protocol_id", protocol_data.get('protocol_id', ''))
        button_layout.addWidget(load_config_btn)

        return main_widget

    def get_field_values(self):
        """
        获取所有字段的当前值

        Returns:
            dict: 字段值字典 {field_id: value}
        """
        values = {}
        for field_id, widget in self.field_widgets.items():
            values[field_id] = widget.get_value()

        return values

    def set_field_values(self, values):
        """
        设置字段值

        Args:
            values (dict): 字段值字典 {field_id: value}
        """
        for field_id, value in values.items():
            if field_id in self.field_widgets:
                self.field_widgets[field_id].set_value(value)