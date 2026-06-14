# FTP 客户端

基于原生 `socket` 的 Windows 图形化 FTP 客户端项目。

## 当前状态

当前仓库已完成项目骨架、公共数据模型和主程序装配入口，便于后续成员分别接入：

- FTP 协议层
- 上传模块
- 下载模块
- GUI 模块
- 日志、配置与测试模块

## 目录结构

```text
ftp_client/
├─ app.py
├─ core/
├─ models/
├─ transfer/
├─ ui/
└─ utils/
```

## 启动方式
```bash
pip install -r requirements.txt  #安装算需要的依赖和环境
```


```bash
python main.py #启动ftp client需要输入远程连接的ftp服务器的地址
python main.py --mock # 模拟启动ftp client如果发现ftp 服务器没用启动就模拟连接，便于测试download功能（双击下载）

```

在 GUI 模块接入前，程序会输出当前装配状态，作为工程骨架的最小可运行验证。

