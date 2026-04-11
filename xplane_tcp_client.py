"""
X-Plane TCP Client - Receives data from X-Plane native plugin
"""

import json
import socket
import logging
import threading
from typing import Callable, Optional, Dict, Any
from PySide6.QtCore import QObject, Signal, QThread

logger = logging.getLogger('ISFP-Connect.XPlaneTCP')


class XPlaneTCPClient(QObject):
    """TCP client to receive data from X-Plane native plugin"""
    
    # Signals
    connected = Signal()
    disconnected = Signal()
    flight_data_received = Signal(dict)  # Flight data from X-Plane
    error_occurred = Signal(str)
    
    def __init__(self, host='127.0.0.1', port=51001, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.connected_flag = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
    def connect_to_xplane(self) -> bool:
        """Connect to X-Plane plugin"""
        import time
        
        # Try to connect multiple times
        for attempt in range(3):
            try:
                logger.info(f"Connecting to X-Plane plugin at {self.host}:{self.port} (attempt {attempt + 1}/3)")
                
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(3.0)
                self.socket.connect((self.host, self.port))
                self.socket.settimeout(None)  # Non-blocking after connection
                
                self.running = True
                self.connected_flag = True
                
                # Start receive thread
                self.thread = threading.Thread(target=self._receive_loop, daemon=True)
                self.thread.start()
                
                self.connected.emit()
                logger.info(f"Connected to X-Plane plugin at {self.host}:{self.port}")
                return True
                
            except ConnectionRefusedError as e:
                logger.warning(f"Connection refused (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    time.sleep(1.0)  # Wait before retry
                else:
                    logger.error("Failed to connect after 3 attempts. Is X-Plane running with ISFP Connect plugin enabled?")
                    self.error_occurred.emit("Connection refused. Please check:\n1. X-Plane is running\n2. ISFP Connect plugin is enabled in Plugins menu\n3. Plugin is installed in correct location")
                    return False
            except Exception as e:
                logger.error(f"Failed to connect to X-Plane: {e}")
                self.error_occurred.emit(str(e))
                return False
    
    def disconnect(self):
        """Disconnect from X-Plane"""
        self.running = False
        self.connected_flag = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.disconnected.emit()
        logger.info("Disconnected from X-Plane")
    
    def is_connected(self) -> bool:
        """Check if connected to X-Plane"""
        return self.connected_flag and self.socket is not None
    
    def get_simulator_version(self) -> int:
        """Get X-Plane simulator version (11 or 12) - 从插件管理器获取"""
        try:
            from xplane_plugin_manager import get_plugin_manager
            import __main__
            # 尝试从主窗口获取 settings
            if hasattr(__main__, 'app') and hasattr(__main__.app, 'settings'):
                manager = get_plugin_manager(__main__.app.settings)
                return manager.get_version()
        except Exception as e:
            logger.debug(f"无法从插件管理器获取版本: {e}")
        
        # 备用：自动检测
        import os
        possible_paths = [
            os.path.expandvars(r"%USERPROFILE%\Desktop\X-Plane 12"),
            os.path.expandvars(r"%USERPROFILE%\Desktop\X-Plane 11"),
            r"C:\X-Plane 12",
            r"C:\X-Plane 11",
            r"D:\X-Plane 12",
            r"D:\X-Plane 11",
            r"E:\X-Plane 12",
            r"E:\X-Plane 11",
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.path.exists(os.path.join(path, 'X-Plane.exe')):
                path_lower = path.lower()
                if 'x-plane 11' in path_lower or 'xplane 11' in path_lower:
                    return 11
                elif 'x-plane 12' in path_lower or 'xplane 12' in path_lower:
                    return 12
        
        return 12
    
    def _receive_loop(self):
        """Main receive loop running in separate thread"""
        buffer = ""
        
        while self.running:
            try:
                if not self.socket:
                    break
                    
                data = self.socket.recv(4096)
                if not data:
                    # Connection closed
                    logger.warning("X-Plane connection closed")
                    break
                
                buffer += data.decode('utf-8')
                
                # Process complete JSON messages
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                        self._process_message(line)
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Receive error: {e}")
                    self.error_occurred.emit(str(e))
                break
        
        # Connection lost
        self.connected_flag = False
        self.disconnected.emit()
    
    def _process_message(self, message: str):
        """Process received message"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')
            
            if msg_type == 'flight_data':
                # Convert COM frequencies from X-Plane format (e.g., 118350) to standard format (e.g., 118.350)
                if 'com1_freq' in data and data['com1_freq']:
                    # X-Plane stores frequency as integer in Hz/100, e.g., 118350 for 118.350 MHz
                    data['com1_freq_mhz'] = data['com1_freq'] / 1000.0
                if 'com2_freq' in data and data['com2_freq']:
                    data['com2_freq_mhz'] = data['com2_freq'] / 1000.0
                self.flight_data_received.emit(data)
            elif msg_type == 'connected':
                version = data.get('version', 0)
                logger.info(f"X-Plane plugin version: {version}")
            else:
                logger.debug(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")


# Global instance
_xplane_tcp_client: Optional[XPlaneTCPClient] = None


def get_xplane_tcp_client(host='127.0.0.1', port=51001) -> XPlaneTCPClient:
    """Get or create X-Plane TCP client singleton"""
    global _xplane_tcp_client
    if _xplane_tcp_client is None:
        _xplane_tcp_client = XPlaneTCPClient(host, port)
    return _xplane_tcp_client
