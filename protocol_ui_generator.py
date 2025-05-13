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
    """字段输入控件，统一使用QLineEdit"""

    valueChanged = pyqtSignal(str, object)  # 值变更信号 (field_id, value)

    def __init__(self, field_info, parent=None):
        super().__init__(parent)
        self.field_info = field_info
        self.field_id = field_info.get('id', '')
        self.original_id = field_info.get('original_id', '')  # 保存原始ID
        self.field_name = field_info.get('name', '')
        self.field_type = field_info.get('type', 'Unsigned')
        self.min_value = field_info.get('min_value', 0)
        self.max_value = field_info.get('max_value', 0)
        self.precision = field_info.get('precision', 1)
        self.offset = field_info.get('offset', 0)
        self.unit = field_info.get('unit', '')
        self.values = field_info.get('values', [])
        self.current_value = None  # 添加一个成员变量来存储当前值

        # 输出调试信息
        print(f"创建字段控件: ID={self.field_id}, 原始ID={self.original_id}, 名称={self.field_name}")

        # 使用网格布局代替垂直布局，便于控制对齐
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)  # 减少间距
        self.layout.setVerticalSpacing(2)  # 减少垂直间距

        # 创建输入控件
        self.create_input_widget()

    def create_input_widget(self):
        """创建输入控件 - 仅使用QLineEdit"""
        # 使用QLineEdit作为输入控件
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

        # 数值类型
        if self.field_type in ['Unsigned', 'Signed']:
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
        self.input_widget.editingFinished.connect(self.editing_finished)

    def value_changed(self, value):
        """值变更处理函数"""
        # 保存当前值
        self.current_value = value
        # 发送信号
        self.valueChanged.emit(self.field_id, value)

        # 针对特定字段添加额外调试信息
        if "_B1[0:1]" in self.field_id or "整车ACC状态" in self.field_name:
            print(f"字段 {self.field_id} 值已变更为: {value}")

    def editing_finished(self):
        """编辑完成处理函数"""
        value = self.input_widget.text()
        # 确保值被保存
        self.current_value = value

        # 针对特定字段添加额外调试信息
        if "_B1[0:1]" in self.field_id or "整车ACC状态" in self.field_name:
            print(f"字段 {self.field_id} 编辑完成，最终值为: {value}")

    def get_value(self):
        """获取当前值"""
        if hasattr(self, 'input_widget'):
            text_value = self.input_widget.text()
            # 如果文本框有值，返回文本框的值
            if text_value is not None:  # 注意这里的变化：我们接受空字符串
                return text_value
            # 如果文本框为None，但current_value有值，返回current_value
            elif self.current_value is not None:
                return self.current_value
        # 如果都没有值，返回None
        return None

    def set_value(self, value):
        """设置当前值"""
        if hasattr(self, 'input_widget'):
            self.input_widget.setText(str(value))
            self.current_value = str(value)

            # 针对特定字段添加额外调试信息
            if "_B1[0:1]" in self.field_id or "整车ACC状态" in self.field_name:
                print(f"设置字段 {self.field_id} 值为: {value}")


