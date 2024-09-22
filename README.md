# Chat with Screen

Chat with Screen is a Python application that allows users to capture screenshots, analyze them using a KoboldCPP server, and engage in a chat-like interaction based on the analysis. The application features a translucent overlay interface for easy interaction with the underlying desktop. Currently only Windows compatible.



https://github.com/user-attachments/assets/f1f456e2-94f7-4e64-bc79-30235a99d99a



## Features

- Capture full screen or selected region screenshots
- Analyze screenshots using KoboldCPP server
- Chat-like interface for interaction with AI based on screen content
- Translucent overlay for seamless desktop integration
- Resizable overlay window
- Right-click context menu for quick actions

## Requirements

- Python 3.8+
- PyQt5
- Pillow
- requests
- KoboldCPP server (running separately)

## Installation

You can install Chat with Screen using either conda or pip. Choose the method that best suits your environment.

### Using conda

1. Clone the repository:
   ```
   git clone https://github.com/PasiKoodaa/Chat-with-Screen
   cd chat-with-screen
   ```

2. Create a new conda environment:
   ```
   conda create -n chat-with-screen python=3.9
   ```

3. Activate the environment:
   ```
   conda activate chat-with-screen
   ```

4. Install the required packages:
   ```
   pip install -r requirements.txt

   ```

### Using pip

1. Clone the repository:
   ```
   git clone https://github.com/PasiKoodaa/Chat-with-Screen
   cd chat-with-screen
   ```

2. Create a new virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```


4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Ensure that your KoboldCPP server is running and accessible at the URL specified in the `KOBOLDCPP_URL` variable in the script.

   ![365400175-c8781ff4-b7c5-47a4-b72e-84da4a5e3ea2](https://github.com/user-attachments/assets/cc67f01b-b45f-47ea-95ff-b52e68eda563)


3. Run the application:
   ```
   python main.py
   ```

4. Use the interface to capture screenshots, analyze them, and chat with the AI about the screen content.

5. Right-click on the overlay to access additional options such as selecting a region or resizing the overlay.

6. Click the 'X' button in the top-right corner or use the right-click menu to close the application.

## Configuration

You can modify the `KOBOLDCPP_URL` variable in the script to point to your KoboldCPP server if it's running on a different address or port.



