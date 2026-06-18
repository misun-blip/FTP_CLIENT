"""
FTP客户端主模块
整合连接、认证、目录浏览、文件传输等功能
"""
import os
import threading
from typing import List, Optional, Callable
from pathlib import Path

from ftp_client.core.connection import FTPConnection
from ftp_client.core.response_parser import FTPResponse, ResponseParser, FTPResponseCode
from ftp_client.models.remote_file import RemoteFile
from ftp_client.models.transfer_task import TransferTask, TransferDirection, TransferStatus
from ftp_client.utils.exceptions import AuthenticationError, FTPException, TransferError
from ftp_client.utils.logger import get_logger


class FTPClient:
    """FTP客户端主类"""
    
    def __init__(self, timeout: int = 10):
        """
        初始化FTP客户端
        
        Args:
            timeout: 连接超时时间（秒）
        """
        self.connection = FTPConnection(timeout)
        self.logger = get_logger(__name__)
        self._current_directory = "/"
        self._transfer_callbacks: List[Callable] = []
        
    def connect(self, host: str, port: int = 21, timeout: int = 10) -> None:
        """
        连接到FTP服务器
        
        Args:
            host: 服务器地址
            port: 服务器端口
            timeout: 超时时间
            
        Raises:
            ConnectionError: 连接失败
        """
        self.logger.info(f"正在连接到 {host}:{port}")
        try:
            self.connection.timeout = timeout
            self.connection.connect(host, port)
            self.logger.info(f"成功连接到 {host}:{port}")
        except Exception as e:
            self.logger.error(f"连接失败: {str(e)}")
            raise
            
    def login(self, username: str, password: str) -> bool:
        """
        用户登录认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            True表示登录成功
            
        Raises:
            AuthenticationError: 认证失败
        """
        self.logger.info(f"正在登录用户: {username}")
        
        # 发送USER命令
        response_raw = self.connection.send_command(f"USER {username}")
        response = FTPResponse.parse(response_raw)
        
        if response.code == FTPResponseCode.SEND_PASSWORD:
            # 发送PASS命令
            response_raw = self.connection.send_command(f"PASS {password}")
            response = FTPResponse.parse(response_raw)
            
        if ResponseParser.validate_login_response(response):
            self.connection.is_logged_in = True
            self.logger.info(f"用户 {username} 登录成功")
            # 获取当前工作目录
            self._current_directory = self.pwd()
            return True
        else:
            error_msg = ResponseParser.get_error_message(response)
            self.logger.error(f"登录失败: {error_msg}")
            raise AuthenticationError(error_msg)
            
    def logout(self) -> None:
        """注销并关闭连接"""
        self.close()
        
    def close(self) -> None:
        """关闭FTP连接"""
        self.logger.info("正在关闭FTP连接")
        self.connection.close()
        self._current_directory = "/"
        
    def pwd(self) -> str:
        """
        获取当前工作目录
        
        Returns:
            当前目录路径
            
        Raises:
            FTPException: 命令执行失败
        """
        response_raw = self.connection.send_command("PWD")
        response = FTPResponse.parse(response_raw)
        
        if response.code == FTPResponseCode.PATHNAME_CREATED:
            # 提取路径，格式: "257 \"/path\" is current directory"
            import re
            match = re.search(r'"([^"]*)"', response.message)
            if match:
                current_dir = match.group(1)
                self._current_directory = current_dir
                return current_dir
                
        raise FTPException(f"获取当前目录失败: {response.message}")
        
    def cwd(self, path: str) -> bool:
        """
        改变当前工作目录
        
        Args:
            path: 目标目录路径
            
        Returns:
            True表示成功
            
        Raises:
            FTPException: 命令执行失败
        """
        self.logger.info(f"切换到目录: {path}")
        response_raw = self.connection.send_command(f"CWD {path}")
        response = FTPResponse.parse(response_raw)
        
        if response.code == FTPResponseCode.FILE_ACTION_OK:
            self._current_directory = path
            return True
        else:
            error_msg = ResponseParser.get_error_message(response)
            raise FTPException(f"切换目录失败: {error_msg}")
            
    def list_dir(self, path: Optional[str] = None) -> List[RemoteFile]:
        """
        列出目录内容
        
        Args:
            path: 目录路径，为None时列出当前目录
            
        Returns:
            RemoteFile对象列表
            
        Raises:
            FTPException: 命令执行失败
        """
        target_path = path if path else self._current_directory
        self.logger.info(f"列出目录: {target_path}")
        
        # 设置二进制传输模式（用于LIST）
        self._set_transfer_type('I')
        
        # 进入被动模式
        pasv_response = self._enter_pasv_mode()
        
        # 发送LIST命令
        list_cmd = f"LIST {target_path}" if target_path != self._current_directory else "LIST"
        self.connection.send_command(list_cmd)
        
        # 建立数据连接并接收数据
        self.connection.setup_data_connection(pasv_response.raw)
        data = self.connection.receive_data()
        self.connection.close_data_connection()
        
        # 接收完成响应
        final_response = self._receive_final_response()
        
        if final_response.code in (FTPResponseCode.DATA_CONNECTION_OPEN, 
                                    FTPResponseCode.CLOSING_DATA_CONNECTION,
                                    FTPResponseCode.FILE_ACTION_OK):
            # 解析目录列表
            return self._parse_list_output(data.decode('utf-8', errors='ignore'), target_path)
        else:
            raise FTPException(f"列出目录失败: {final_response.message}")
            
    def _parse_list_output(self, output: str, base_path: str) -> List[RemoteFile]:
        """
        解析LIST命令输出
        
        Args:
            output: LIST命令的输出文本
            base_path: 基础路径
            
        Returns:
            RemoteFile对象列表
        """
        files = []
        lines = output.strip().split('\r\n')
        
        for line in lines:
            if not line.strip():
                continue
                
            # 解析UNIX风格的ls -l输出
            # 格式: drwxr-xr-x 2 user group 4096 Jan 1 12:34 dirname
            parts = line.split(maxsplit=8)
            
            if len(parts) < 9:
                # 简单格式（仅文件名）
                name = line.strip()
                is_dir = False
                size = 0
                modified_time = ""
            else:
                permissions = parts[0]
                size = int(parts[4])
                # 日期时间部分
                month = parts[5]
                day = parts[6]
                time = parts[7]
                name = parts[8]
                is_dir = permissions.startswith('d')
                modified_time = f"{month} {day} {time}"
                
            # 构建完整路径
            if base_path == "/":
                full_path = f"/{name}" if name != ".." else "/.."
            else:
                full_path = f"{base_path}/{name}" if base_path != "/" else f"/{name}"
                
            remote_file = RemoteFile(
                name=name,
                path=full_path,
                size=size,
                is_dir=is_dir,
                modified_time=modified_time
            )
            files.append(remote_file)
            
        return files
        
    def download(self, remote_path: str, local_path: str) -> TransferTask:
        """
        下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地保存路径
            
        Returns:
            传输任务对象
        """
        self.logger.info(f"下载文件: {remote_path} -> {local_path}")
        
        # 获取文件大小
        file_size = self._get_file_size(remote_path)
        
        # 创建传输任务
        task = TransferTask(
            direction=TransferDirection.DOWNLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=file_size
        )
        
        # 开始下载
        try:
            self._do_download(remote_path, local_path, task)
            task.status = TransferStatus.COMPLETED
            self.logger.info(f"下载完成: {remote_path}")
        except Exception as e:
            task.status = TransferStatus.FAILED
            task.error_message = str(e)
            self.logger.error(f"下载失败: {str(e)}")
            raise
            
        return task
        
    def _do_download(self, remote_path: str, local_path: str, task: TransferTask) -> None:
        """
        执行下载操作
        
        Args:
            remote_path: 远程路径
            local_path: 本地路径
            task: 传输任务对象
        """
        # 设置二进制传输模式
        self._set_transfer_type('I')
        
        # 进入被动模式
        pasv_response = self._enter_pasv_mode()
        
        # 发送RETR命令
        self.connection.send_command(f"RETR {remote_path}")
        
        # 建立数据连接
        self.connection.setup_data_connection(pasv_response.raw)
        
        # 接收数据并写入文件
        # 确保本地目录存在
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        received_size = 0
        with open(local_path, 'wb') as f:
            while True:
                chunk = self.connection.data_socket.recv(8192)
                if not chunk:
                    break
                f.write(chunk)
                received_size += len(chunk)
                task.transferred_size = received_size
                
        self.connection.close_data_connection()
        
        # 接收完成响应
        final_response = self._receive_final_response()
        if final_response.code != FTPResponseCode.CLOSING_DATA_CONNECTION:
            raise TransferError(f"传输异常: {final_response.message}")
            
    def resume_download(self, remote_path: str, local_path: str) -> TransferTask:
        """
        断点续传下载
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径
            
        Returns:
            传输任务对象
        """
        self.logger.info(f"断点续传下载: {remote_path} -> {local_path}")
        
        # 检查本地文件是否存在
        local_file = Path(local_path)
        transferred_size = local_file.stat().st_size if local_file.exists() else 0
        
        # 获取远程文件大小
        file_size = self._get_file_size(remote_path)
        
        # 创建传输任务
        task = TransferTask(
            direction=TransferDirection.DOWNLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=file_size,
            transferred_size=transferred_size
        )
        
        # 如果已完成，直接返回
        if transferred_size >= file_size:
            task.status = TransferStatus.COMPLETED
            return task
            
        # 执行断点续传
        try:
            self._do_resume_download(remote_path, local_path, transferred_size, task)
            task.status = TransferStatus.COMPLETED
            self.logger.info(f"断点续传完成: {remote_path}")
        except Exception as e:
            task.status = TransferStatus.FAILED
            task.error_message = str(e)
            self.logger.error(f"断点续传失败: {str(e)}")
            raise
            
        return task
        
    def _do_resume_download(self, remote_path: str, local_path: str, 
                           resume_pos: int, task: TransferTask) -> None:
        """
        执行断点续传下载
        
        Args:
            remote_path: 远程路径
            local_path: 本地路径
            resume_pos: 续传起始位置
            task: 传输任务对象
        """
        # 设置二进制传输模式
        self._set_transfer_type('I')
        
        # 发送REST命令指定续传位置
        if resume_pos > 0:
            rest_response_raw = self.connection.send_command(f"REST {resume_pos}")
            rest_response = FTPResponse.parse(rest_response_raw)
            if rest_response.code != FTPResponseCode.FILE_ACTION_PENDING:
                raise TransferError(f"不支持断点续传: {rest_response.message}")
                
        # 进入被动模式
        pasv_response = self._enter_pasv_mode()
        
        # 发送RETR命令
        self.connection.send_command(f"RETR {remote_path}")
        
        # 建立数据连接
        self.connection.setup_data_connection(pasv_response.raw)
        
        # 以追加模式打开文件
        with open(local_path, 'ab') as f:
            received_size = resume_pos
            while received_size < task.total_size:
                chunk = self.connection.data_socket.recv(8192)
                if not chunk:
                    break
                f.write(chunk)
                received_size += len(chunk)
                task.transferred_size = received_size
                
        self.connection.close_data_connection()
        
        # 接收完成响应
        final_response = self._receive_final_response()
        if final_response.code != FTPResponseCode.CLOSING_DATA_CONNECTION:
            raise TransferError(f"传输异常: {final_response.message}")
            
    def upload(self, local_path: str, remote_path: str) -> TransferTask:
        """
        上传文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程保存路径
            
        Returns:
            传输任务对象
        """
        self.logger.info(f"上传文件: {local_path} -> {remote_path}")
        
        # 获取本地文件大小
        local_file = Path(local_path)
        if not local_file.exists():
            raise FileNotFoundError(f"本地文件不存在: {local_path}")
            
        file_size = local_file.stat().st_size
        
        # 创建传输任务
        task = TransferTask(
            direction=TransferDirection.UPLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=file_size
        )
        
        # 开始上传
        try:
            self._do_upload(local_path, remote_path, task)
            task.status = TransferStatus.COMPLETED
            self.logger.info(f"上传完成: {remote_path}")
        except Exception as e:
            task.status = TransferStatus.FAILED
            task.error_message = str(e)
            self.logger.error(f"上传失败: {str(e)}")
            raise
            
        return task
        
    def _do_upload(self, local_path: str, remote_path: str, task: TransferTask) -> None:
        """
        执行上传操作
        
        Args:
            local_path: 本地路径
            remote_path: 远程路径
            task: 传输任务对象
        """
        # 设置二进制传输模式
        self._set_transfer_type('I')
        
        # 进入被动模式
        pasv_response = self._enter_pasv_mode()
        
        # 发送STOR命令
        self.connection.send_command(f"STOR {remote_path}")
        
        # 建立数据连接
        self.connection.setup_data_connection(pasv_response.raw)
        
        # 读取文件并发送数据
        sent_size = 0
        with open(local_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                self.connection.send_data(chunk)
                sent_size += len(chunk)
                task.transferred_size = sent_size
                
        self.connection.close_data_connection()
        
        # 接收完成响应
        final_response = self._receive_final_response()
        if final_response.code != FTPResponseCode.CLOSING_DATA_CONNECTION:
            raise TransferError(f"传输异常: {final_response.message}")
            
    def resume_upload(self, local_path: str, remote_path: str) -> TransferTask:
        """
        断点续传上传
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程保存路径
            
        Returns:
            传输任务对象
        """
        self.logger.info(f"断点续传上传: {local_path} -> {remote_path}")
        
        # 检查本地文件
        local_file = Path(local_path)
        if not local_file.exists():
            raise FileNotFoundError(f"本地文件不存在: {local_path}")
            
        file_size = local_file.stat().st_size
        
        # 获取远程文件已上传大小
        uploaded_size = self._get_remote_file_size(remote_path)
        
        # 创建传输任务
        task = TransferTask(
            direction=TransferDirection.UPLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=file_size,
            transferred_size=uploaded_size
        )
        
        # 如果已完成，直接返回
        if uploaded_size >= file_size:
            task.status = TransferStatus.COMPLETED
            return task
            
        # 执行断点续传
        try:
            self._do_resume_upload(local_path, remote_path, uploaded_size, task)
            task.status = TransferStatus.COMPLETED
            self.logger.info(f"断点续传上传完成: {remote_path}")
        except Exception as e:
            task.status = TransferStatus.FAILED
            task.error_message = str(e)
            self.logger.error(f"断点续传上传失败: {str(e)}")
            raise
            
        return task
        
    def _do_resume_upload(self, local_path: str, remote_path: str,
                         resume_pos: int, task: TransferTask) -> None:
        """
        执行断点续传上传
        
        Args:
            local_path: 本地路径
            remote_path: 远程路径
            resume_pos: 续传起始位置
            task: 传输任务对象
        """
        # 设置二进制传输模式
        self._set_transfer_type('I')
        
        # 发送REST命令
        if resume_pos > 0:
            rest_response_raw = self.connection.send_command(f"REST {resume_pos}")
            rest_response = FTPResponse.parse(rest_response_raw)
            if rest_response.code != FTPResponseCode.FILE_ACTION_PENDING:
                raise TransferError(f"不支持断点续传: {rest_response.message}")
                
        # 进入被动模式
        pasv_response = self._enter_pasv_mode()
        
        # 发送STOR命令
        self.connection.send_command(f"STOR {remote_path}")
        
        # 建立数据连接
        self.connection.setup_data_connection(pasv_response.raw)
        
        # 从指定位置开始读取并发送
        with open(local_path, 'rb') as f:
            f.seek(resume_pos)
            sent_size = resume_pos
            while sent_size < task.total_size:
                chunk = f.read(8192)
                if not chunk:
                    break
                self.connection.send_data(chunk)
                sent_size += len(chunk)
                task.transferred_size = sent_size
                
        self.connection.close_data_connection()
        
        # 接收完成响应
        final_response = self._receive_final_response()
        if final_response.code != FTPResponseCode.CLOSING_DATA_CONNECTION:
            raise TransferError(f"传输异常: {final_response.message}")
            
    def _set_transfer_type(self, type_code: str) -> None:
        """
        设置传输类型
        
        Args:
            type_code: 'A' ASCII模式，'I' 二进制模式
        """
        response_raw = self.connection.send_command(f"TYPE {type_code}")
        response = FTPResponse.parse(response_raw)
        
        if not ResponseParser.validate_type_response(response):
            raise FTPException(f"设置传输类型失败: {response.message}")
            
    def _enter_pasv_mode(self) -> FTPResponse:
        """
        进入被动模式
        
        Returns:
            PASV命令的响应对象
        """
        response_raw = self.connection.send_command("PASV")
        response = FTPResponse.parse(response_raw)
        
        if not ResponseParser.validate_pasv_response(response):
            raise FTPException(f"进入被动模式失败: {response.message}")
            
        return response
        
    def _receive_final_response(self) -> FTPResponse:
        """
        接收传输完成后的最终响应
        
        Returns:
            最终响应对象
        """
        return self.connection._receive_response()
        
    def _get_file_size(self, remote_path: str) -> int:
        """
        获取远程文件大小
        
        Args:
            remote_path: 远程文件路径
            
        Returns:
            文件大小（字节）
        """
        response_raw = self.connection.send_command(f"SIZE {remote_path}")
        response = FTPResponse.parse(response_raw)
        
        if response.code == 213:
            try:
                return int(response.message.strip())
            except ValueError:
                return 0
        else:
            # 如果不支持SIZE命令，尝试从LIST解析
            return self._get_file_size_from_list(remote_path)
            
    def _get_file_size_from_list(self, remote_path: str) -> int:
        """
        通过LIST命令获取文件大小
        
        Args:
            remote_path: 远程文件路径
            
        Returns:
            文件大小
        """
        # 切换到文件所在目录
        parent_dir = str(Path(remote_path).parent)
        if parent_dir != ".":
            try:
                self.cwd(parent_dir)
            except:
                pass
                
        files = self.list_dir()
        file_name = Path(remote_path).name
        
        for file in files:
            if file.name == file_name:
                return file.size
                
        return 0
        
    def _get_remote_file_size(self, remote_path: str) -> int:
        """
        获取远程文件已上传的大小（用于断点续传）
        
        Args:
            remote_path: 远程文件路径
            
        Returns:
            文件大小，如果文件不存在返回0
        """
        try:
            response_raw = self.connection.send_command(f"SIZE {remote_path}")
            response = FTPResponse.parse(response_raw)
            
            if response.code == 213:
                return int(response.message.strip())
        except:
            pass
            
        return 0
        
    def register_callback(self, callback: Callable) -> None:
        """
        注册传输进度回调函数
        
        Args:
            callback: 回调函数，接收TransferTask参数
        """
        self._transfer_callbacks.append(callback)
        
    def _notify_callbacks(self, task: TransferTask) -> None:
        """
        通知所有回调函数
        
        Args:
            task: 传输任务对象
        """
        for callback in self._transfer_callbacks:
            try:
                callback(task)
            except Exception as e:
                self.logger.error(f"回调函数执行失败: {str(e)}")
                
    def abort_transfer(self) -> None:
        """中止当前传输"""
        self.connection.abort()
