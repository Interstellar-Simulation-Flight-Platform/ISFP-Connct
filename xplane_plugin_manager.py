"""
X-Plane Plugin Manager - 管理 X-Plane 插件的安装、卸载和检测
"""

import os
import shutil
import logging
from typing import Optional, Tuple
from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtWidgets import QFileDialog, QMessageBox

logger = logging.getLogger('ISFP-Connect.XPlanePlugin')


class XPlanePluginManager(QObject):
    """X-Plane 插件管理器 - 处理路径选择、版本检测、插件安装/卸载"""
    
    # 信号
    path_changed = Signal(str)  # X-Plane 路径改变
    plugin_installed = Signal(bool, str)  # 安装结果 (成功/失败, 消息)
    plugin_uninstalled = Signal(bool, str)  # 卸载结果 (成功/失败, 消息)
    version_detected = Signal(int)  # 检测到版本 (11 或 12)
    
    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._xplane_path: Optional[str] = None
        self._version: int = 12  # 默认版本
        self._load_saved_path()
    
    def _load_saved_path(self):
        """加载保存的 X-Plane 路径"""
        saved_path = self.settings.value("xplane/path", "")
        if saved_path and os.path.exists(saved_path):
            self._xplane_path = saved_path
            self._version = self._detect_version_from_path(saved_path)
            logger.info(f"加载保存的 X-Plane 路径: {saved_path}, 版本: {self._version}")
    
    def get_xplane_path(self) -> Optional[str]:
        """获取当前 X-Plane 路径"""
        return self._xplane_path
    
    def get_version(self) -> int:
        """获取检测到的 X-Plane 版本 (11 或 12)"""
        return self._version
    
    def select_xplane_path(self, parent_widget=None) -> Optional[str]:
        """让用户选择 X-Plane 安装路径"""
        dialog = QFileDialog(parent_widget)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setWindowTitle("选择 X-Plane 安装目录")
        
        # 设置默认路径
        if self._xplane_path and os.path.exists(self._xplane_path):
            dialog.setDirectory(self._xplane_path)
        else:
            # 尝试常见路径
            for path in self._get_common_paths():
                if os.path.exists(path):
                    dialog.setDirectory(os.path.dirname(path))
                    break
        
        if dialog.exec():
            selected_path = dialog.selectedFiles()[0]
            if self._is_valid_xplane_path(selected_path):
                self.set_xplane_path(selected_path)
                return selected_path
            else:
                if parent_widget:
                    QMessageBox.warning(
                        parent_widget,
                        "无效路径",
                        f"选择的目录不是有效的 X-Plane 安装目录。\n\n"
                        f"请确保目录包含 X-Plane.exe 和 Resources 文件夹。"
                    )
        return None
    
    def set_xplane_path(self, path: str):
        """设置 X-Plane 路径"""
        if not self._is_valid_xplane_path(path):
            logger.warning(f"设置的 X-Plane 路径无效: {path}")
            return
        
        self._xplane_path = path
        self._version = self._detect_version_from_path(path)
        self.settings.setValue("xplane/path", path)
        self.settings.setValue("xplane/version", self._version)
        
        logger.info(f"设置 X-Plane 路径: {path}, 版本: {self._version}")
        self.path_changed.emit(path)
        self.version_detected.emit(self._version)
    
    def auto_detect_path(self) -> Optional[str]:
        """自动检测 X-Plane 安装路径"""
        for path in self._get_common_paths():
            if self._is_valid_xplane_path(path):
                self.set_xplane_path(path)
                return path
        return None
    
    def _get_common_paths(self) -> list:
        """获取常见的 X-Plane 安装路径"""
        return [
            os.path.expandvars(r"%USERPROFILE%\Desktop\X-Plane 12"),
            os.path.expandvars(r"%USERPROFILE%\Desktop\X-Plane 11"),
            r"C:\X-Plane 12",
            r"C:\X-Plane 11",
            r"D:\X-Plane 12",
            r"D:\X-Plane 11",
            r"E:\X-Plane 12",
            r"E:\X-Plane 11",
            r"F:\X-Plane 12",
            r"F:\X-Plane 11",
        ]
    
    def _is_valid_xplane_path(self, path: str) -> bool:
        """检查路径是否是有效的 X-Plane 安装目录"""
        if not path or not os.path.exists(path):
            return False
        # 检查关键文件/目录是否存在
        required_items = ['X-Plane.exe', 'Resources']
        for item in required_items:
            if not os.path.exists(os.path.join(path, item)):
                return False
        return True
    
    def _detect_version_from_path(self, path: str) -> int:
        """从路径检测 X-Plane 版本 (11 或 12)"""
        path_lower = path.lower()
        if 'x-plane 11' in path_lower or 'xplane 11' in path_lower:
            return 11
        elif 'x-plane 12' in path_lower or 'xplane 12' in path_lower:
            return 12
        # 默认返回 12
        return 12
    
    def get_plugin_path(self) -> Optional[str]:
        """获取 ISFP Connect 插件路径"""
        if not self._xplane_path:
            return None
        plugin_path = os.path.join(
            self._xplane_path, 
            'Resources', 'plugins', 'ISFPConnect'
        )
        return plugin_path
    
    def is_plugin_installed(self) -> bool:
        """检查插件是否已安装"""
        plugin_path = self.get_plugin_path()
        if not plugin_path:
            return False
        
        # 检查关键文件
        required_files = ['ISFPConnect.xpl', 'ISFPConnect.dll']
        for file in required_files:
            if os.path.exists(os.path.join(plugin_path, file)):
                return True
        
        # 检查 64 位插件
        win64_path = os.path.join(plugin_path, 'win_x64')
        if os.path.exists(win64_path):
            for file in required_files:
                if os.path.exists(os.path.join(win64_path, file)):
                    return True
        
        return False
    
    def get_plugin_status(self) -> dict:
        """获取插件状态信息"""
        status = {
            'installed': False,
            'path': None,
            'version': None,
            'xplane_version': self._version,
            'xplane_path': self._xplane_path
        }
        
        plugin_path = self.get_plugin_path()
        if plugin_path:
            status['path'] = plugin_path
            status['installed'] = self.is_plugin_installed()
        
        return status
    
    def install_plugin(self, parent_widget=None) -> Tuple[bool, str]:
        """安装插件到 X-Plane"""
        if not self._xplane_path:
            msg = "未设置 X-Plane 路径，请先选择 X-Plane 安装目录"
            self.plugin_installed.emit(False, msg)
            return False, msg
        
        plugin_path = self.get_plugin_path()
        
        try:
            # 创建插件目录
            os.makedirs(plugin_path, exist_ok=True)
            
            # 获取源插件文件路径（假设插件文件在应用目录的 plugins 文件夹中）
            app_dir = os.path.dirname(os.path.abspath(__file__))
            source_plugin_dir = os.path.join(app_dir, 'plugins', f'xplane{self._version}')
            
            # 如果没有版本特定目录，尝试通用目录
            if not os.path.exists(source_plugin_dir):
                source_plugin_dir = os.path.join(app_dir, 'plugins', 'xplane')
            
            if not os.path.exists(source_plugin_dir):
                msg = f"找不到插件文件，请确保插件文件位于: {source_plugin_dir}"
                self.plugin_installed.emit(False, msg)
                return False, msg
            
            # 复制插件文件
            copied_files = []
            for item in os.listdir(source_plugin_dir):
                source = os.path.join(source_plugin_dir, item)
                dest = os.path.join(plugin_path, item)
                
                if os.path.isdir(source):
                    if os.path.exists(dest):
                        shutil.rmtree(dest)
                    shutil.copytree(source, dest)
                else:
                    shutil.copy2(source, dest)
                copied_files.append(item)
            
            # 保存安装状态到配置
            self.settings.setValue("xplane/plugin_installed", True)
            self.settings.setValue("xplane/plugin_path", plugin_path)
            
            msg = f"插件安装成功！已复制 {len(copied_files)} 个文件到:\n{plugin_path}"
            logger.info(msg)
            self.plugin_installed.emit(True, msg)
            return True, msg
            
        except Exception as e:
            msg = f"插件安装失败: {str(e)}"
            logger.error(msg)
            self.plugin_installed.emit(False, msg)
            return False, msg
    
    def uninstall_plugin(self, parent_widget=None) -> Tuple[bool, str]:
        """从 X-Plane 卸载插件"""
        if not self._xplane_path:
            msg = "未设置 X-Plane 路径"
            self.plugin_uninstalled.emit(False, msg)
            return False, msg
        
        plugin_path = self.get_plugin_path()
        
        if not os.path.exists(plugin_path):
            msg = "插件目录不存在，可能已被卸载"
            self.settings.setValue("xplane/plugin_installed", False)
            self.plugin_uninstalled.emit(True, msg)
            return True, msg
        
        # 确认对话框
        if parent_widget:
            reply = QMessageBox.question(
                parent_widget,
                "确认卸载",
                f"确定要卸载 ISFP Connect 插件吗？\n\n"
                f"插件目录: {plugin_path}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return False, "用户取消卸载"
        
        try:
            # 删除插件目录
            shutil.rmtree(plugin_path)
            
            # 更新配置
            self.settings.setValue("xplane/plugin_installed", False)
            self.settings.remove("xplane/plugin_path")
            
            msg = f"插件已成功卸载"
            logger.info(msg)
            self.plugin_uninstalled.emit(True, msg)
            return True, msg
            
        except Exception as e:
            msg = f"插件卸载失败: {str(e)}"
            logger.error(msg)
            self.plugin_uninstalled.emit(False, msg)
            return False, msg
    
    def check_and_update_status(self) -> dict:
        """检查并更新插件状态，保存到配置"""
        status = self.get_plugin_status()
        self.settings.setValue("xplane/plugin_installed", status['installed'])
        self.settings.setValue("xplane/last_check", 
                              __import__('datetime').datetime.now().isoformat())
        return status


# 全局实例
_plugin_manager: Optional[XPlanePluginManager] = None


def get_plugin_manager(settings: QSettings = None, parent=None) -> XPlanePluginManager:
    """获取或创建插件管理器单例"""
    global _plugin_manager
    if _plugin_manager is None:
        if settings is None:
            raise ValueError("首次创建 PluginManager 需要提供 settings 参数")
        _plugin_manager = XPlanePluginManager(settings, parent)
    return _plugin_manager
