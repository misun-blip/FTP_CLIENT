"""
FTP响应解析模块
负责解析FTP服务器的响应码和响应消息
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import IntEnum


class FTPResponseCode(IntEnum):
    """FTP响应码枚举"""
    # 积极完成响应
    READY_FOR_NEW_USER = 220
    SERVICE_CLOSING = 221
    DATA_CONNECTION_OPEN = 225
    CLOSING_DATA_CONNECTION = 226
    ENTERING_PASSIVE_MODE = 227
    LOGGED_IN = 230
    FILE_ACTION_OK = 250
    PATHNAME_CREATED = 257
    
    # 需要进一步操作
    SEND_PASSWORD = 331
    NEED_ACCOUNT = 332
    FILE_ACTION_PENDING = 350
    
    # 临时失败
    SERVICE_NOT_READY = 421
    CANNOT_OPEN_DATA_CONNECTION = 425
    TRANSFER_ABORTED = 426
    
    # 永久失败
    INVALID_COMMAND = 500
    BAD_SEQUENCE = 503
    NOT_LOGGED_IN = 530
    FILE_UNAVAILABLE = 550
    PAGE_TYPE_UNKNOWN = 551
    EXCEEDED_STORAGE = 552
    FILE_NAME_NOT_ALLOWED = 553


@dataclass
class FTPResponse:
    """FTP响应对象"""
    code: int
    message: str
    raw: str
    is_multiline: bool = False
    lines: List[str] = None
    
    def __post_init__(self):
        if self.lines is None:
            self.lines = []
            
    @classmethod
    def parse(cls, raw_response: str) -> 'FTPResponse':
        """
        解析原始FTP响应字符串
        
        Args:
            raw_response: 原始响应字符串
            
        Returns:
            FTPResponse对象
        """
        lines = raw_response.strip().split('\r\n')
        if not lines:
            raise ValueError("空响应")
            
        first_line = lines[0]
        
        # 解析响应码（前3个字符）
        if len(first_line) < 3 or not first_line[:3].isdigit():
            raise ValueError(f"无效的响应格式: {first_line}")
            
        code = int(first_line[:3])
        
        # 判断是否是多行响应
        # 多行响应的第一个字符是 '-' 或第4个字符是 '-'
        is_multiline = False
        if len(first_line) > 3:
            if first_line[3] == '-':
                is_multiline = True
                
        # 提取消息内容
        if is_multiline:
            # 多行响应：跳过第一行的 '-' 和后续的响应码
            messages = []
            for i, line in enumerate(lines):
                if i == 0:
                    # 第一行去掉响应码和 '-'
                    message = line[4:].strip()
                else:
                    # 后续行，如果是最后一行可能包含响应码
                    if len(line) >= 4 and line[:3].isdigit() and line[3] == ' ':
                        message = line[4:].strip()
                    else:
                        message = line.strip()
                messages.append(message)
            message = '\n'.join(messages)
        else:
            # 单行响应：去掉响应码
            if len(first_line) > 4:
                message = first_line[4:].strip()
            else:
                message = ""
                
        return cls(
            code=code,
            message=message,
            raw=raw_response,
            is_multiline=is_multiline,
            lines=lines
        )
        
    def is_success(self) -> bool:
        """
        判断响应是否表示成功
        
        Returns:
            True表示成功（2xx），False表示失败
        """
        return 200 <= self.code < 300
        
    def is_intermediate(self) -> bool:
        """
        判断是否需要进一步操作
        
        Returns:
            True表示需要进一步操作（3xx）
        """
        return 300 <= self.code < 400
        
    def is_temporary_failure(self) -> bool:
        """
        判断是否是临时失败
        
        Returns:
            True表示临时失败（4xx）
        """
        return 400 <= self.code < 500
        
    def is_permanent_failure(self) -> bool:
        """
        判断是否是永久失败
        
        Returns:
            True表示永久失败（5xx）
        """
        return 500 <= self.code < 600
        
    def get_status_message(self) -> str:
        """
        获取状态描述
        
        Returns:
            状态描述字符串
        """
        status_messages = {
            220: "服务就绪",
            221: "服务关闭",
            225: "数据连接打开",
            226: "数据传输完成",
            227: "进入被动模式",
            230: "用户登录成功",
            250: "操作成功",
            257: "路径创建成功",
            331: "需要密码",
            332: "需要账户",
            350: "等待文件操作",
            421: "服务不可用",
            425: "无法打开数据连接",
            426: "传输中止",
            500: "无效命令",
            503: "命令顺序错误",
            530: "未登录",
            550: "文件不可用",
            552: "存储空间不足",
            553: "文件名不允许"
        }
        
        return status_messages.get(self.code, f"响应码 {self.code}")


class ResponseParser:
    """响应解析器，提供响应验证和提取功能"""
    
    @staticmethod
    def validate_login_response(response: FTPResponse) -> bool:
        """
        验证登录响应
        
        Args:
            response: FTP响应对象
            
        Returns:
            True表示登录成功
        """
        return response.code == 230
        
    @staticmethod
    def validate_pasv_response(response: FTPResponse) -> bool:
        """
        验证PASV响应
        
        Args:
            response: FTP响应对象
            
        Returns:
            True表示PASV响应有效
        """
        return response.code == 227
        
    @staticmethod
    def extract_pasv_port(response: FTPResponse) -> Optional[int]:
        """
        从PASV响应中提取端口号
        
        Args:
            response: FTP响应对象
            
        Returns:
            端口号，解析失败返回None
        """
        if not ResponseParser.validate_pasv_response(response):
            return None
            
        import re
        pattern = r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)'
        match = re.search(pattern, response.raw)
        
        if match:
            p1 = int(match.group(5))
            p2 = int(match.group(6))
            return p1 * 256 + p2
            
        return None
        
    @staticmethod
    def extract_list_response(response: FTPResponse) -> List[str]:
        """
        从LIST响应中提取文件列表
        
        Args:
            response: FTP响应对象
            
        Returns:
            文件列表字符串
        """
        if response.code != 226 and response.code != 250:
            return []
            
        # LIST结果通常在响应消息中
        lines = response.raw.split('\r\n')
        
        # 过滤掉包含响应码的行
        result = []
        for line in lines:
            if line.strip() and not (line[:3].isdigit() and len(line) > 3 and line[3] in (' ', '-')):
                result.append(line.strip())
                
        return result
        
    @staticmethod
    def validate_type_response(response: FTPResponse) -> bool:
        """
        验证TYPE命令响应
        
        Args:
            response: FTP响应对象
            
        Returns:
            True表示设置成功
        """
        return response.code == 200
        
    @staticmethod
    def get_error_message(response: FTPResponse) -> str:
        """
        获取错误消息
        
        Args:
            response: FTP响应对象
            
        Returns:
            友好的错误消息
        """
        if response.is_permanent_failure():
            if response.code == 530:
                return "认证失败，请检查用户名和密码"
            elif response.code == 550:
                return "文件或目录不存在"
            elif response.code == 552:
                return "存储空间不足"
            elif response.code == 553:
                return "文件名无效"
            else:
                return f"操作失败: {response.message}"
        elif response.is_temporary_failure():
            return f"临时错误，请重试: {response.message}"
        else:
            return f"未知错误: {response.message}"