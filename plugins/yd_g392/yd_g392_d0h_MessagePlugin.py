# -*- coding: utf-8 -*-
"""
YD-G392-D0h报文生成与解析插件
基于RS485线总线ICM节点通信协议(2024版)V2.01
实现IOT节点D0h报文的生成与解析
"""
import os
import sys
import re

# 获取当前脚本文件的绝对路径
current_file_path = os.path.abspath(__file__)
# 获取当前脚本所在的目录
current_dir = os.path.dirname(current_file_path)

# 将当前目录添加到Python的搜索路径
sys.path.append(current_dir)
from rs485_message_base_plugin import RS485MessagePlugin, RS485MessageBaseWidget
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox,
                             QGroupBox, QCheckBox, QSpinBox, QTextEdit, QTabWidget,
                             QRadioButton, QButtonGroup, QDateTimeEdit, QFrame,
                             QListWidget, QListWidgetItem, QDialog, QScrollArea,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime, QObject
from PyQt5.QtGui import QColor, QBrush, QFont


class MessageParser(QObject):
    """报文解析类"""

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse_d0h_message(message_bytes):
        """
        解析D0h报文

        Args:
            message_bytes (bytes): 完整的报文字节

        Returns:
            dict: 解析后的报文内容，如果解析失败返回None
        """
        try:
            # 处理报文格式
            if message_bytes.startswith(b'\x59\x44'):  # 检查报文头
                # 如果有完整的报文头尾，截取ID到数据结束部分（不含CRC和报文尾）
                if message_bytes.endswith(b'\x4B\x4A'):
                    # 截取ID和数据部分（不含报文头、CRC和报文尾）
                    message_data = message_bytes[2:-4]
                else:
                    # 只有报文头，无报文尾，截取ID后所有内容
                    message_data = message_bytes[2:]
            else:
                # 无报文头，直接使用内容
                message_data = message_bytes

            # 检查是否是D0h报文
            if len(message_data) >= 2 and message_data[0] == 0xD0:
                # 报文ID为D0h
                data_length = message_data[1]  # 数据长度

                # 检查长度是否匹配
                if len(message_data) < data_length + 2:  # ID + 长度 + 数据
                    return None

                # 提取有效数据部分
                data = message_data[2:2 + data_length]

                # 解析数据内容
                result = {
                    "message_id": "D0h",
                    "data_length": data_length,
                    "raw_data": " ".join([f"{b:02X}" for b in data])
                }

                # 如果数据长度不足，返回原始数据
                if len(data) < 27:
                    return result

                # 解析IOT实时时间（B0-B5）
                year = 2000 + data[0] if data[0] < 100 else data[0]
                result["datetime"] = f"{year}-{data[1]:02d}-{data[2]:02d} {data[3]:02d}:{data[4]:02d}:{data[5]:02d}"

                # B6解析
                b6 = data[6] if len(data) > 6 else 0
                # 解析周
                week_day = b6 & 0x07
                week_days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
                result["week_day"] = week_days[week_day] if week_day < 7 else "无效"

                # 解析设备类型
                device_type = (b6 >> 3) & 0x01
                result["device_type"] = "ALM" if device_type == 1 else "IOT"

                # GPS状态
                gps_status = (b6 >> 5) & 0x01
                result["gps_status"] = "点亮" if gps_status == 1 else "熄灭"

                # GSM状态
                gsm_status = (b6 >> 6) & 0x01
                result["gsm_status"] = "点亮" if gsm_status == 1 else "熄灭"

                # B9解析远程控制指令
                if len(data) > 9:
                    control_cmd = data[9]
                    control_cmd_map = {
                        0x0: "设防", 0x1: "解防", 0x2: "开机", 0x3: "关机", 0x4: "寻车",
                        0x5: "解电磁阀", 0x6: "总计里程清零指令", 0x7: "请求ALM进入从机模式指令",
                        0x8: "请求主节点轮询静态报文指令", 0xE: "无操作", 0xF: "无效值"
                    }
                    result["control_command"] = control_cmd_map.get(control_cmd, f"未知指令({control_cmd:02X})")

                # B19解析充电相关状态
                if len(data) > 19:
                    charge_status = data[19] & 0x03
                    charge_status_map = {
                        0: "未连接", 1: "已连接未充电", 2: "充电中", 3: "充电完成"
                    }
                    result["charge_status"] = charge_status_map.get(charge_status, f"未知状态({charge_status:02X})")

                # B20解析手机/座垫感应开关状态
                if len(data) > 20:
                    b20 = data[20]
                    phone_detect = (b20 & 0x01)
                    result["phone_detect"] = "检测到" if phone_detect == 1 else "未检测"

                    seat_detect = ((b20 >> 2) & 0x01)
                    result["seat_detect"] = "检测到" if seat_detect == 1 else "未检测"

                # B21解析主节点元器件类型
                if len(data) > 21:
                    b21 = data[21]
                    rs485_master_type = (b21 & 0x01)
                    result["rs485_master_type"] = "ALM" if rs485_master_type == 1 else "IOT"

                    kline_master_type = ((b21 >> 2) & 0x01)
                    result["kline_master_type"] = "ALM" if kline_master_type == 1 else "IOT"

                # 天气相关信息（B22-B26）
                if len(data) > 26:
                    # 预警天气类型
                    weather_warning_type = data[22]
                    result["weather_warning_type"] = weather_warning_type

                    # 当前天气类型
                    current_weather = data[23]
                    result["current_weather"] = current_weather

                    # 当前天气温度
                    current_temp = data[24]
                    # 转换为有符号数（如果最高位为1，表示负数）
                    if current_temp & 0x80:
                        current_temp = current_temp - 256
                    result["current_temp"] = f"{current_temp} ℃"

                    # 恶劣天气类型
                    bad_weather_type = data[25]
                    result["bad_weather_type"] = bad_weather_type

                    # 天气预警等级和恶劣天气发生时间
                    b26 = data[26]
                    warning_level = b26 & 0x07
                    warning_level_map = {
                        0: "白色", 1: "蓝色", 2: "黄色", 3: "橙色", 4: "红色"
                    }
                    result["warning_level"] = warning_level_map.get(warning_level, f"未知等级({warning_level:02X})")

                    bad_weather_time = (b26 >> 3) & 0x1F
                    if bad_weather_time == 0:
                        result["bad_weather_time"] = "Reserved"
                    elif bad_weather_time <= 6:
                        result["bad_weather_time"] = f"{bad_weather_time}小时"
                    else:
                        result["bad_weather_time"] = f"未知时间({bad_weather_time:02X})"

                return result

            return None
        except Exception as e:
            print(f"解析D0h报文错误: {str(e)}")
            return None


