# -*- coding: utf-8 -*-
"""
@Author     : 王舒
@Company    : 黑龙江天有为科技有限公司
@Date       : 2025-05-10
@Python     : 3.10
@Description: 配置文件解析模块，负责解析INI配置和JSON协议文件，增加JSON校验功能
"""
import os
import json
import configparser
from PyQt5.QtWidgets import QMessageBox
from log_manager import log_debug, log_info, log_error


class ConfigParser:
    """配置文件解析器，用于解析INI配置文件和JSON协议文件"""

    def __init__(self):
        self.config = None  # INI配置对象
        self.protocols = {}  # 协议信息字典 {protocol_id: protocol_data}
        self.config_path = ""  # 配置文件路径
        self.plugins_dir = ""  # 插件目录
        self.validation_errors = []  # 验证错误列表

    def load_config(self, config_path):
        """
        加载INI配置文件

        Args:
            config_path (str): 配置文件路径

        Returns:
            bool: 是否成功加载
        """
        try:
            if not os.path.exists(config_path):
                QMessageBox.warning(None, "错误", f"配置文件不存在: {config_path}")
                return False

            self.config_path = config_path
            self.config = configparser.ConfigParser()
            self.config.read(config_path, encoding='utf-8')

            # 获取插件目录
            self.plugins_dir = self.config.get('General', 'pluginsdir', fallback='plugins')

            # 确保插件目录是绝对路径
            if not os.path.isabs(self.plugins_dir):
                base_dir = os.path.dirname(os.path.abspath(config_path))
                self.plugins_dir = os.path.join(base_dir, self.plugins_dir)

            # 清空之前的协议信息
            self.protocols.clear()
            self.validation_errors = []

            # 加载各个协议文件
            for section in self.config.sections():
                if section != 'General':
                    protocol_id = section
                    json_file = self.config.get(section, 'file', fallback=None)

                    if json_file:
                        # 构建JSON文件的完整路径
                        json_path = os.path.join(self.plugins_dir, json_file)

                        if os.path.exists(json_path):
                            # 加载并验证JSON协议文件
                            protocol_data = self.load_protocol_json(json_path)
                            if protocol_data:
                                # 验证协议数据
                                is_valid, error_message = self.validate_protocol_json(protocol_data)
                                if is_valid:
                                    # 添加协议ID信息
                                    protocol_data['protocol_id'] = protocol_id
                                    self.protocols[protocol_id] = protocol_data
                                    log_info(f"成功加载并验证协议: {protocol_id}")
                                else:
                                    error = f"协议 {protocol_id} 验证失败: {error_message}"
                                    self.validation_errors.append(error)
                                    log_error(error)
                            else:
                                error = f"协议 {protocol_id}: 无法加载JSON文件 {json_file}"
                                self.validation_errors.append(error)
                                log_error(error)
                        else:
                            error = f"协议 {protocol_id}: 文件不存在: {json_file}"
                            self.validation_errors.append(error)
                            log_error(error)

            # 显示验证错误
            if self.validation_errors:
                error_message = "部分协议加载失败:\n\n" + "\n".join(self.validation_errors)
                QMessageBox.warning(None, "验证错误", error_message)

            # 验证协议兼容性
            is_compatible, compatibility_report = self.validate_protocol_compatibility()
            if not is_compatible:
                QMessageBox.warning(None, "协议兼容性问题", compatibility_report)
                log_warning(compatibility_report)

            return len(self.protocols) > 0

        except Exception as e:
            error_msg = f"加载配置文件错误: {str(e)}"
            QMessageBox.critical(None, "错误", error_msg)
            log_error(error_msg)
            return False

    def load_protocol_json(self, json_path):
        """
        加载JSON协议文件

        Args:
            json_path (str): JSON文件路径

        Returns:
            dict: 协议数据，加载失败则返回None
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                protocol_data = json.load(f)
            return protocol_data
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析错误({json_path}): {str(e)}"
            log_error(error_msg)
            return None
        except Exception as e:
            error_msg = f"加载协议JSON文件错误({json_path}): {str(e)}"
            log_error(error_msg)
            return None

    def validate_protocol_json(self, protocol_data):
        """
        验证协议JSON数据结构

        Args:
            protocol_data (dict): 要验证的协议数据

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # 检查protocol_data是否为字典
            if not isinstance(protocol_data, dict):
                return False, "协议数据必须是JSON对象"

            # 检查必需的顶级字段
            required_fields = ['protocol_name', 'protocol_version', 'message_id', 'message_type']
            missing_fields = [field for field in required_fields if field not in protocol_data]
            if missing_fields:
                return False, f"缺少必需字段: {', '.join(missing_fields)}"

            # 检查fields数组
            fields = protocol_data.get('fields')
            if not fields:
                return False, "协议必须包含'fields'数组"

            if not isinstance(fields, list):
                return False, "'fields'必须是数组"

            # 验证每个字段
            field_ids = set()
            for i, field in enumerate(fields):
                if not isinstance(field, dict):
                    return False, f"索引{i}处的字段必须是对象"

                # 检查必需的字段属性
                required_props = ['name', 'id', 'byte_position']
                missing_props = [prop for prop in required_props if prop not in field]
                if missing_props:
                    return False, f"字段'{field.get('name', f'索引{i}处')}' 缺少必需属性: {', '.join(missing_props)}"

                # 检查字段ID重复
                field_id = field.get('id')
                if field_id in field_ids:
                    return False, f"重复的字段ID: {field_id}"
                field_ids.add(field_id)

                # 验证byte_position
                byte_pos = field.get('byte_position')
                if not (isinstance(byte_pos, int) or isinstance(byte_pos, list)):
                    return False, f"字段'{field.get('id')}'的byte_position无效(必须是整数或数组)"

            # 检查message_format部分
            message_format = protocol_data.get('message_format')
            if not message_format:
                return False, "协议必须包含'message_format'部分"

            if not isinstance(message_format, dict):
                return False, "'message_format'必须是对象"

            # 检查必需的消息格式字段
            required_format_fields = ['start_bytes', 'message_id', 'end_bytes']
            missing_format_fields = [field for field in required_format_fields if field not in message_format]
            if missing_format_fields:
                return False, f"缺少必需的message_format字段: {', '.join(missing_format_fields)}"

            # 检查校验和字段
            checksum = message_format.get('checksum')
            if not checksum or not isinstance(checksum, str):
                return False, "message_format必须包含有效的'checksum'字段"

            # 检查起始和结束字节格式
            start_bytes = message_format.get('start_bytes')
            end_bytes = message_format.get('end_bytes')

            if not isinstance(start_bytes, list) or not isinstance(end_bytes, list):
                return False, "start_bytes和end_bytes必须是数组"

            for byte in start_bytes + end_bytes:
                if not isinstance(byte, str) or not byte.startswith("0x"):
                    return False, f"start_bytes和end_bytes中的所有值必须是十六进制字符串格式，例如'0x59'"

            return True, ""

        except Exception as e:
            return False, f"验证错误: {str(e)}"

    def validate_all_protocols(self):
        """
        验证所有已加载的协议并生成报告

        Returns:
            tuple: (all_valid, validation_report)
        """
        validation_results = []
        all_valid = True

        for protocol_id, protocol_data in self.protocols.items():
            is_valid, error_message = self.validate_protocol_json(protocol_data)
            validation_results.append({
                "protocol_id": protocol_id,
                "valid": is_valid,
                "error": error_message if not is_valid else ""
            })

            if not is_valid:
                all_valid = False

        # 生成报告
        report = "协议验证报告:\n\n"
        for result in validation_results:
            if result["valid"]:
                report += f"✅ {result['protocol_id']}: 有效\n"
            else:
                report += f"❌ {result['protocol_id']}: 无效 - {result['error']}\n"

        return all_valid, report

    def validate_protocol_compatibility(self):
        """
        验证不同协议文件之间的兼容性

        Returns:
            tuple: (is_compatible, compatibility_report)
        """
        compatibility_issues = []
        is_compatible = True

        # 检查消息ID冲突
        message_id_map = {}
        for protocol_id, protocol_data in self.protocols.items():
            message_id = protocol_data.get('message_id')
            if message_id in message_id_map:
                compatibility_issues.append(
                    f"消息ID冲突: '{message_id}' 同时被 '{protocol_id}' 和 '{message_id_map[message_id]}' 使用"
                )
                is_compatible = False
            else:
                message_id_map[message_id] = protocol_id

        # 检查消息格式定义的一致性
        format_definitions = {}
        for protocol_id, protocol_data in self.protocols.items():
            message_format = protocol_data.get('message_format', {})
            checksum = message_format.get('checksum', '')
            format_key = json.dumps(message_format.get('start_bytes', [])) + json.dumps(
                message_format.get('end_bytes', []))

            if format_key in format_definitions and format_definitions[format_key][1] != checksum:
                compatibility_issues.append(
                    f"消息格式不一致: '{protocol_id}' 和 '{format_definitions[format_key][0]}' 使用相同的起始和结束字节，但校验和方法不同"
                )
                is_compatible = False
            else:
                format_definitions[format_key] = (protocol_id, checksum)

        # 检查字段ID重复
        all_field_ids = {}
        for protocol_id, protocol_data in self.protocols.items():
            fields = protocol_data.get('fields', [])
            for field in fields:
                field_id = field.get('id', '')
                qualified_field_id = f"{protocol_id}_{field_id}"

                if field_id in all_field_ids and all_field_ids[field_id] != protocol_id:
                    # 这里不算作错误，因为不同协议可以有相同的字段ID
                    log_debug(
                        f"注意: 字段ID '{field_id}' 在多个协议中使用: '{protocol_id}' 和 '{all_field_ids[field_id]}'")
                else:
                    all_field_ids[field_id] = protocol_id

        # 生成报告
        report = "协议兼容性报告:\n\n"
        if is_compatible:
            report += "✅ 所有协议相互兼容\n"
        else:
            report += "❌ 发现兼容性问题:\n"
            for issue in compatibility_issues:
                report += f"   - {issue}\n"

        return is_compatible, report

    def get_validation_errors(self):
        """
        获取验证错误列表

        Returns:
            list: 验证错误列表
        """
        return self.validation_errors

    def get_protocols(self):
        """
        获取所有协议信息

        Returns:
            dict: 协议信息字典 {protocol_id: protocol_data}
        """
        return self.protocols

    def get_protocol(self, protocol_id):
        """
        获取指定协议信息

        Args:
            protocol_id (str): 协议ID

        Returns:
            dict: 协议数据，未找到则返回None
        """
        return self.protocols.get(protocol_id, None)

    def get_config_path(self):
        """
        获取配置文件路径

        Returns:
            str: 配置文件路径
        """
        return self.config_path

    def get_plugins_dir(self):
        """
        获取插件目录

        Returns:
            str: 插件目录路径
        """
        return self.plugins_dir