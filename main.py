import sys
import time
from PIL import Image, ImageGrab
import io
import requests
import base64
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget,
                             QHBoxLayout, QInputDialog, QTextEdit, QLineEdit, QSizePolicy, QMenu, QComboBox)
from PyQt5.QtCore import Qt, QRect, QThread, QObject, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QFont, QPainter, QPen, QPixmap, QColor, QPainterPath

from transformers import (
    AutoModelForCausalLM,
    AutoProcessor,
    GenerationConfig,
    BitsAndBytesConfig,
)

# KoboldCPP server settings
KOBOLDCPP_URL = "http://localhost:5001/api/v1/generate"

logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def resize_image(image, backend):
    if backend == "koboldcpp":
        MAX_PIXELS = 1_800_000
    else:
        MAX_PIXELS = 350_000 # for Transformers-model
    print(backend)
    print("MAX_PIXELS is set to:",(MAX_PIXELS))
    current_pixels = image.width * image.height
    if current_pixels <= MAX_PIXELS:
        return image
    scale_factor = (MAX_PIXELS / current_pixels) ** 0.5
    new_width = int(image.width * scale_factor)
    new_height = int(image.height * scale_factor)
    print("screenshot orginal size is",(image.height),"*",(image.width), "=", (image.height * image.width), "pixels")
    print("screenshot new size is",(new_height),"*",(new_width), "=", (new_height*new_width), "pixels")
    return image.resize((new_width, new_height), Image.LANCZOS)

def encode_image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def analyze_image_with_koboldcpp(image, prompt):
    image_base64 = encode_image_to_base64(image)
    
    payload = {
        "n": 1,
        "max_context_length": 8192,
        "max_length": 200,
        "temperature": 0.7,
        "top_p": 0.9,
        "images": [image_base64],
        "prompt": f"\n(Attached Image)\n<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
        "stop_sequence": ["<|eot_id|><|start_header_id|>user<|end_header_id|>", "<|eot_id|><|start_header_id|>assistant<|end_header_id|>"]
    }
    
    try:
        response = requests.post(KOBOLDCPP_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        return result['results'][0]['text'].strip()
    except requests.RequestException as e:
        print(f"Error communicating with KoboldCPP: {e}")
        return "Unable to analyze image at this time."

class TransformersModelWorker(QObject):
    model_loaded = pyqtSignal()
    analysis_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.model = None
        self.processor = None


    @pyqtSlot()
    def load_model(self):
        try:
            arguments = {"device_map": "auto", "torch_dtype": "auto", "trust_remote_code": True}
            self.processor = AutoProcessor.from_pretrained("allenai/Molmo-7B-O-0924", **arguments)
            
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="fp4",
                bnb_4bit_use_double_quant=True,
            )
            arguments["quantization_config"] = quantization_config
            
            self.model = AutoModelForCausalLM.from_pretrained("allenai/Molmo-7B-O-0924", **arguments)
            self.model_loaded.emit()

        except Exception as e:
            self.error_occurred.emit(f"Error loading model: {str(e)}")

    @pyqtSlot(object, str)
    def analyze_image(self, image, prompt):
        if self.model is None or self.processor is None:
            self.error_occurred.emit("Model not loaded. Please wait for the model to load and try again.")
            return

        try:
            inputs = self.processor.process(images=[image], text=prompt)
            inputs = {k: v.to(self.model.device).unsqueeze(0) for k, v in inputs.items()}
            
            output = self.model.generate_from_batch(
                inputs,
                GenerationConfig(max_new_tokens=200, stop_strings="<|endoftext|>"),
                tokenizer=self.processor.tokenizer,
            )
            
            generated_tokens = output[0, inputs["input_ids"].size(1):]
            generated_text = self.processor.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            self.analysis_complete.emit(generated_text)
        except Exception as e:
            self.error_occurred.emit(f"Error analyzing image: {str(e)}")