class MessageDetailDialog(QDialog):
    """报文详情对话框"""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("报文详情")
        self.resize(600, 400)
        self.data = data
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 创建报文详情表格
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["参数", "值"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # 填充表格数据
        self.fill_table()

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def fill_table(self):
        """填充表格数据"""
        if not self.data:
            return

        # 字段显示顺序和显示名称
        field_order = [
            ("message_id", "报文ID"),
            ("data_length", "数据长度"),
            ("datetime", "IOT实时时间"),
            ("week_day", "星期"),
            ("device_type", "设备类型"),
            ("gps_status", "GPS状态"),
            ("gsm_status", "GSM状态"),
            ("control_command", "远程控制指令"),
            ("charge_status", "充电器接入状态"),
            ("phone_detect", "手机检测状态"),
            ("seat_detect", "座垫感应状态"),
            ("rs485_master_type", "RS485主节点类型"),
            ("kline_master_type", "K线主节点类型"),
            ("weather_warning_type", "预警天气类型"),
            ("current_weather", "当前天气类型"),
            ("current_temp", "当前天气温度"),
            ("bad_weather_type", "恶劣天气类型"),
            ("warning_level", "天气预警等级"),
            ("bad_weather_time", "恶劣天气发生时间"),
            ("raw_data", "原始数据")
        ]

        # 填充表格
        for i, (key, name) in enumerate(field_order):
            if key in self.data:
                self.table.insertRow(i)
                self.table.setItem(i, 0, QTableWidgetItem(name))
                self.table.setItem(i, 1, QTableWidgetItem(str(self.data[key])))


class MessagePlugin(RS485MessagePlugin):
    """
    YD-G392-D0h报文生成与解析插件类
    实现IOT节点D0h报文的生成与解析
    """

    def __init__(self):
        super().__init__()
        self.name = "YD-G392-D0h报文生成与解析插件"
        self.description = "用于生成和解析IOT节点D0h周期响应报文"
        self.message_parser = MessageParser()

    def create_ui(self):
        """创建插件UI"""
        self.widget = yd_g392_d0h_MessageWidget(self)
        return self.widget

    def generate_message(self, params=None):
        """
        生成IOT节点D0h报文

        Args:
            params (dict): 报文参数

        Returns:
            bytes: 生成的报文
        """
        if not params:
            return None

        try:
            # 构建报文数据
            message_data = bytearray()

            # IOT实时时间（B0-B5，0-5字节）
            dt = params.get('datetime', QDateTime.currentDateTime())
            message_data.append(dt.date().year() % 100)  # 年（取后两位）
            message_data.append(dt.date().month())  # 月
            message_data.append(dt.date().day())  # 日
            message_data.append(dt.time().hour())  # 时
            message_data.append(dt.time().minute())  # 分
            message_data.append(dt.time().second())  # 秒

            # IOT实时时间-周和主节点元器件类型等（B6，6字节）
            b6 = 0
            # 周（0-6对应周日-周六，7为无效值）
            week_day = dt.date().dayOfWeek() % 7  # Qt的dayOfWeek()返回1-7，转换为0-6
            b6 |= (week_day & 0x07)

            # 元器件类型和状态指示
            if params.get('device_type') == 'IOT':
                b6 |= (0 << 3)
            elif params.get('device_type') == 'ALM':
                b6 |= (1 << 3)

            if params.get('gps_status') == '点亮':
                b6 |= (1 << 5)

            if params.get('gsm_status') == '点亮':
                b6 |= (1 << 6)

            message_data.append(b6)

            # 预留字节（B7-B8，7-8字节）
            message_data.extend([0xFF, 0xFF])

            # 远程控制指令（B9，9字节）
            b9 = 0
            control_cmd = params.get('control_command', '无操作')
            if control_cmd == '设防':
                b9 = 0x0
            elif control_cmd == '解防':
                b9 = 0x1
            elif control_cmd == '开机':
                b9 = 0x2
            elif control_cmd == '关机':
                b9 = 0x3
            elif control_cmd == '寻车':
                b9 = 0x4
            elif control_cmd == '解电磁阀':
                b9 = 0x5
            elif control_cmd == '总计里程清零指令':
                b9 = 0x6
            elif control_cmd == '请求ALM进入从机模式指令':
                b9 = 0x7
            elif control_cmd == '请求主节点轮询静态报文指令':
                b9 = 0x8
            elif control_cmd == '无操作':
                b9 = 0xE
            else:
                b9 = 0xF  # 无效值

            message_data.append(b9)

            # 预留字节（B10-B18，10-18字节）
            message_data.extend([0xFF] * 9)

            # 预估剩余里程当前值（B17-B18，已在预留字节中）

            # 充电相关状态（B19，19字节）
            b19 = 0

            # 按照协议文档定义充电器接入状态
            charge_status = params.get('charge_status', '未连接')
            if charge_status == '未连接':
                b19 |= 0
            elif charge_status == '已连接未充电':
                b19 |= 1
            elif charge_status == '充电中':
                b19 |= 2
            elif charge_status == '充电完成':
                b19 |= 3

            message_data.append(b19)

            # 手机/座垫感应开关状态（B20，20字节）
            b20 = 0
            if params.get('phone_detect') == '检测到':
                b20 |= 1

            if params.get('seat_detect') == '检测到':
                b20 |= (1 << 2)

            message_data.append(b20)

            # 主节点元器件类型（B21，21字节）
            b21 = 0
            # RS485主节点类型
            rs485_type = params.get('rs485_master_type', 'IOT')
            if rs485_type == 'IOT':
                b21 |= 0
            elif rs485_type == 'ALM':
                b21 |= 1

            # K线主节点类型
            kline_type = params.get('kline_master_type', 'IOT')
            if kline_type == 'IOT':
                b21 |= (0 << 2)
            elif kline_type == 'ALM':
                b21 |= (1 << 2)

            message_data.append(b21)

            # 天气相关信息（B22-B26，22-26字节）
            # 预警天气类型
            weather_warning_type = int(params.get('weather_warning_type', 0))
            message_data.append(weather_warning_type & 0xFF)

            # 当前天气类型
            current_weather = int(params.get('current_weather', 0))
            message_data.append(current_weather & 0xFF)

            # 当前天气温度
            current_temp = int(params.get('current_temp', 20))
            message_data.append(current_temp & 0xFF)

            # 恶劣天气类型
            bad_weather_type = int(params.get('bad_weather_type', 0))
            message_data.append(bad_weather_type & 0xFF)

            # 天气预警等级和恶劣天气发生时间（B26，26字节）
            b26 = 0
            # 天气预警等级
            warning_level = int(params.get('warning_level', 0))
            b26 |= (warning_level & 0x07)

            # 恶劣天气发生时间
            bad_weather_time = int(params.get('bad_weather_time', 0))
            b26 |= ((bad_weather_time & 0x1F) << 3)

            message_data.append(b26)

            # 构建完整报文
            full_message = bytearray()

            # 添加报文头
            if params.get('add_header', True):
                full_message.extend(b'\x59\x44')  # 报文头固定值

            # 添加报文ID
            full_message.append(0xD0)  # D0h报文ID

            # 添加数据长度
            full_message.append(len(message_data))

            # 添加数据内容
            full_message.extend(message_data)

            # 添加CRC校验
            if params.get('add_crc', True):
                # 计算从ID开始到数据结束的CRC
                crc_data = full_message[2:] if params.get('add_header', True) else full_message
                crc = self.calculate_crc16(crc_data)
                full_message.extend(crc.to_bytes(2, byteorder='little'))

            # 添加报文尾
            if params.get('add_footer', True):
                full_message.extend(b'\x4B\x4A')  # 报文尾固定值

            return bytes(full_message)

        except Exception as e:
            if self.app:
                self.app.add_log_message(f"生成D0h报文错误: {str(e)}", "error")
            return None

    def parse_message(self, message_bytes):
        """
        解析收到的报文

        Args:
            message_bytes (bytes): 报文字节

        Returns:
            dict: 解析结果
        """
        # 首先检查是否为D0h报文
        return self.message_parser.parse_d0h_message(message_bytes)

    def on_data_received(self, data):
        """
        接收到数据的处理函数

        Args:
            data (bytes): 接收到的数据
        """
        # 尝试解析报文
        parsed_data = self.parse_message(data)
        if parsed_data and self.widget:
            self.widget.add_parsed_message(parsed_data)


class yd_g392_d0h_MessageWidget(RS485MessageBaseWidget):
    """YD-G392-D0h报文生成与解析插件UI"""

    def __init__(self, plugin):
        super().__init__(plugin)
        self.extend_ui()

        # 接收报文列表
        self.received_messages = []

    def extend_ui(self):
        """扩展基础UI，添加IOT节点D0h报文特有的UI元素"""
        # 在基础UI的基础上添加IOT特有的参数

        # 更新报文ID默认值
        self.message_id_edit.setText("D0h")
        self.message_id_edit.setReadOnly(True)

        # 更新节点类型
        self.node_combo.setCurrentText("IOT")
        self.node_combo.setEnabled(False)

        # 创建选项卡
        self.tab_widget = QTabWidget()
        self.main_layout.insertWidget(2, self.tab_widget)

        # 创建基本参数选项卡
        self.basic_tab = QWidget()
        self.tab_widget.addTab(self.basic_tab, "基本参数")
        self.basic_layout = QGridLayout(self.basic_tab)

        # 创建天气参数选项卡
        self.weather_tab = QWidget()
        self.tab_widget.addTab(self.weather_tab, "天气参数")
        self.weather_layout = QGridLayout(self.weather_tab)

        # 创建接收报文选项卡
        self.receive_tab = QWidget()
        self.tab_widget.addTab(self.receive_tab, "接收报文")
        self.receive_layout = QVBoxLayout(self.receive_tab)

        # 接收报文列表
        self.receive_list = QListWidget()
        self.receive_list.setAlternatingRowColors(True)
        self.receive_list.itemDoubleClicked.connect(self.show_message_detail)
        self.receive_layout.addWidget(self.receive_list)

        # 接收区按钮布局
        receive_btn_layout = QHBoxLayout()
        self.receive_layout.addLayout(receive_btn_layout)

        # 清空接收区按钮
        clear_receive_btn = QPushButton("清空接收区")
        clear_receive_btn.clicked.connect(self.clear_receive_list)
        receive_btn_layout.addWidget(clear_receive_btn)

        # 解析选中报文按钮
        parse_selected_btn = QPushButton("解析选中报文")
        parse_selected_btn.clicked.connect(self.parse_selected_message)
        receive_btn_layout.addWidget(parse_selected_btn)

        # 添加基本参数
        self.setup_basic_params()

        # 添加天气参数
        self.setup_weather_params()

        # 修改复制到发送区的处理逻辑
        if hasattr(self, 'copy_to_send_btn'):
            self.copy_to_send_btn.clicked.connect(self.copy_to_quick_send)

    def show_message_detail(self, item):
        """显示报文详情"""
        index = self.receive_list.row(item)
        if 0 <= index < len(self.received_messages):
            dialog = MessageDetailDialog(self.received_messages[index], self)
            dialog.exec_()

    def clear_receive_list(self):
        """清空接收列表"""
        self.receive_list.clear()
        self.received_messages.clear()

    def parse_selected_message(self):
        """解析选中的报文"""
        selected_items = self.receive_list.selectedItems()
        if not selected_items:
            return

        index = self.receive_list.row(selected_items[0])
        if 0 <= index < len(self.received_messages):
            dialog = MessageDetailDialog(self.received_messages[index], self)
            dialog.exec_()

    def add_parsed_message(self, parsed_data):
        """添加解析后的报文到列表"""
        if not parsed_data:
            return

        # 添加到内部列表
        self.received_messages.append(parsed_data)

        # 创建列表项
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        # 构建显示内容
        if "datetime" in parsed_data:
            item_text = f"{timestamp} - D0h报文 - {parsed_data['datetime']}"
        else:
            item_text = f"{timestamp} - D0h报文"

        # 添加到列表控件
        item = QListWidgetItem(item_text)
        self.receive_list.addItem(item)
        self.receive_list.scrollToBottom()

    def copy_to_quick_send(self):
        """将生成的报文复制到快速发送区"""
        try:
            # 获取当前参数
            params = self.get_parameters()

            # 生成报文
            message = self.plugin.generate_message(params)

            if message:
                # 转换为十六进制字符串
                hex_str = ''.join([f"{b:02X}" for b in message])

                # 复制到快速发送区
                main_window = self.window()
                if hasattr(main_window, 'quick_send_text'):
                    main_window.quick_send_text.setText(hex_str)

                    # 添加日志
                    if hasattr(main_window, 'add_log_message'):
                        main_window.add_log_message("报文已复制到快速发送区", "system")
                else:
                    # 无法找到快速发送区，弹出消息
                    QMessageBox.information(self, "提示", f"报文已生成，但未找到快速发送区。\n\n报文内容：{hex_str}")
        except Exception as e:
            # 错误处理
            error_message = f"复制报文到发送区失败: {str(e)}"
            main_window = self.window()
            if hasattr(main_window, 'add_log_message'):
                main_window.add_log_message(error_message, "error")
            else:
                QMessageBox.warning(self, "错误", error_message)

    def setup_basic_params(self):
        """设置基本参数UI"""
        # 日期时间
        self.basic_layout.addWidget(QLabel("IOT实时时间:"), 0, 0)
        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.basic_layout.addWidget(self.datetime_edit, 0, 1)

        # 设备类型
        self.basic_layout.addWidget(QLabel("设备类型:"), 1, 0)
        self.device_type_combo = QComboBox()
        self.device_type_combo.addItems(["IOT", "ALM"])
        self.basic_layout.addWidget(self.device_type_combo, 1, 1)

        # GPS状态
        self.basic_layout.addWidget(QLabel("GPS状态:"), 2, 0)
        self.gps_combo = QComboBox()
        self.gps_combo.addItems(["熄灭", "点亮"])
        self.basic_layout.addWidget(self.gps_combo, 2, 1)

        # GSM状态
        self.basic_layout.addWidget(QLabel("GSM状态:"), 3, 0)
        self.gsm_combo = QComboBox()
        self.gsm_combo.addItems(["熄灭", "点亮"])
        self.basic_layout.addWidget(self.gsm_combo, 3, 1)

        # 远程控制指令
        self.basic_layout.addWidget(QLabel("远程控制指令:"), 4, 0)
        self.control_combo = QComboBox()
        self.control_combo.addItems([
            "无操作","设防", "解防", "开机", "关机", "寻车",
            "解电磁阀", "总计里程清零指令", "请求ALM进入从机模式指令",
            "请求主节点轮询静态报文指令"
        ])
        self.basic_layout.addWidget(self.control_combo, 4, 1)

        # 充电器接入状态
        self.basic_layout.addWidget(QLabel("充电器接入状态:"), 5, 0)
        self.charge_combo = QComboBox()
        self.charge_combo.addItems(["未连接", "已连接未充电", "充电中", "充电完成"])
        self.basic_layout.addWidget(self.charge_combo, 5, 1)

        # 手机检测状态
        self.basic_layout.addWidget(QLabel("手机检测状态:"), 6, 0)
        self.phone_combo = QComboBox()
        self.phone_combo.addItems(["未检测", "检测到"])
        self.basic_layout.addWidget(self.phone_combo, 6, 1)

        # 座垫感应状态
        self.basic_layout.addWidget(QLabel("座垫感应状态:"), 7, 0)
        self.seat_combo = QComboBox()
        self.seat_combo.addItems(["未检测", "检测到"])
        self.basic_layout.addWidget(self.seat_combo, 7, 1)

        # RS485主节点类型
        self.basic_layout.addWidget(QLabel("RS485主节点类型:"), 8, 0)
        self.rs485_master_combo = QComboBox()
        self.rs485_master_combo.addItems(["IOT", "ALM"])
        self.basic_layout.addWidget(self.rs485_master_combo, 8, 1)

        # K线主节点类型
        self.basic_layout.addWidget(QLabel("K线主节点类型:"), 9, 0)
        self.kline_master_combo = QComboBox()
        self.kline_master_combo.addItems(["IOT", "ALM"])
        self.basic_layout.addWidget(self.kline_master_combo, 9, 1)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.basic_layout.addWidget(line, 10, 0, 1, 2)

    def setup_weather_params(self):
        """设置天气参数UI"""
        # 预警天气类型
        self.weather_layout.addWidget(QLabel("预警天气类型:"), 0, 0)
        self.weather_warning_combo = QComboBox()
        self.weather_warning_combo.addItems([
            "0-晴", "1-晴", "2-多云", "3-晴间多云", "4-晴间多云", "5-大部多云",
            "6-大部多云", "7-阴", "8-阵雨", "9-雷阵雨", "10-雷阵雨伴有冰雹",
            "11-小雨", "12-中雨", "13-大雨", "14-暴雨", "15-大暴雨",
            "16-特大暴雨", "17-冻雨", "18-雨夹雪", "19-阵雪", "20-小雪"
        ])
        self.weather_layout.addWidget(self.weather_warning_combo, 0, 1)

        # 当前天气类型
        self.weather_layout.addWidget(QLabel("当前天气类型:"), 1, 0)
        self.current_weather_combo = QComboBox()
        self.current_weather_combo.addItems([
            "0-晴", "1-晴", "2-多云", "3-晴间多云", "4-晴间多云", "5-大部多云",
            "6-大部多云", "7-阴", "8-阵雨", "9-雷阵雨", "10-雷阵雨伴有冰雹",
            "11-小雨", "12-中雨", "13-大雨", "14-暴雨", "15-大暴雨",
            "16-特大暴雨", "17-冻雨", "18-雨夹雪", "19-阵雪", "20-小雪"
        ])
        self.weather_layout.addWidget(self.current_weather_combo, 1, 1)

        # 当前天气温度
        self.weather_layout.addWidget(QLabel("当前天气温度:"), 2, 0)
        self.current_temp_spin = QSpinBox()
        self.current_temp_spin.setRange(-100, 100)
        self.current_temp_spin.setValue(20)
        self.current_temp_spin.setSuffix(" ℃")
        self.weather_layout.addWidget(self.current_temp_spin, 2, 1)

        # 恶劣天气类型
        self.weather_layout.addWidget(QLabel("恶劣天气类型:"), 3, 0)
        self.bad_weather_combo = QComboBox()
        self.bad_weather_combo.addItems([
            "1-阵雨", "2-雷阵雨", "3-雷阵雨伴有冰雹", "4-小雨", "5-中雨",
            "6-大雨", "7-暴雨", "8-大暴雨", "9-特大暴雨", "10-冻雨",
            "11-雨夹雪", "12-阵雪", "13-小雪", "14-中雪", "15-大雪",
            "16-暴雪", "17-浮尘", "18-扬沙", "19-沙尘暴", "20-强沙尘暴",
            "21-雾", "22-霾", "23-风", "24-大风", "25-飓风",
            "26-热带风暴", "27-龙卷风"
        ])
        self.weather_layout.addWidget(self.bad_weather_combo, 3, 1)

        # 天气预警等级
        self.weather_layout.addWidget(QLabel("天气预警等级:"), 4, 0)
        self.warning_level_combo = QComboBox()
        self.warning_level_combo.addItems([
            "0-白色", "1-蓝色", "2-黄色", "3-橙色", "4-红色"
        ])
        self.weather_layout.addWidget(self.warning_level_combo, 4, 1)

        # 恶劣天气发生时间
        self.weather_layout.addWidget(QLabel("恶劣天气发生时间:"), 5, 0)
        self.bad_weather_time_combo = QComboBox()
        self.bad_weather_time_combo.addItems([
            "0-Reserved", "1-1小时", "2-2小时", "3-3小时",
            "4-4小时", "5-5小时", "6-6小时"
        ])
        self.weather_layout.addWidget(self.bad_weather_time_combo, 5, 1)

    def get_parameters(self):
        """
        获取UI上的参数

        Returns:
            dict: 参数字典
        """
        # 获取基础参数
        params = super().get_parameters()

        # 添加D0h报文特有参数
        params.update({
            'datetime': self.datetime_edit.dateTime(),
            'device_type': self.device_type_combo.currentText(),
            'gps_status': self.gps_combo.currentText(),
            'gsm_status': self.gsm_combo.currentText(),
            'control_command': self.control_combo.currentText(),
            'charge_status': self.charge_combo.currentText(),
            'phone_detect': self.phone_combo.currentText(),
            'seat_detect': self.seat_combo.currentText(),
            'rs485_master_type': self.rs485_master_combo.currentText(),
            'kline_master_type': self.kline_master_combo.currentText(),

            # 获取天气参数
            'weather_warning_type': int(self.weather_warning_combo.currentText().split('-')[0]),
            'current_weather': int(self.current_weather_combo.currentText().split('-')[0]),
            'current_temp': self.current_temp_spin.value(),
            'bad_weather_type': int(self.bad_weather_combo.currentText().split('-')[0]),
            'warning_level': int(self.warning_level_combo.currentText().split('-')[0]),
            'bad_weather_time': int(self.bad_weather_time_combo.currentText().split('-')[0]),
        })

        return params