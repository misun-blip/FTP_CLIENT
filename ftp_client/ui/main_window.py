from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ftp_client.interfaces import (
    FTPClientProtocol,
    LoggerProtocol,
)
from ftp_client.models.transfer_task import TransferDirection, TransferStatus, TransferTask

if TYPE_CHECKING:
    from ftp_client.interfaces import DownloaderProtocol, UploaderProtocol


class ConnectWorker(QThread):
    """后台执行 FTP 连接与登录，避免阻塞 GUI。"""

    result = Signal(bool, str)

    def __init__(
        self,
        ftp: FTPClientProtocol,
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> None:
        super().__init__()
        self._ftp = ftp
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    def run(self) -> None:
        try:
            self._ftp.connect(self._host, self._port)
            ok = self._ftp.login(self._username, self._password)
            if ok:
                self.result.emit(True, "连接并登录成功")
            else:
                self.result.emit(False, "登录失败：用户名或密码错误")
        except Exception as exc:
            self.result.emit(False, f"连接失败：{exc}")


class ListDirWorker(QThread):
    """后台执行远端目录查询。"""

    result = Signal(list)

    def __init__(self, ftp: FTPClientProtocol, path: str | None = None) -> None:
        super().__init__()
        self._ftp = ftp
        self._path = path

    def run(self) -> None:
        try:
            files = self._ftp.list_dir(self._path)
            self.result.emit(files)
        except Exception:
            self.result.emit([])


class MainWindow(QMainWindow):
    """FTP 客户端主窗口。

    区域划分：
      - 左上：连接信息区
      - 左下：本地目录区
      - 右上：远程目录区
      - 右下：任务列表区
      - 底部：日志区
    """

    def __init__(
        self,
        ftp: FTPClientProtocol | None = None,
        downloader: DownloaderProtocol | None = None,
        uploader: UploaderProtocol | None = None,
        logger: LoggerProtocol | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("FTP 客户端")
        self.resize(1100, 700)

        self._ftp = ftp
        self._downloader = downloader
        self._uploader = uploader
        self._logger = logger

        self._connected = False

        self._build_ui()
        self._apply_styles()

    # ------------------------------------------------------------------
    # 整体布局
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        # ── 上部：左右分栏 ──
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：连接区 + 本地目录
        left_panel = QSplitter(Qt.Orientation.Vertical)
        left_panel.addWidget(self._create_connection_group())
        left_panel.addWidget(self._create_local_dir_group())
        left_panel.setSizes([140, 300])
        top_splitter.addWidget(left_panel)

        # 右侧：远程目录 + 任务区
        right_panel = QSplitter(Qt.Orientation.Vertical)
        right_panel.addWidget(self._create_remote_dir_group())
        right_panel.addWidget(self._create_task_group())
        right_panel.setSizes([220, 220])
        top_splitter.addWidget(right_panel)

        top_splitter.setSizes([400, 680])
        root_layout.addWidget(top_splitter, stretch=3)

        # ── 底部：日志区 ──
        root_layout.addWidget(self._create_log_group(), stretch=1)

    # ------------------------------------------------------------------
    # 1. 连接信息区
    # ------------------------------------------------------------------

    def _create_connection_group(self) -> QGroupBox:
        group = QGroupBox("连接信息")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        # 主机
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("主机:"))
        self._host_edit = QLineEdit("127.0.0.1")
        host_layout.addWidget(self._host_edit)
        layout.addLayout(host_layout)

        # 端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        self._port_edit = QLineEdit("21")
        self._port_edit.setMaximumWidth(80)
        port_layout.addWidget(self._port_edit)
        port_layout.addStretch()
        layout.addLayout(port_layout)

        # 用户名
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("用户:"))
        self._user_edit = QLineEdit("anonymous")
        user_layout.addWidget(self._user_edit)
        layout.addLayout(user_layout)

        # 密码
        pass_layout = QHBoxLayout()
        pass_layout.addWidget(QLabel("密码:"))
        self._pass_edit = QLineEdit()
        self._pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pass_layout.addWidget(self._pass_edit)
        layout.addLayout(pass_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        self._connect_btn = QPushButton("连接")
        self._connect_btn.clicked.connect(self._on_connect)
        btn_layout.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("断开")
        self._disconnect_btn.setEnabled(False)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        btn_layout.addWidget(self._disconnect_btn)
        layout.addLayout(btn_layout)

        return group

    # ------------------------------------------------------------------
    # 2. 本地目录区
    # ------------------------------------------------------------------

    def _create_local_dir_group(self) -> QGroupBox:
        group = QGroupBox("本地目录")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        # 路径
        path_layout = QHBoxLayout()
        self._local_path_edit = QLineEdit(os.getcwd())
        path_layout.addWidget(QLabel("路径:"))
        path_layout.addWidget(self._local_path_edit)
        path_layout.addWidget(QPushButton("浏览", clicked=self._browse_local))
        layout.addLayout(path_layout)

        # 文件列表
        self._local_list = QListWidget()
        self._local_list.setAlternatingRowColors(True)
        layout.addWidget(self._local_list)

        self._refresh_local_dir()
        return group

    # ------------------------------------------------------------------
    # 3. 远程目录区
    # ------------------------------------------------------------------

    def _create_remote_dir_group(self) -> QGroupBox:
        group = QGroupBox("远程目录")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        # 路径
        path_layout = QHBoxLayout()
        self._remote_path_edit = QLineEdit("/")
        path_layout.addWidget(QLabel("路径:"))
        path_layout.addWidget(self._remote_path_edit)

        self._remote_refresh_btn = QPushButton("刷新")
        self._remote_refresh_btn.clicked.connect(self._on_refresh_remote)
        path_layout.addWidget(self._remote_refresh_btn)
        layout.addLayout(path_layout)

        # 目录表
        self._remote_table = QTableWidget(0, 3)
        self._remote_table.setHorizontalHeaderLabels(["名称", "大小", "修改时间"])
        self._remote_table.horizontalHeader().setStretchLastSection(True)
        self._remote_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._remote_table.setAlternatingRowColors(True)
        self._remote_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._remote_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._remote_table.doubleClicked.connect(self._on_remote_double_click)
        layout.addWidget(self._remote_table)

        return group

    # ------------------------------------------------------------------
    # 4. 任务列表区
    # ------------------------------------------------------------------

    def _create_task_group(self) -> QGroupBox:
        group = QGroupBox("传输任务")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        self._task_table = QTableWidget(0, 4)
        self._task_table.setHorizontalHeaderLabels(["文件", "方向", "进度", "状态"])
        self._task_table.horizontalHeader().setStretchLastSection(True)
        self._task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._task_table.setAlternatingRowColors(True)
        self._task_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._task_table)

        return group

    # ------------------------------------------------------------------
    # 5. 日志区
    # ------------------------------------------------------------------

    def _create_log_group(self) -> QGroupBox:
        group = QGroupBox("日志")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.document().setMaximumBlockCount(500)
        layout.addWidget(self._log_text)

        return group

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------

    def _on_connect(self) -> None:
        if self._ftp is None:
            self._append_log("[ERROR] FTP 服务未注入")
            return

        host = self._host_edit.text().strip()
        port = int(self._port_edit.text().strip())
        username = self._user_edit.text().strip()
        password = self._pass_edit.text()

        self._connect_btn.setEnabled(False)
        self._append_log(f"正在连接 {host}:{port} ...")

        self._connect_worker = ConnectWorker(self._ftp, host, port, username, password)
        self._connect_worker.result.connect(self._on_connect_result)
        self._connect_worker.start()

    def _on_connect_result(self, success: bool, message: str) -> None:
        self._connect_btn.setEnabled(not success)
        self._disconnect_btn.setEnabled(success)
        self._connected = success
        self._append_log(f"{'[INFO]' if success else '[ERROR]'} {message}")

        if success:
            self._on_refresh_remote()

    def _on_disconnect(self) -> None:
        if self._ftp is not None:
            try:
                self._ftp.close()
            except Exception:
                pass
        self._connected = False
        self._connect_btn.setEnabled(True)
        self._disconnect_btn.setEnabled(False)
        self._remote_table.setRowCount(0)
        self._append_log("[INFO] 已断开连接")

    def _on_refresh_remote(self) -> None:
        if self._ftp is None or not self._connected:
            return
        path = self._remote_path_edit.text().strip()
        self._append_log(f"正在获取远程目录 {path} ...")
        self._list_worker = ListDirWorker(self._ftp, path)
        self._list_worker.result.connect(self._on_list_dir_result)
        self._list_worker.start()

    def _on_list_dir_result(self, files: list) -> None:
        self._remote_table.setRowCount(0)
        for f in files:
            row = self._remote_table.rowCount()
            self._remote_table.insertRow(row)
            self._remote_table.setItem(row, 0, QTableWidgetItem(f.name))
            size_text = "" if f.is_dir else self._format_size(f.size)
            self._remote_table.setItem(row, 1, QTableWidgetItem(size_text))
            self._remote_table.setItem(row, 2, QTableWidgetItem(f.modified_time or ""))
        self._append_log(f"获取到 {len(files)} 个条目")

    def _on_remote_double_click(self, index) -> None:
        """双击远程目录表：若为目录则进入，若为文件则触发下载。"""
        name_item = self._remote_table.item(index.row(), 0)
        if name_item is None:
            return
        name = name_item.text()
        size_item = self._remote_table.item(index.row(), 1)
        is_dir = (size_item is not None and size_item.text() == "")

        if is_dir:
            self._enter_remote_dir(name)
        else:
            self._start_download(name)

    def _enter_remote_dir(self, name: str) -> None:
        current = self._remote_path_edit.text().strip()
        if not current.endswith("/"):
            current += "/"
        self._remote_path_edit.setText(current + name)
        self._on_refresh_remote()

    def _start_download(self, name: str) -> None:
        if self._downloader is None:
            self._append_log("[ERROR] 下载模块未注入")
            return
        remote = self._remote_path_edit.text().strip()
        if not remote.endswith("/"):
            remote += "/"
        remote += name
        local = os.path.join(self._local_path_edit.text().strip(), name)
        try:
            task = self._downloader.download(remote, local)
            self._append_log(f"[INFO] 开始下载: {name}")
            self._add_task_row(task)
        except Exception as exc:
            self._append_log(f"[ERROR] 下载失败: {exc}")

    # ------------------------------------------------------------------
    # 本地浏览
    # ------------------------------------------------------------------

    def _browse_local(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path = QFileDialog.getExistingDirectory(self, "选择本地目录", self._local_path_edit.text())
        if path:
            self._local_path_edit.setText(path)
            self._refresh_local_dir()

    def _refresh_local_dir(self) -> None:
        self._local_list.clear()
        path = self._local_path_edit.text().strip()
        if not os.path.isdir(path):
            return
        try:
            entries = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            for name in entries:
                full = os.path.join(path, name)
                icon = "📁 " if os.path.isdir(full) else "📄 "
                item = QListWidgetItem(icon + name)
                self._local_list.addItem(item)
        except OSError as exc:
            self._append_log(f"[ERROR] 读取本地目录失败: {exc}")

    # ------------------------------------------------------------------
    # 任务列表
    # ------------------------------------------------------------------

    def _add_task_row(self, task: TransferTask) -> None:
        row = self._task_table.rowCount()
        self._task_table.insertRow(row)

        fname = os.path.basename(task.remote_path)
        self._task_table.setItem(row, 0, QTableWidgetItem(fname))

        direction = "上传" if task.direction == TransferDirection.UPLOAD else "下载"
        self._task_table.setItem(row, 1, QTableWidgetItem(direction))

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(task.progress * 100))
        self._task_table.setCellWidget(row, 2, progress)

        self._task_table.setItem(row, 3, QTableWidgetItem(task.status.value))

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------

    def _append_log(self, message: str) -> None:
        self._log_text.append(message)

    # ------------------------------------------------------------------
    # 样式
    # ------------------------------------------------------------------

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                padding: 4px 12px;
            }
            QTableWidget, QListWidget, QTextEdit {
                border: 1px solid #ddd;
                border-radius: 2px;
            }
        """)

    # ------------------------------------------------------------------
    # 公开入口
    # ------------------------------------------------------------------

    def show(self) -> None:
        """启动并显示主窗口。"""
        super().show()

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.2f} GB"
