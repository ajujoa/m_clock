import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLCDNumber, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QFont, QPainter, QColor, QPen
import ctypes
import configparser
import keyboard
import threading
import time
from PyQt5.QtWidgets import QMessageBox

class TimerSignals(QObject):
    update = pyqtSignal(int)
    
class OverlayTimer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.Window |  # 작업 표시줄에 표시하기 위해 Qt.Window 플래그 사용
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon("m_clock.ico"))
        self.signals = TimerSignals()
        self.signals.update.connect(self.updateDisplay)
        
        self.config = configparser.ConfigParser()
        self.ini_path = 'timer_config.ini'
        self.load_config()
        
        self.initUI()
        self.initTrayIcon()

    def initUI(self):
        # LCD 숫자 디스플레이 설정
        self.lcd = QLCDNumber(self)
        self.lcd.setDigitCount(8)
        self.lcd.setSegmentStyle(QLCDNumber.Flat)

        # 타이머 설정
        self.seconds = 0
        self.is_running = False
        self.timer_thread = None
        self.is_locked = False

        # 화면 크기 체크 타이머
        self.screen_check_timer = QTimer(self)
        self.screen_check_timer.timeout.connect(self.check_screen_size)
        self.screen_check_timer.start(1000)  # 1초마다 화면 크기 체크

        self.update_size_and_position()
        self.updateDisplay(self.seconds)

        # 전역 핫키 등록
        self.register_hotkeys()

        self.setWindowTitle("PoE Timer v0.1")  # 작업 표시줄에 표시될 제목 설정

    def initTrayIcon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("m_clock.png"))  # 아이콘 파일 경로 지정
        
        # 트레이 아이콘 메뉴 생성
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.close)  # self.close()를 호출하도록 변경
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def load_config(self):
        if os.path.exists(self.ini_path):
            self.config.read(self.ini_path)
        else:
            self.config['Position'] = {'x': '0.9', 'y': '0.05'}
            self.config['Size'] = {'width': '0.05', 'height': '0.025'}
            self.save_config()

    def save_config(self):
        with open(self.ini_path, 'w') as configfile:
            self.config.write(configfile)

    def register_hotkeys(self):
        keyboard.add_hotkey('F2', self.reset_timer_wrapper)
        keyboard.add_hotkey('F3', self.start_timer_wrapper)
        keyboard.add_hotkey('F4', self.toggle_timer_wrapper)
        keyboard.add_hotkey('F6', self.toggle_lock)
        keyboard.add_hotkey('F7', self.close)

    def reset_timer_wrapper(self):
        self.reset_timer()

    def start_timer_wrapper(self):
        self.start_timer()

    def toggle_timer_wrapper(self):
        self.toggle_timer()

    def updateDisplay(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        time = f"{h:02d}:{m:02d}:{s:02d}"
        self.lcd.display(time)
        self.update()  # 화면 갱신

    def timer_function(self):
        while self.is_running:
            time.sleep(1)
            self.seconds += 1
            self.signals.update.emit(self.seconds)

    def start_timer(self):
        if not self.is_running:
            self.is_running = True
            self.timer_thread = threading.Thread(target=self.timer_function)
            self.timer_thread.start()

    def toggle_timer(self):
        if self.is_running:
            self.is_running = False
            if self.timer_thread:
                self.timer_thread.join()
        else:
            self.start_timer()

    def reset_timer(self):
        self.is_running = False
        if self.timer_thread:
            self.timer_thread.join()
        self.seconds = 0
        self.signals.update.emit(self.seconds)

    def toggle_lock(self):
        self.is_locked = not self.is_locked
        if self.is_locked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowTransparentForInput)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowTransparentForInput)
        self.show()  # 윈도우 플래그 변경 후 다시 표시
        self.update()  # 화면 갱신

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 테두리 색상 설정
        if self.is_locked:
            border_color = QColor(255, 255, 255)  # 흰색
        else:
            border_color = QColor(255, 0, 0)  # 빨간색

        # 테두리 그리기
        pen = QPen(border_color)
        pen.setWidth(2)  # 테두리 두께 설정
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

        # LCD 색상 설정
        if self.is_running:
            lcd_color = "rgb(255, 255, 255)"  # 하얀색
        elif self.seconds > 0:
            lcd_color = "rgb(255, 165, 0)"  # 오렌지색
        else:
            lcd_color = "rgb(192, 192, 192)"  # 회색
        self.lcd.setStyleSheet(f"background-color: rgba(0, 0, 0, 100); color: {lcd_color};")

    def mousePressEvent(self, event):
        if not self.is_locked:
            if event.button() == Qt.LeftButton:
                self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if not self.is_locked:
            if event.buttons() == Qt.LeftButton:
                self.move(event.globalPos() - self.dragPosition)
                event.accept()

    def mouseReleaseEvent(self, event):
        if not self.is_locked:
            if event.button() == Qt.LeftButton:
                self.save_position()

    def update_size_and_position(self):
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)

        width_ratio = self.config.getfloat('Size', 'width', fallback=0.05)
        height_ratio = self.config.getfloat('Size', 'height', fallback=0.025)
        x_ratio = self.config.getfloat('Position', 'x', fallback=0.9)
        y_ratio = self.config.getfloat('Position', 'y', fallback=0.05)

        self.timer_width = int(self.screen_width * width_ratio)
        self.timer_height = int(self.screen_height * height_ratio)
        pos_x = int(self.screen_width * x_ratio)
        pos_y = int(self.screen_height * y_ratio)

        self.setGeometry(pos_x, pos_y, self.timer_width, self.timer_height)
        self.lcd.resize(self.timer_width, self.timer_height)

    def check_screen_size(self):
        user32 = ctypes.windll.user32
        new_width = user32.GetSystemMetrics(0)
        new_height = user32.GetSystemMetrics(1)
        if new_width != self.screen_width or new_height != self.screen_height:
            self.update_size_and_position()

    def save_position(self):
        x = self.x() / self.screen_width
        y = self.y() / self.screen_height
        self.config['Position'] = {'x': str(x), 'y': str(y)}
        self.save_config()

    # def closeEvent(self, event):
    #     # 타이머 중지
    #     self.is_running = False
    #     if self.timer_thread:
    #         self.timer_thread.join()
    #     # 핫키 해제
    #     keyboard.unhook_all()
    #     self.save_position()
    #     event.accept()
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Exit', 'Do you want to exit the application?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # 타이머 중지
            self.is_running = False
            if self.timer_thread:
                self.timer_thread.join()
            # 핫키 해제
            keyboard.unhook_all()
            self.save_position()
            event.accept()
            QApplication.instance().quit()
        else:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "PoE Timer",
                "Application was minimized to tray",
                QSystemTrayIcon.Information,
                2000
            )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = OverlayTimer()
    ex.show()
    sys.exit(app.exec_())
