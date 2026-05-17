"""
FTP连接管理模块
负责底层socket连接、命令发送和响应接收
"""
import socket
import ssl
from typing import Optional, Tuple
import threading


class FTPConnection:
    """FTP连接类，管理控制连接和数据连接"""
    
    def __init__(self, timeout: int = 10):
        """
        初始化FTP连接
        
        Args:
            timeout: 连接超时时间（秒）
        """
        self.control_socket: Optional[socket.socket] = None
        self.data_socket: Optional[socket.socket] = None
        self.timeout = timeout
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.is_connected = False
        self.is_logged_in = False
        self._lock = threading.Lock()
        
    def connect(self, host: str, port: int = 21) -> None:
        """
        建立FTP控制连接
        
        Args:
            host: FTP服务器地址
            port: FTP服务器端口，默认21
            
        Raises:
            ConnectionError: 连接失败时抛出
        """
        try:
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.settimeout(self.timeout)
            self.control_socket.connect((host, port))
            self.host = host
            self.port = port
            self.is_connected = True
            
            # 接收连接成功响应
            response = self._receive_response()
            if response.code != 220:
                raise ConnectionError(f"连接失败: {response.message}")
                
        except socket.timeout:
            raise ConnectionError(f"连接超时 ({self.timeout}秒)")
        except socket.error as e:
            raise ConnectionError(f"连接错误: {str(e)}")
            
    def send_command(self, command: str) -> str:
        """
        发送FTP命令
        
        Args:
            command: FTP命令字符串
            
        Returns:
            服务器响应字符串
        """
        with self._lock:
            if not self.control_socket:
                raise ConnectionError("未建立控制连接")
                
            # 发送命令
            command_bytes = (command + '\r\n').encode('utf-8')
            self.control_socket.send(command_bytes)
            
            # 接收响应
            response = self._receive_response()
            return response.raw
            
    def _receive_response(self) -> 'FTPResponse':
        """
        接收FTP服务器响应
        
        Returns:
            FTPResponse对象
        """
        from core.response_parser import FTPResponse
        
        response_data = []
        while True:
            try:
                line = self.control_socket.recv(4096).decode('utf-8', errors='ignore')
                if not line:
                    break
                    
                response_data.append(line)
                
                # 检查是否是多行响应的最后一行
                # FTP多行响应以 "xxx " 开始，以 "xxx " 结束
                if len(line) >= 4 and line[3] == ' ':
                    break
                # 单行响应以换行结束
                elif '\n' in line and len(response_data) > 0:
                    break
                    
            except socket.timeout:
                raise TimeoutError("接收响应超时")
                
        raw_response = ''.join(response_data)
        return FTPResponse.parse(raw_response)
        
    def setup_data_connection(self, pasv_response: str) -> None:
        """
        建立数据连接（被动模式）
        
        Args:
            pasv_response: PASV命令的响应，格式如 "227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)"
        """
        # 解析IP和端口
        ip, port = self._parse_pasv_response(pasv_response)
        
        # 创建数据连接
        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_socket.settimeout(self.timeout)
        self.data_socket.connect((ip, port))
        
    def _parse_pasv_response(self, response: str) -> Tuple[str, int]:
        """
        解析PASV响应，获取IP和端口
        
        Args:
            response: PASV命令的响应字符串
            
        Returns:
            (IP地址, 端口号)
        """
        # 查找括号内的数字
        start = response.find('(')
        end = response.find(')')
        
        if start == -1 or end == -1:
            raise ValueError(f"无效的PASV响应: {response}")
            
        numbers = response[start + 1:end].split(',')
        if len(numbers) != 6:
            raise ValueError(f"无效的PASV响应格式: {response}")
            
        # 计算IP地址
        ip = '.'.join(numbers[:4])
        
        # 计算端口: p1*256 + p2
        port = int(numbers[4]) * 256 + int(numbers[5])
        
        return ip, port
        
    def send_data(self, data: bytes) -> None:
        """
        通过数据连接发送数据
        
        Args:
            data: 要发送的字节数据
        """
        if not self.data_socket:
            raise ConnectionError("未建立数据连接")
            
        self.data_socket.sendall(data)
        
    def receive_data(self) -> bytes:
        """
        从数据连接接收数据
        
        Returns:
            接收到的字节数据
        """
        if not self.data_socket:
            raise ConnectionError("未建立数据连接")
            
        data = []
        while True:
            try:
                chunk = self.data_socket.recv(8192)
                if not chunk:
                    break
                data.append(chunk)
            except socket.timeout:
                break
                
        return b''.join(data)
        
    def close_data_connection(self) -> None:
        """关闭数据连接"""
        if self.data_socket:
            try:
                self.data_socket.close()
            except:
                pass
            self.data_socket = None
            
    def close(self) -> None:
        """关闭控制连接"""
        if self.control_socket:
            try:
                self.send_command('QUIT')
            except:
                pass
                
            try:
                self.control_socket.close()
            except:
                pass
                
        self.control_socket = None
        self.is_connected = False
        self.is_logged_in = False
        self.close_data_connection()
        
    def abort(self) -> None:
        """中止当前传输"""
        try:
            self.send_command('ABOR')
        except:
            pass
            
    def __enter__(self):
        """上下文管理器入口"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()