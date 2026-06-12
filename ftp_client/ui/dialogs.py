from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class LoginDialog(QDialog):
    """独立的登录对话框，可在主窗口连接前弹出。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FTP 登录")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        # 主机
        layout.addWidget(QLabel("主机:"))
        self.host_edit = QLineEdit("127.0.0.1")
        layout.addWidget(self.host_edit)

        # 端口
        layout.addWidget(QLabel("端口:"))
        self.port_edit = QLineEdit("21")
        layout.addWidget(self.port_edit)

        # 用户名
        layout.addWidget(QLabel("用户名:"))
        self.user_edit = QLineEdit("anonymous")
        layout.addWidget(self.user_edit)

        # 密码
        layout.addWidget(QLabel("密码:"))
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_edit)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, int, str, str]:
        """返回 (host, port, username, password)。"""
        host = self.host_edit.text().strip()
        port = int(self.port_edit.text().strip())
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        return host, port, username, password
