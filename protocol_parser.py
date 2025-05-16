# -*- coding: utf-8 -*-
"""
@Author     : 王舒
@Company    : 黑龙江天有为科技有限公司
@Date       : 2025-05-10
@Python     : 3.10
@Description: 报文解析模块，负责解析各种协议报文
"""

import struct
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal
from log_manager import LogManager, log_debug, log_info, log_error, log_exception

class ProtocolParser(QObject):
    """协议解析器，解析接收到的报文数据"""

    message_parsed = pyqtSignal(str, dict)  # 报文解析完成信号 (protocol_id, parsed_data)

    def __init__(self):
        super().__init__()
        self.protocols = {}  # 协议信息字典 {protocol_id: protocol_data}

    def set_protocols(self, protocols):
        """
        设置协议信息

        Args:
            protocols (dict): 协议信息字典 {protocol_id: protocol_data}
        """
        self.protocols = protocols

    def generate_message(self, protocol_id, field_values):
        """
        根据协议和字段值生成报文

        Args:
            protocol_id (str): 协议ID
            field_values (dict): 字段值字典 {field_id: value}

        Returns:
            bytes: 生成的报文数据，生成失败则返回None
        """
        try:
            # 获取协议数据
            protocol_data = self.protocols.get(protocol_id)
            if not protocol_data:
                log_debug("错误: 未找到协议数据")
                return None

            # 获取报文格式信息
            message_format = protocol_data.get('message_format', {})
            start_bytes = message_format.get('start_bytes', ["0x59", "0x44"])
            message_id = message_format.get('message_id', "0x00")
            end_bytes = message_format.get('end_bytes', ["0x4B", "0x4A"])
            length_bytes = message_format.get('length_bytes', 1)  # 默认为1字节

            # 获取规定的数据长度
            data_length = 0
            if "data_length" in message_format:
                data_length = int(message_format.get('data_length', "0"), 16)
            else:
                # 根据字段计算数据长度
                fields = protocol_data.get('fields', [])
                for field in fields:
                    byte_position = field.get('byte_position', [])
                    if isinstance(byte_position, list) and byte_position:
                        data_length = max(data_length, max(byte_position) + 1)
                    elif isinstance(byte_position, int):
                        data_length = max(data_length, byte_position + 1)

            log_debug(f"协议ID: {protocol_id}, 报文ID: {message_id}, 数据长度: {data_length} 字节")

            # 计算总报文长度
            # 报文头 + 报文ID + 长度字段 + 数据 + CRC校验 + 报文尾
            total_length = len(start_bytes) + 1 + length_bytes + data_length + 2 + len(end_bytes)
            log_debug(f"计算的总报文长度: {total_length} 字节")

            # 创建固定长度的报文数组
            message_bytes = bytearray(total_length)

            # 1. 填充报文头
            for i, b in enumerate(start_bytes):
                message_bytes[i] = int(b, 16)

            # 2. 填充报文ID
            message_bytes[len(start_bytes)] = int(message_id, 16)

            # 3. 填充长度字段
            length_pos = len(start_bytes) + 1
            if length_bytes == 1:
                message_bytes[length_pos] = data_length
            else:
                message_bytes[length_pos] = data_length & 0xFF  # 低字节
                message_bytes[length_pos + 1] = (data_length >> 8) & 0xFF  # 高字节

            # 4. 填充数据部分 - 初始化为全0
            data_start = len(start_bytes) + 1 + length_bytes
            data_end = data_start + data_length

            # 5. 根据字段信息填充数据
            fields = protocol_data.get('fields', [])
            for field in fields:
                field_id = field.get('id', '')
                field_name = field.get('name', '')
                field_value = field_values.get(field_id)

                if field_value is None:
                    continue

                field_type = field.get('type', 'Unsigned')
                field_length = field.get('length', 1)
                precision = field.get('precision', 1)
                offset = field.get('offset', 0)
                byte_position = field.get('byte_position', [])
                bit_position = field.get('bit_position', None)

                try:
                    # 处理不同的字段类型
                    if field_type in ['Unsigned', 'Signed']:
                        # 将字符串转换为数值
                        try:
                            if not field_value or field_value.strip() == '':
                                numeric_value = 0
                            elif field_value.startswith('0x'):
                                numeric_value = int(field_value, 16)
                            else:
                                numeric_value = float(field_value)
                                if precision != 1 or offset != 0:
                                    numeric_value = (numeric_value - offset) / precision
                                numeric_value = int(round(numeric_value))
                        except ValueError:
                            log_debug(f"无法将字段 {field_id} 的值 '{field_value}' 转换为数值，使用默认值0")
                            numeric_value = 0

                        # 根据字段长度转换为字节
                        if field_length == 1:
                            value_bytes = [numeric_value & 0xFF]
                        elif field_length == 2:
                            value_bytes = [numeric_value & 0xFF, (numeric_value >> 8) & 0xFF]
                        elif field_length == 4:
                            value_bytes = [
                                numeric_value & 0xFF,
                                (numeric_value >> 8) & 0xFF,
                                (numeric_value >> 16) & 0xFF,
                                (numeric_value >> 24) & 0xFF
                            ]
                        else:
                            value_bytes = [(numeric_value >> (i * 8)) & 0xFF for i in range(field_length)]

                        # 填充到数据字节
                        if isinstance(byte_position, list):
                            # 多字节字段
                            for i, pos in enumerate(byte_position):
                                if i < len(value_bytes) and data_start + pos < len(message_bytes):
                                    message_bytes[data_start + pos] = value_bytes[i]

                        elif isinstance(byte_position, int):
                            # 单字节字段，但可能只使用部分位
                            if data_start + byte_position >= len(message_bytes):
                                continue

                            if bit_position:
                                # 有位定义，只修改指定位
                                if isinstance(bit_position, list):
                                    # 多位
                                    mask = 0
                                    for bit in bit_position:
                                        mask |= (1 << bit)

                                    # 清除原有位
                                    message_bytes[data_start + byte_position] &= ~mask

                                    # 设置新值
                                    min_bit = min(bit_position)
                                    message_bytes[data_start + byte_position] |= ((numeric_value << min_bit) & mask)

                                elif isinstance(bit_position, int):
                                    # 单位
                                    # 清除原有位
                                    message_bytes[data_start + byte_position] &= ~(1 << bit_position)

                                    # 设置新值
                                    if numeric_value:
                                        message_bytes[data_start + byte_position] |= (1 << bit_position)
                            else:
                                # 没有位定义，使用整个字节
                                message_bytes[data_start + byte_position] = value_bytes[0]

                except Exception as e:
                    log_debug(f"设置字段 {field_id} 值时出错: {str(e)}")
                    continue

            # 6. 计算CRC校验
            crc_data = message_bytes[len(start_bytes):data_end]
            crc = self.calculate_crc16(crc_data)
            crc_pos = data_end
            message_bytes[crc_pos] = (crc >> 8) & 0xFF  # 高字节
            message_bytes[crc_pos + 1] = crc & 0xFF  # 低字节

            # 7. 填充报文尾
            for i, b in enumerate(end_bytes):
                message_bytes[crc_pos + 2 + i] = int(b, 16)

            # 打印最终报文结构
            log_debug("\n最终报文结构:")
            log_debug(f"报文头: {message_bytes[:len(start_bytes)].hex(' ').upper()}")
            log_debug(f"报文ID: {message_bytes[len(start_bytes):len(start_bytes) + 1].hex(' ').upper()}")

            if length_bytes == 1:
                log_debug(
                    f"长度字段(单字节): {message_bytes[length_pos:length_pos + 1].hex(' ').upper()} (十进制: {message_bytes[length_pos]})")
            else:
                length_value = message_bytes[length_pos] + (message_bytes[length_pos + 1] << 8)
                log_debug(
                    f"长度字段(双字节): {message_bytes[length_pos:length_pos + 2].hex(' ').upper()} (十进制: {length_value})")

            log_debug(f"数据部分: {message_bytes[data_start:data_end].hex(' ').upper()} ({data_length} 字节)")
            log_debug(f"CRC校验: {message_bytes[crc_pos:crc_pos + 2].hex(' ').upper()}")
            log_debug(f"报文尾: {message_bytes[crc_pos + 2:].hex(' ').upper()}")
            log_debug(f"完整报文: {message_bytes.hex(' ').upper()}")
            log_debug(f"完整报文长度: {len(message_bytes)} 字节")

            return bytes(message_bytes)

        except Exception as e:
            log_debug(f"生成报文错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def parse_message(self, message_bytes):
        """
        解析报文

        Args:
            message_bytes (bytes): 报文数据

        Returns:
            tuple: (protocol_id, parsed_data) 协议ID和解析后的数据，未识别则返回(None, None)
        """
        try:
            # 检查报文是否符合YD协议格式
            if len(message_bytes) >= 8 and message_bytes.startswith(b'\x59\x44'):
                # 提取报文ID
                message_id = message_bytes[2]
                message_id_hex = f"{message_id:02X}h"

                # 查找对应协议
                for protocol_id, protocol_data in self.protocols.items():
                    if protocol_data.get('message_id', '') == message_id_hex:
                        # 解析找到的协议
                        parsed_data = self.parse_protocol_message(protocol_data, message_bytes)
                        if parsed_data:
                            # 发送解析完成信号
                            self.message_parsed.emit(protocol_id, parsed_data)
                            return protocol_id, parsed_data

            # 如果没有匹配的协议，尝试所有协议解析
            for protocol_id, protocol_data in self.protocols.items():
                parsed_data = self.parse_protocol_message(protocol_data, message_bytes)
                if parsed_data:
                    # 发送解析完成信号
                    self.message_parsed.emit(protocol_id, parsed_data)
                    return protocol_id, parsed_data

            return None, None

        except Exception as e:
            log_debug(f"解析报文错误: {str(e)}")
            return None, None

    def parse_protocol_message(self, protocol_data, message_bytes):
        """
        根据协议定义解析报文

        Args:
            protocol_data (dict): 协议数据
            message_bytes (bytes): 报文数据

        Returns:
            dict: 解析结果，解析失败则返回None
        """
        try:
            # 获取报文格式信息
            message_format = protocol_data.get('message_format', {})
            start_bytes = message_format.get('start_bytes', ["0x59", "0x44"])
            message_id = message_format.get('message_id', "0x00")
            end_bytes = message_format.get('end_bytes', ["0x4B", "0x4A"])
            # 新增: 检查是否使用2字节数据长度
            length_bytes = message_format.get('length_bytes', 1)  # 默认为1字节

            # 转换为字节格式
            start_bytes_value = bytes([int(b, 16) for b in start_bytes])
            message_id_value = int(message_id, 16)
            end_bytes_value = bytes([int(b, 16) for b in end_bytes])

            # 判断报文格式
            # 情况1: 有报文头和报文尾
            if (len(message_bytes) >= len(start_bytes_value) + len(end_bytes_value) + 4 and
                    message_bytes.startswith(start_bytes_value) and
                    message_bytes.endswith(end_bytes_value)):

                # 提取数据部分（不含报文头、报文尾和校验码）
                data_start = len(start_bytes_value)
                data_end = len(message_bytes) - len(end_bytes_value) - 2  # 减去2字节CRC

                # 检查报文ID
                if message_bytes[data_start] == message_id_value:
                    # 根据长度字节数提取数据
                    if length_bytes == 1:
                        # 单字节数据长度
                        data_bytes = message_bytes[data_start:data_end]
                        return self.parse_fields(protocol_data, data_bytes[2:], raw_message=message_bytes)
                    else:
                        # 两字节数据长度(小端格式)
                        data_length = message_bytes[data_start + 1] + (message_bytes[data_start + 2] << 8)
                        # 实际数据从第4个字节开始(报文头2字节+ID 1字节+长度2字节)
                        data_bytes = message_bytes[data_start:data_start + 3 + data_length]
                        return self.parse_fields(protocol_data, data_bytes[3:], raw_message=message_bytes)

            # 情况2: 只有报文ID，没有完整的报文头尾
            else:
                # 尝试从任意位置查找报文ID
                for i in range(len(message_bytes) - 2):
                    if message_bytes[i] == message_id_value:
                        if length_bytes == 1:
                            # 单字节长度格式
                            # 检查后面的一个字节是否是长度字段
                            length = message_bytes[i + 1]

                            # 如果剩余数据长度符合长度字段，尝试解析
                            if i + 2 + length <= len(message_bytes):
                                data_bytes = message_bytes[i + 2:i + 2 + length]
                                return self.parse_fields(protocol_data, data_bytes,
                                                         raw_message=message_bytes[i:i + 2 + length])
                        else:
                            # 两字节长度格式(小端)
                            if i + 2 < len(message_bytes):
                                # 读取两字节长度(小端格式)
                                length = message_bytes[i + 1] + (message_bytes[i + 2] << 8)

                                # 如果剩余数据长度符合长度字段，尝试解析
                                if i + 3 + length <= len(message_bytes):
                                    data_bytes = message_bytes[i + 3:i + 3 + length]
                                    return self.parse_fields(protocol_data, data_bytes,
                                                             raw_message=message_bytes[i:i + 3 + length])

            return None

        except Exception as e:
            log_debug(f"解析协议报文错误: {str(e)}")
            return None

    def parse_fields(self, protocol_data, data_bytes, raw_message=None):
        """
        解析报文字段

        Args:
            protocol_data (dict): 协议数据
            data_bytes (bytes): 数据部分字节
            raw_message (bytes): 原始报文数据

        Returns:
            dict: 解析结果
        """
        result = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'protocol_id': protocol_data.get('protocol_id', ''),
            'protocol_name': protocol_data.get('protocol_name', ''),
            'message_id': protocol_data.get('message_id', ''),
            'message_type': protocol_data.get('message_type', ''),
            'raw_message': ' '.join([f"{b:02X}" for b in raw_message]) if raw_message else '',
            'fields': {}
        }

        # 解析每个字段
        fields = protocol_data.get('fields', [])
        for field in fields:
            field_id = field.get('id', '')
            field_name = field.get('name', '')
            field_type = field.get('type', 'Unsigned')
            field_length = field.get('length', 1)
            precision = field.get('precision', 1)
            offset = field.get('offset', 0)
            byte_position = field.get('byte_position', [])
            bit_position = field.get('bit_position', None)
            values = field.get('values', [])

            # 根据字段类型解析值
            try:
                # 检查字节位置是否在数据范围内
                if isinstance(byte_position, list):
                    # 多字节字段
                    if max(byte_position) >= len(data_bytes):
                        continue

                    # 提取字段数据
                    field_bytes = bytes([data_bytes[pos] for pos in byte_position])

                elif isinstance(byte_position, int):
                    # 单字节字段，但可能只使用部分位
                    if byte_position >= len(data_bytes):
                        continue

                    byte_value = data_bytes[byte_position]

                    # 如果有位定义，提取指定位
                    if bit_position:
                        if isinstance(bit_position, list):
                            # 多位
                            mask = 0
                            for bit in bit_position:
                                mask |= (1 << bit)

                            # 提取位并右移到最低位
                            min_bit = min(bit_position)
                            bit_value = (byte_value & mask) >> min_bit

                            # 保存解析值和描述
                            value = bit_value

                            # 查找对应的描述
                            description = None
                            for val_info in values:
                                val = int(val_info.get('value', '0'), 16)
                                if val == value:
                                    description = val_info.get('description', '')
                                    break

                            # 保存到结果
                            result['fields'][field_id] = {
                                'name': field_name,
                                'value': value,
                                'hex': f"0x{value:X}",
                                'description': description
                            }
                            continue

                        elif isinstance(bit_position, int):
                            # 单位
                            bit_value = (byte_value >> bit_position) & 0x01

                            # 保存解析值和描述
                            value = bit_value

                            # 查找对应的描述
                            description = None
                            for val_info in values:
                                val = int(val_info.get('value', '0'), 16)
                                if val == value:
                                    description = val_info.get('description', '')
                                    break

                            # 保存到结果
                            result['fields'][field_id] = {
                                'name': field_name,
                                'value': value,
                                'hex': f"0x{value:X}",
                                'description': description
                            }
                            continue

                    # 没有位定义，使用整个字节
                    field_bytes = bytes([byte_value])

                else:
                    continue

                # 解析字段值
                if field_type == 'Unsigned':
                    # 根据长度解析无符号整数
                    if len(field_bytes) == 1:
                        value = field_bytes[0]
                    elif len(field_bytes) == 2:
                        value = struct.unpack('<H', field_bytes)[0]
                    elif len(field_bytes) == 4:
                        value = struct.unpack('<I', field_bytes)[0]
                    else:
                        value = int.from_bytes(field_bytes, byteorder='little')

                    # 应用精度和偏移
                    if precision != 1 or offset != 0:
                        value = value * precision + offset

                    # 查找对应的描述
                    description = None
                    if values:
                        for val_info in values:
                            val = int(val_info.get('value', '0'), 16)
                            if val == value:
                                description = val_info.get('description', '')
                                break

                    # 保存到结果
                    result['fields'][field_id] = {'name': field_name,
                                                  'value': value,
                                                  'raw_value': value if precision == 1 and offset == 0 else round(
                                                      (value - offset) / precision),
                                                  'hex': f"0x{value if precision == 1 and offset == 0 else round((value - offset) / precision):X}",
                                                  'description': description
                                                  }

                elif field_type == 'Signed':
                    # 根据长度解析有符号整数
                    if len(field_bytes) == 1:
                        value = struct.unpack('<b', field_bytes)[0]
                    elif len(field_bytes) == 2:
                        value = struct.unpack('<h', field_bytes)[0]
                    elif len(field_bytes) == 4:
                        value = struct.unpack('<i', field_bytes)[0]
                    else:
                        # 转换为有符号数
                        unsigned_value = int.from_bytes(field_bytes, byteorder='little')
                        bit_length = len(field_bytes) * 8
                        value = unsigned_value if unsigned_value < (1 << (bit_length - 1)) else unsigned_value - (
                                    1 << bit_length)

                    # 应用精度和偏移
                    if precision != 1 or offset != 0:
                        value = value * precision + offset

                    # 保存到结果
                    result['fields'][field_id] = {
                        'name': field_name,
                        'value': value,
                        'raw_value': value if precision == 1 and offset == 0 else round((value - offset) / precision),
                        'hex': f"0x{value if precision == 1 and offset == 0 else (value - offset) / precision:X}",
                        'description': None
                    }

                else:
                    # 其他类型，保存原始字节
                    result['fields'][field_id] = {
                        'name': field_name,
                        'value': ' '.join([f"{b:02X}" for b in field_bytes]),
                        'raw_value': field_bytes,
                        'hex': '0x' + ''.join([f"{b:02X}" for b in field_bytes]),
                        'description': None
                    }

            except Exception as e:
                log_debug(f"解析字段 {field_name}({field_id}) 错误: {str(e)}")
                continue

        return result

    def generate_protocol_message(self, protocol_id):
        """
        生成协议报文

        Args:
            protocol_id (str): 协议ID
        """
        try:
            log_debug(f"当前需要处理的协议: {protocol_id}")

            # 获取协议数据
            protocol_data = self.config_parser.get_protocol(protocol_id)
            if not protocol_data:
                self.add_log_message(f"错误: 未找到协议 {protocol_id} 的数据", "error")
                return

            # 输出当前协议的字段列表
            log_debug("当前协议可能的字段ID列表:")
            fields = protocol_data.get('fields', [])
            for field in fields:
                field_id = field.get('id', '')
                field_name = field.get('name', '')
                new_field_id = f"{protocol_id}_{field_id}"
                log_debug(f"  {new_field_id} ({field_name})")

            # 只获取当前协议的字段值，使用专门的错误处理
            try:
                protocol_field_values_with_prefix = self.protocol_ui_generator.get_field_values(protocol_id)
            except Exception as e:
                log_debug(f"获取字段值时出错: {str(e)}")
                self.add_log_message(f"获取字段值时出错: {str(e)}", "error")
                return

            # 转换为不带前缀的字段值，用于生成报文
            protocol_field_values = {}
            prefix_len = len(protocol_id) + 1  # 协议ID + 下划线的长度

            for field_id, value in protocol_field_values_with_prefix.items():
                # 移除协议前缀
                if field_id.startswith(f"{protocol_id}_"):
                    original_id = field_id[prefix_len:]
                    protocol_field_values[original_id] = value
                    log_debug(f"字段映射: {field_id} -> {original_id} = {value}")

            # 打印最终要使用的字段值
            log_debug("\n最终使用的字段值:")
            if protocol_field_values:
                for field_id, value in protocol_field_values.items():
                    log_debug(f"  {field_id} = {value}")
            else:
                log_debug("  无有效字段值")

            # 使用过滤后的字段值生成报文
            try:
                message = self.protocol_parser.generate_message(protocol_id, protocol_field_values)

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
                log_debug(f"生成或发送报文时出错: {str(e)}")
                self.add_log_message(f"生成报文时出错: {str(e)}", "error")

        except Exception as e:
            log_debug(f"生成报文过程中出现未处理的错误: {str(e)}")
            self.add_log_message(f"生成报文错误: {str(e)}", "error")


    def calculate_crc16(self, data):
        """
        计算CRC16校验码 (Modbus)

        Args:
            data (bytes): 要计算的数据

        Returns:
            int: CRC16校验码
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc