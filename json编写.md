# TYW串口工具通信协议JSON文件编写指南

## 1. 简介

本文档提供了TYW串口工具通信协议配置文件的编写规范。这些JSON格式的配置文件用于定义不同节点之间的通信协议，支持RS485线总线通信。适用于YD-G392等系列产品的通信协议定义和解析。

## 2. 文件命名与目录结构

### 2.1 命名规范

协议文件应按照报文ID进行命名，格式为`[message_id].json`，例如：
- `d0h.json` - IOT周期响应报文
- `d1h.json` - BMS周期响应报文
- `d2h.json` - MCU周期响应报文
- `d3h.json` - ALM周期响应报文
- `d4h.json` - ICM周期响应报文
- `b6h.json` - BMS1静态响应报文

### 2.2 目录结构

协议文件应放置在配置文件指定的插件目录下，默认为`plugins\yd_g392\`。目录结构如下：

```
plugins/
  yd_g392/
    d0h.json
    d1h.json
    d2h.json
    d3h.json
    d4h.json
    b6h.json
    ...
```

## 3. JSON文件结构

协议JSON文件由以下主要部分组成：

1. 协议基本信息
2. 字段定义
3. 消息格式定义

### 3.1 基本结构

```json
{
  "protocol_id": "D3h",
  "protocol_name": "新架构RS485线总线ALM节点通信协议",
  "protocol_version": "V2.01",
  "message_id": "D3h",
  "message_type": "周期响应报文",
  "message_source": "ALM",
  "fields": [
    // 字段定义...
  ],
  "message_format": {
    // 消息格式定义...
  }
}
```

### 3.2 必需字段说明

| 字段名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| protocol_id | 字符串 | 协议ID，必须与文件名一致 | "D3h" |
| protocol_name | 字符串 | 协议名称 | "新架构RS485线总线ALM节点通信协议" |
| protocol_version | 字符串 | 协议版本 | "V2.01" |
| message_id | 字符串 | 报文ID，必须与文件名一致 | "D3h" |
| message_type | 字符串 | 报文类型 | "周期响应报文" 或 "静态响应报文" |
| message_source | 字符串 | 报文来源 | "ALM", "MCU", "BMS", "ICM", "BMS1" 等 |
| fields | 数组 | 字段定义数组 | [] |
| message_format | 对象 | 消息格式定义 | {} |

## 4. 字段定义

每个字段的定义包含以下属性：

```json
{
  "name": "整车状态",
  "id": "B0[0:2]",
  "byte_position": 0,
  "bit_position": [0, 1, 2],
  "type": "Unsigned",
  "length": 1,
  "precision": 1,
  "offset": 0,
  "unit": "-",
  "min_value": 0,
  "max_value": 7,
  "min_hex": "0x0",
  "max_hex": "0x7",
  "default_hex": "0x0",
  "invalid_hex": "0x7",
  "description": "整车状态",
  "values": [
    {"value": "0x0", "description": "设防"},
    {"value": "0x1", "description": "撤防"},
    {"value": "0x2", "description": "Reserved"},
    {"value": "0x3", "description": "Reserved"},
    {"value": "0x4", "description": "整车上电状态"},
    {"value": "0x5", "description": "Reserved"},
    {"value": "0x6", "description": "Reserved"},
    {"value": "0x7", "description": "void"}
  ]
}
```

### 4.1 字段属性说明

| 属性名 | 类型 | 描述 | 示例 | 是否必需 |
|--------|------|------|------|----------|
| name | 字符串 | 字段名称 | "整车状态" | 是 |
| id | 字符串 | 字段ID，用于标识字段位置 | "B0[0:2]", "B1:B2" | 是 |
| byte_position | 数字/数组 | 字段所在字节位置 | 0 或 [0, 1] | 是 |
| bit_position | 数组/null | 位域字段的位位置 | [0, 1, 2] 或 null | 是 |
| type | 字符串 | 数据类型 | "Unsigned", "Signed", "ASCII" | 是 |
| length | 数字 | 字段长度（字节数） | 1, 2, 4 | 是 |
| precision | 数字 | 精度（物理值=总线值*精度+偏移量） | 0.1, 1, 0.01 | 是 |
| offset | 数字 | 偏移量 | 0, -40, -1000 | 是 |
| unit | 字符串 | 单位 | "℃", "V", "A", "-" | 是 |
| min_value | 数字 | 最小物理值 | 0, -40, -1000 | 是 |
| max_value | 数字 | 最大物理值 | 100, 255, 1000 | 是 |
| min_hex | 字符串 | 最小十六进制值 | "0x0" | 是 |
| max_hex | 字符串 | 最大十六进制值 | "0xFF", "0x7" | 是 |
| default_hex | 字符串 | 默认十六进制值 | "0x0", "0xFF" | 是 |
| invalid_hex | 字符串 | 无效十六进制值 | "0xFF", "0x7" | 是 |
| description | 字符串 | 字段描述 | "整车状态" | 是 |
| values | 数组 | 预定义值列表 | [] | 否 |

### 4.2 ID格式说明

字段ID用于标识字段在报文中的位置，格式如下：

- 单字节：`B0` - 表示第0个字节
- 字节范围：`B0:B1` - 表示第0个到第1个字节
- 位域：`B0[0:2]` - 表示第0个字节的第0、1、2位
- 单个位：`B0[3]` - 表示第0个字节的第3位

### 4.3 数据类型

支持的数据类型包括：

- `Unsigned`：无符号整数
- `Signed`：有符号整数
- `ASCII`：ASCII字符

### 4.4 预定义值列表

当字段有固定的可选值时，可以使用`values`属性定义这些值：

```json
"values": [
  {"value": "0x0", "description": "设防"},
  {"value": "0x1", "description": "撤防"},
  // 更多值...
]
```

## 5. 消息格式定义

消息格式定义指定了协议的报文格式，包括起始字节、报文ID、数据长度、结束字节和校验方式：

```json
"message_format": {
  "start_bytes": ["0x59", "0x44"],
  "message_id": "0xD3",
  "data_length": "0x1A",
  "end_bytes": ["0x4B", "0x4A"],
  "checksum": "CRC16-modbus"
}
```

### 5.1 消息格式属性说明

| 属性名 | 类型 | 描述 | 示例 | 是否必需 |
|--------|------|------|------|----------|
| start_bytes | 数组 | 起始字节 | ["0x59", "0x44"] | 是 |
| message_id | 字符串 | 报文ID（十六进制） | "0xD3" | 是 |
| data_length | 字符串 | 数据长度（十六进制） | "0x1A" | 是 |
| end_bytes | 数组 | 结束字节 | ["0x4B", "0x4A"] | 是 |
| checksum | 字符串 | 校验方式 | "CRC16-modbus" | 是 |

## 6. 完整示例

### 6.1 B6h.json（BMS1静态响应报文）

```json
{
  "protocol_id": "B6h",
  "protocol_name": "新架构RS485线总线BMS1节点通信协议",
  "protocol_version": "V2.01",
  "message_id": "B6h",
  "message_type": "静态响应报文",
  "message_source": "BMS1",
  "fields": [
    {
      "name": "硬件版本号",
      "id": "B0",
      "byte_position": 0,
      "bit_position": null,
      "type": "Unsigned",
      "length": 1,
      "precision": 1,
      "offset": 0,
      "unit": "-",
      "min_value": 0,
      "max_value": 6,
      "min_hex": "0x0",
      "max_hex": "0x6",
      "default_hex": "0xFF",
      "invalid_hex": "0xFF",
      "description": "硬件编码，详见《通信设备软硬件编码规则》"
    },
    {
      "name": "电池类型",
      "id": "B64[4:7]",
      "byte_position": 64,
      "bit_position": [4, 5, 6, 7],
      "type": "Unsigned",
      "length": 1,
      "precision": 1,
      "offset": 0,
      "unit": "-",
      "min_value": 0,
      "max_value": 1,
      "min_hex": "0x0",
      "max_hex": "0x1",
      "default_hex": "0xF",
      "invalid_hex": "0xF",
      "description": "电池类型",
      "values": [
        {"value": "0x0", "description": "锰酸锂"},
        {"value": "0x1", "description": "磷酸铁锂"},
        {"value": "0x2", "description": "三元锂"},
        {"value": "0x3", "description": "Reserved"},
        {"value": "0x4", "description": "Reserved"},
        {"value": "0x5", "description": "石墨烯铅酸电池"},
        {"value": "0x6", "description": "普通铅酸电池"},
        {"value": "0x7", "description": "钠电"},
        {"value": "0x8-0xE", "description": "Reserved"},
        {"value": "0xF", "description": "void"}
      ]
    }
  ],
  "message_format": {
    "start_bytes": ["0x59", "0x44"],
    "message_id": "0xB6",
    "data_length": "0x56",
    "end_bytes": ["0x4B", "0x4A"],
    "checksum": "CRC16-modbus"
  }
}
```

### 6.2 D3h.json（ALM周期响应报文）

```json
{
  "protocol_id": "D3h",
  "protocol_name": "新架构RS485线总线ALM节点通信协议",
  "protocol_version": "V2.01",
  "message_id": "D3h",
  "message_type": "周期响应报文",
  "message_source": "ALM",
  "fields": [
    {
      "name": "整车状态",
      "id": "B0[0:2]",
      "byte_position": 0,
      "bit_position": [0, 1, 2],
      "type": "Unsigned",
      "length": 1,
      "precision": 1,
      "offset": 0,
      "unit": "-",
      "min_value": 0,
      "max_value": 7,
      "min_hex": "0x0",
      "max_hex": "0x7",
      "default_hex": "0x0",
      "invalid_hex": "0x7",
      "description": "整车状态",
      "values": [
        {"value": "0x0", "description": "设防"},
        {"value": "0x1", "description": "撤防"},
        {"value": "0x2", "description": "Reserved"},
        {"value": "0x3", "description": "Reserved"},
        {"value": "0x4", "description": "整车上电状态"},
        {"value": "0x5", "description": "Reserved"},
        {"value": "0x6", "description": "Reserved"},
        {"value": "0x7", "description": "void"}
      ]
    },
    {
      "name": "整车开关机状态",
      "id": "B0[3:7]",
      "byte_position": 0,
      "bit_position": [3, 4, 5, 6, 7],
      "type": "Unsigned",
      "length": 1,
      "precision": 1,
      "offset": 0,
      "unit": "-",
      "min_value": 0,
      "max_value": 31,
      "min_hex": "0x0",
      "max_hex": "0x1F",
      "default_hex": "0x1F",
      "invalid_hex": "0x1F",
      "description": "整车开关机状态",
      "values": [
        {"value": "0x0", "description": "开机状态-电门锁开机"},
        {"value": "0x1", "description": "开机状态-免钥匙开机_IOT"},
        {"value": "0x2", "description": "开机状态-免钥匙开机（APP)_BLE"},
        {"value": "0x3", "description": "开机状态-靠近解锁开机_BLE"},
        {"value": "0x4", "description": "开机状态-NFC开机_BLE"},
        {"value": "0x5", "description": "开机状态-遥控钥匙开机"},
        {"value": "0x6", "description": "开机状态-密码开机"},
        {"value": "0x7", "description": "开机状态-座垫感应开机"},
        {"value": "0x8", "description": "关机状态-电门锁关机"},
        {"value": "0x9", "description": "关机状态-免钥匙关机_IOT"},
        {"value": "0xA", "description": "关机状态-免钥匙关机_BLE"},
        {"value": "0xB", "description": "关机状态-自动关机"},
        {"value": "0xC", "description": "关机状态-强制关机"},
        {"value": "0xD", "description": "关机状态-上电关机"},
        {"value": "0xE", "description": "关机状态-掉电关机"},
        {"value": "0xF", "description": "关机状态-NFC关机"},
        {"value": "0x10", "description": "关机状态-遥控钥匙关机"},
        {"value": "0x11", "description": "边撑开机"},
        {"value": "0x12", "description": "边撑关机"},
        {"value": "0x13-0x1E", "description": "Reserved"},
        {"value": "0x1F", "description": "void"}
      ]
    }
  ],
  "message_format": {
    "start_bytes": ["0x59", "0x44"],
    "message_id": "0xD3",
    "data_length": "0x1A",
    "end_bytes": ["0x4B", "0x4A"],
    "checksum": "CRC16-modbus"
  }
}
```

## 7. 常见问题及解决方案

### 7.1 协议未生成对应Tab的问题

如果在加载协议时没有生成对应的Tab页，请检查以下几点：

1. 确保JSON文件中包含`protocol_id`字段，且与文件名一致
2. 确保文件位于正确的目录下
3. 检查JSON格式是否正确，特别是数组和对象的括号匹配
4. 对于`bit_position`为`null`的字段，有些系统可能需要使用空数组`[]`替代

### 7.2 字段显示问题

如果字段值显示不正确，请检查：

1. 确保`precision`和`offset`值正确
2. 检查`min_value`和`max_value`范围是否合理
3. 对于预定义值，确保`values`数组中的值覆盖了所有可能的情况

### 7.3 校验错误

如果报文校验失败，请检查：

1. 确保`message_format`中的所有字段正确
2. 确保`checksum`字段设置为正确的校验方式（目前仅支持"CRC16-modbus"）

## 8. 协议测试与验证

完成协议JSON文件编写后，建议进行以下测试：

1. **格式验证**：使用JSON验证工具验证文件格式
2. **加载测试**：将文件放置到正确目录，测试是否能正确加载
3. **字段测试**：逐一测试各字段的输入和显示
4. **报文生成测试**：测试是否能正确生成报文
5. **报文解析测试**：使用实际设备发送的报文，测试是否能正确解析

## 9. 参考资料

- 《新架构RS485线总线ICM节点通信协议(2024版)V2.01》