class ScreenshotWorker(QObject):
    screenshot_taken = pyqtSignal(object)
    take_screenshot_signal = pyqtSignal()

    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        self.take_screenshot_signal.connect(self.take_screenshot)

    @pyqtSlot()
    def take_screenshot(self):
        if self.overlay.capture_region:
            screenshot = ImageGrab.grab(bbox=(
                self.overlay.capture_region.left(),
                self.overlay.capture_region.top(),
                self.overlay.capture_region.right(),
                self.overlay.capture_region.bottom()
            ))
        else:
            screenshot = ImageGrab.grab()
        

        # resized_image = resize_image(screenshot)
        # Resize image based on backend
        resized_image = resize_image(screenshot, self.overlay.backend)

        self.screenshot_taken.emit(resized_image)

class TransparentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)

        painter.setOpacity(0.8)
        painter.fillPath(path, QColor(30, 30, 30))

        painter.setOpacity(1)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawPath(path)

class ChatOverlay(QMainWindow):
    analyze_image_signal = pyqtSignal(object, str)

    def __init__(self):
        super().__init__()
        self.initUI()
        self.capture_region = None
        self.current_image = None
        self.dragging = False
        self.selecting_region = False
        self.start_point = None
        self.end_point = None
        self.memory_enabled = False
        self.chat_history = []
        self.backend = "koboldcpp"
        self.model_loaded = False

        self.screenshot_thread = QThread()
        self.screenshot_worker = ScreenshotWorker(self)
        self.screenshot_worker.moveToThread(self.screenshot_thread)
        self.screenshot_worker.screenshot_taken.connect(self.process_screenshot)
        self.screenshot_thread.start()

        self.transformers_thread = QThread()
        self.transformers_worker = TransformersModelWorker()
        self.transformers_worker.moveToThread(self.transformers_thread)
        self.transformers_worker.model_loaded.connect(self.on_model_loaded)
        self.transformers_worker.analysis_complete.connect(self.on_analysis_complete)
        self.transformers_worker.error_occurred.connect(self.on_error)
        self.analyze_image_signal.connect(self.transformers_worker.analyze_image)
        self.analysis_in_progress = False
        self.transformers_thread.start()


    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(800, 600)

        self.central_widget = TransparentWidget(self)
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        # Add close button
        self.close_button = QPushButton("×", self)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.5);
            }
        """)
        self.close_button.setFixedSize(20, 20)
        self.close_button.clicked.connect(QApplication.quit)
        layout.addWidget(self.close_button, 0, Qt.AlignRight)

        self.chat_display = QTextEdit(self)
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: transparent; color: white; border: none;")
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); color: white; border: 1px solid gray; border-radius: 5px; padding: 2px;")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send", self)
        self.send_button.setStyleSheet("background-color: rgba(0, 122, 255, 0.7); color: white; border: none; border-radius: 5px; padding: 5px;")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        layout.addLayout(input_layout)

        button_layout = QHBoxLayout()
        select_region_button = QPushButton("Select Region", self)
        select_region_button.setStyleSheet("background-color: rgba(52, 199, 89, 0.7); color: white; border: none; border-radius: 5px; padding: 5px;")
        select_region_button.clicked.connect(self.select_region)
        button_layout.addWidget(select_region_button)

        resize_button = QPushButton("Resize Overlay", self)
        resize_button.setStyleSheet("background-color: rgba(255, 149, 0, 0.7); color: white; border: none; border-radius: 5px; padding: 5px;")
        resize_button.clicked.connect(self.resize_overlay)
        button_layout.addWidget(resize_button)

        layout.addLayout(button_layout)

        self.waiting_indicator = QLabel("", self)
        self.waiting_indicator.setStyleSheet("color: yellow; font-weight: bold;")
        layout.addWidget(self.waiting_indicator)

        # Add memory toggle button
        self.memory_toggle = QPushButton("Memory: Off", self)
        self.memory_toggle.setStyleSheet("background-color: rgba(255, 59, 48, 0.7); color: white; border: none; border-radius: 5px; padding: 5px;")
        self.memory_toggle.clicked.connect(self.toggle_memory)
        button_layout.addWidget(self.memory_toggle)

        # Add backend selection dropdown
        self.backend_selector = QComboBox(self)
        self.backend_selector.addItems(["KoboldCPP", "Transformers"])
        self.backend_selector.currentTextChanged.connect(self.change_backend)
        layout.addWidget(self.backend_selector)

        self.show()

    def toggle_memory(self):
        self.memory_enabled = not self.memory_enabled
        if self.memory_enabled:
            self.memory_toggle.setText("Memory: On")
            self.memory_toggle.setStyleSheet("background-color: rgba(52, 199, 89, 0.7); color: white; border: none; border-radius: 5px; padding: 5px;")
        else:
            self.memory_toggle.setText("Memory: Off")
            self.memory_toggle.setStyleSheet("background-color: rgba(255, 59, 48, 0.7); color: white; border: none; border-radius: 5px; padding: 5px;")
            self.chat_history.clear()
            
    def change_backend(self, backend):
        if backend == "KoboldCPP":
            self.backend = "koboldcpp"
        else:
            self.backend = "transformers"
            if not self.model_loaded:
                self.waiting_indicator.setText("Loading Transformers model...")
                QTimer.singleShot(100, self.transformers_worker.load_model)

    def send_message(self):
        if self.analysis_in_progress:
            return
        message = self.input_field.text()
        if message:
            self.chat_display.append(f"<span style='color: #58D68D;'>You:</span> {message}")
            self.input_field.clear()
            self.waiting_indicator.setText("Waiting for AI response...")
            self.analysis_in_progress = True
            self.send_button.setEnabled(False)
            self.send_button.setStyleSheet("background-color: rgba(0, 122, 255, 0.3); color: white; border: none; border-radius: 5px; padding: 5px;")
            
            if self.memory_enabled:
                self.chat_history.append(f"User: {message}")
                if len(self.chat_history) > 8:  # Keep only the last 4 pairs
                    self.chat_history = self.chat_history[-8:]
            
            self.take_screenshot()

    def take_screenshot(self):
        self.hide()
        QTimer.singleShot(50, self._take_and_process_screenshot)

    def _take_and_process_screenshot(self):
        self.screenshot_worker.take_screenshot_signal.emit()
        self.show()


    @pyqtSlot(object)
    def process_screenshot(self, image):
        self.current_image = image
        
        if self.memory_enabled:
            context = "\n".join(self.chat_history)
            prompt = context + "\n" + self.chat_display.toPlainText().split('\n')[-1]
        else:
            prompt = self.chat_display.toPlainText().split('\n')[-1]
        
        if self.backend == "koboldcpp":
            self.waiting_indicator.setText("Analyzing image with KoboldCPP...")
            QTimer.singleShot(100, lambda: self.process_koboldcpp(image, prompt))
        else:
            if not self.model_loaded:
                self.waiting_indicator.setText("Model not loaded. Please wait and try again.")
                self.analysis_in_progress = False
                self.send_button.setEnabled(True)
                self.send_button.setStyleSheet("background-color: rgba(0, 122, 255, 0.7); color: white; border: none; border-radius: 5px; padding: 5px;")
                return
            self.waiting_indicator.setText("Analyzing image with Transformers...")
            self.analyze_image_signal.emit(image, prompt)

    def process_koboldcpp(self, image, prompt):
        try:
            response = analyze_image_with_koboldcpp(image, prompt)
            self.on_analysis_complete(response)
        except Exception as e:
            self.on_error(f"Error analyzing image with KoboldCPP: {str(e)}")

    @pyqtSlot()
    def on_model_loaded(self):
        self.model_loaded = True
        self.waiting_indicator.setText("Transformers model loaded successfully.")
        QTimer.singleShot(3000, lambda: self.waiting_indicator.clear())

    @pyqtSlot(str)
    def on_error(self, error_message):
        self.waiting_indicator.setText(f"Error: {error_message}")
        self.chat_display.append(f"<span style='color: red;'>Error:</span> {error_message}")
        QTimer.singleShot(5000, lambda: self.waiting_indicator.clear())
        self.analysis_in_progress = False
        self.send_button.setEnabled(True)
        self.send_button.setStyleSheet("background-color: rgba(0, 122, 255, 0.7); color: white; border: none; border-radius: 5px; padding: 5px;")

    @pyqtSlot(str)
    def on_analysis_complete(self, response):
        self.chat_display.append(f"<span style='color: #5DADE2;'>AI:</span> {response}")
        
        if self.memory_enabled:
            self.chat_history.append(f"AI: {response}")
            if len(self.chat_history) > 8:  # Keep only the last 4 pairs
                self.chat_history = self.chat_history[-8:]
        
        self.waiting_indicator.clear()
        self.analysis_in_progress = False
        self.send_button.setEnabled(True)
        self.send_button.setStyleSheet("background-color: rgba(0, 122, 255, 0.7); color: white; border: none; border-radius: 5px; padding: 5px;")

   
        self.waiting_indicator.clear()

    def select_region(self):
        self.hide()
        screen = QApplication.primaryScreen()
        self.original_screenshot = screen.grabWindow(0)
        self.select_window = QMainWindow()
        self.select_window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.select_window.setGeometry(screen.geometry())
        self.select_window.setAttribute(Qt.WA_TranslucentBackground)
        self.select_window.show()
        self.select_window.setMouseTracking(True)
        self.select_window.mousePressEvent = self.region_select_press
        self.select_window.mouseMoveEvent = self.region_select_move
        self.select_window.mouseReleaseEvent = self.region_select_release
        self.select_window.paintEvent = self.region_select_paint
        self.selecting_region = True
        self.start_point = None
        self.end_point = None

    def region_select_press(self, event):
        if self.selecting_region:
            self.start_point = event.pos()
            self.end_point = None

    def region_select_move(self, event):
        if self.selecting_region and self.start_point:
            self.end_point = event.pos()
            self.select_window.update()

    def region_select_release(self, event):
        if self.selecting_region:
            self.end_point = event.pos()
            if self.start_point and self.end_point:
                self.capture_region = QRect(self.start_point, self.end_point).normalized()
            self.selecting_region = False
            self.select_window.close()
            self.show()

    def region_select_paint(self, event):
        painter = QPainter(self.select_window)
        painter.drawPixmap(self.select_window.rect(), self.original_screenshot)
        if self.start_point and self.end_point:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            painter.setBrush(QColor(255, 0, 0, 50))
            painter.drawRect(QRect(self.start_point, self.end_point).normalized())

    def resize_overlay(self):
        new_width, ok1 = QInputDialog.getInt(self, 'Resize Overlay', 'Enter new width:', self.width(), 100, 2000)
        if ok1:
            new_height, ok2 = QInputDialog.getInt(self, 'Resize Overlay', 'Enter new height:', self.height(), 100, 2000)
            if ok2:
                self.setFixedSize(new_width, new_height)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(self.mapToGlobal(event.pos() - self.offset))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        select_region_action = context_menu.addAction("Select Region")
        resize_overlay_action = context_menu.addAction("Resize Overlay")
        close_action = context_menu.addAction("Close App")

        action = context_menu.exec_(self.mapToGlobal(event.pos()))
        if action == select_region_action:
            self.select_region()
        elif action == resize_overlay_action:
            self.resize_overlay()
        elif action == close_action:
            QApplication.quit()


def main():
    app = QApplication(sys.argv)
    overlay = ChatOverlay()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
