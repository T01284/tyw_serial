# -*- coding: utf-8 -*-
"""
@Author     : 架构修改
@Company    : 黑龙江天有为科技有限公司
@Date       : 2025-05-10
@Python     : 3.10
@Description: 配置文件解析模块，负责解析INI配置和JSON协议文件
"""
import os
import json
import configparser
from PyQt5.QtWidgets import QMessageBox


class ConfigParser:
    """配置文件解析器，用于解析INI配置文件和JSON协议文件"""

    def __init__(self):
        self.config = None  # INI配置对象
        self.protocols = {}  # 协议信息字典 {protocol_id: protocol_data}
        self.config_path = ""  # 配置文件路径
        self.plugins_dir = ""  # 插件目录

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

            # 加载各个协议文件
            for section in self.config.sections():
                if section != 'General':
                    protocol_id = section
                    json_file = self.config.get(section, 'file', fallback=None)

                    if json_file:
                        # 构建JSON文件的完整路径
                        json_path = os.path.join(self.plugins_dir, json_file)

                        if os.path.exists(json_path):
                            # 加载JSON协议文件
                            protocol_data = self.load_protocol_json(json_path)
                            if protocol_data:
                                # 添加协议ID信息
                                protocol_data['protocol_id'] = protocol_id
                                self.protocols[protocol_id] = protocol_data

            return len(self.protocols) > 0

        except Exception as e:
            print(f"加载配置文件错误: {str(e)}")
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
        except Exception as e:
            print(f"加载协议JSON文件错误({json_path}): {str(e)}")
            return None

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