class ProtocolUIGenerator:
    """协议界面生成器，根据协议数据生成界面"""

    def __init__(self):
        self.field_widgets = {}  # 字段控件字典 {field_id: widget}
        self.protocol_widgets = {}  # 按协议组织的字段控件 {protocol_id: {field_id: widget}}

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

        # 获取协议ID
        protocol_id = protocol_data.get('protocol_id', '')
        if protocol_id not in self.protocol_widgets:
            self.protocol_widgets[protocol_id] = {}

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
            original_field_id = field.get('id', f'B{i}')
            field_desc = field.get('description', '')

            # 创建新的字段ID: 协议ID + 字段ID
            new_field_id = f"{protocol_id}_{original_field_id}"

            # 输出字段ID映射，用于调试
            print(f"字段ID映射: {original_field_id} -> {new_field_id}")

            # 更新字段信息中的ID（复制一份以避免修改原始数据）
            field_info = field.copy()
            field_info['original_id'] = original_field_id  # 保存原始ID
            field_info['id'] = new_field_id  # 设置新ID

            # 创建标签
            label = QLabel(f"{field_name}:")
            if field_desc:
                label.setToolTip(field_desc)

            # 创建输入控件
            input_widget = FieldInputWidget(field_info)

            # 添加到布局
            fields_layout.addWidget(label, i, 0)
            fields_layout.addWidget(input_widget, i, 1)

            # 保存控件引用到两个字典
            self.field_widgets[new_field_id] = input_widget
            self.protocol_widgets[protocol_id][new_field_id] = input_widget

        # 添加操作按钮区域
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        # 生成报文按钮
        generate_btn = QPushButton("生成报文")
        generate_btn.setObjectName("generate_btn")
        generate_btn.setProperty("protocol_id", protocol_id)
        button_layout.addWidget(generate_btn)

        # 复制到发送区按钮
        copy_to_send_btn = QPushButton("复制到发送区")
        copy_to_send_btn.setObjectName("copy_to_send_btn")
        copy_to_send_btn.setProperty("protocol_id", protocol_id)
        button_layout.addWidget(copy_to_send_btn)

        # 保存配置按钮
        save_config_btn = QPushButton("保存配置")
        save_config_btn.setObjectName("save_config_btn")
        save_config_btn.setProperty("protocol_id", protocol_id)
        button_layout.addWidget(save_config_btn)

        # 加载配置按钮
        load_config_btn = QPushButton("加载配置")
        load_config_btn.setObjectName("load_config_btn")
        load_config_btn.setProperty("protocol_id", protocol_id)
        button_layout.addWidget(load_config_btn)

        return main_widget

    def get_field_values(self, protocol_id=None):
        """
        获取字段的当前值，如果指定了protocol_id则只获取该协议的字段值

        Args:
            protocol_id (str, optional): 协议ID，如果提供则只获取该协议的字段值

        Returns:
            dict: 字段值字典 {field_id: value}，根据protocol_id可能只返回部分字段
        """
        values = {}
        print(f"\n============== 控件值调试信息 {'(协议:' + protocol_id + ')' if protocol_id else ''} ==============")

        # 首先打印所有字段ID，看看哪些字段是可用的
        if protocol_id:
            # 使用协议特定的字段字典
            if protocol_id in self.protocol_widgets:
                widgets_dict = self.protocol_widgets[protocol_id]
                print(f"使用协议 {protocol_id} 的专用控件字典，包含 {len(widgets_dict)} 个控件")
            else:
                # 如果没有该协议的专用字典，从全局字典中筛选
                widgets_dict = {k: v for k, v in self.field_widgets.items() if k.startswith(f"{protocol_id}_")}
                print(f"从全局字典中筛选协议 {protocol_id} 的控件，找到 {len(widgets_dict)} 个")
        else:
            # 使用全局字段字典
            widgets_dict = self.field_widgets
            print(f"使用全局控件字典，包含 {len(widgets_dict)} 个控件")

        # 打印所有可用控件的ID
        print("可用控件ID列表:")
        for field_id in widgets_dict.keys():
            print(f"  {field_id}")

        # 处理每个控件并获取值
        try:
            for field_id, widget in widgets_dict.items():
                try:
                    value = widget.get_value()

                    # 特别检查特定字段
                    if field_id.endswith("_B1[0:1]") or "整车ACC状态" in getattr(widget, 'field_name', ''):
                        print(f"检查字段 {field_id}: 值 = {value}, 类型 = {type(value)}")
                        # 尝试从文本框直接获取
                        if hasattr(widget, 'input_widget'):
                            text_value = widget.input_widget.text()
                            if text_value:
                                value = text_value
                                print(f"  从文本框直接获取到值: {value}")
                            # 尝试从current_value获取
                            elif hasattr(widget, 'current_value') and widget.current_value:
                                value = widget.current_value
                                print(f"  从current_value获取到值: {value}")

                    # 直接输出值的内容和类型，以便调试
                    print(f"控件 {field_id}: 值 = {value}, 类型 = {type(value)}")

                    # 存储所有非None值
                    if value is not None:
                        values[field_id] = value
                        print(f"  - 已添加到字段值字典")
                    else:
                        print(f"  - 值为None，未添加到字段值字典")
                except Exception as e:
                    print(f"获取控件 {field_id} 的值时出错: {str(e)}")
                    continue
        except Exception as e:
            print(f"遍历控件时出错: {str(e)}")

        # 特别处理D3h_B1[0:1]字段（整车ACC状态）
        if protocol_id == "D3h":
            special_field_id = "D3h_B1[0:1]"
            if special_field_id not in values and special_field_id in widgets_dict:
                widget = widgets_dict[special_field_id]
                if hasattr(widget, 'current_value') and widget.current_value:
                    values[special_field_id] = widget.current_value
                    print(f"特别处理: 从current_value添加字段 {special_field_id} 的值 = {widget.current_value}")
                elif hasattr(widget, 'input_widget'):
                    text_value = widget.input_widget.text()
                    if text_value:
                        values[special_field_id] = text_value
                        print(f"特别处理: 从文本框添加字段 {special_field_id} 的值 = {text_value}")

        count = sum(1 for field_id in values if protocol_id and field_id.startswith(f"{protocol_id}_"))
        print(
            f"共获取到 {len(values)} 个字段值，其中 {count} 个属于协议 {protocol_id}" if protocol_id else f"共获取到 {len(values)} 个字段值")
        print("==========================================\n")
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