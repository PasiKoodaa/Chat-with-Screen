# Chat with Screen

Chat with Screen is a Python application that allows users to capture screenshots, analyze captured screenshots using AI vision models. It supports both KoboldCPP and Transformers backends for image analysis (the default Transformers-model is Molmo-7B-O-0924). Users can engage in a chat-like interaction based on the analysis. The application features a translucent overlay interface for easy interaction with the underlying desktop.




https://github.com/user-attachments/assets/0497795d-da1e-4eb5-9e44-462b2b9a8123





## Features

- Capture full screen or selected region screenshots
- Analyze screenshots using KoboldCPP server
- Chat-like interface for interaction with AI based on screen content
- Translucent overlay for seamless desktop integration
- Resizable overlay window
- Right-click context menu for quick actions
- Chat history memory option for contextual conversations

## Requirements

- Python 3.8+
- PyQt5
- Pillow
- requests
- KoboldCPP server (for gguf-models)
- transformers (for Transformers-models)
- torch (for Transformers-models)

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
   conda create -n chat-with-screen python==3.9
   ```

3. Activate the environment:
   ```
   conda activate chat-with-screen
   ```

4. Install the required packages:
   ```
   pip install -r requirements.txt

   ```
5. Install torch if you use Transformers-models
   ```
   https://pytorch.org/get-started/locally/
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
   - On Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
5. Install torch if you use Transformers-models
   ```
   https://pytorch.org/get-started/locally/
   ```
   
## Usage

1. Ensure that your KoboldCPP server is running and accessible at the URL specified in the `KOBOLDCPP_URL` variable in the script.

   ![365400175-c8781ff4-b7c5-47a4-b72e-84da4a5e3ea2](https://github.com/user-attachments/assets/cc67f01b-b45f-47ea-95ff-b52e68eda563)

2. Run the application:
   ```
   python main.py
   ```
3. Use the interface to capture screenshots, analyze them, and chat with the AI about the screen content.
4. Toggle the chat history memory on or off using the "Memory" button. When enabled, the AI will consider the last four question-answer pairs for context.
5. Right-click on the overlay to access additional options such as selecting a region or resizing the overlay.
6. Click the 'X' button in the top-right corner or use the right-click menu to close the application.


## Configuration

You can modify the `KOBOLDCPP_URL` variable in the script to point to your KoboldCPP server if it's running on a different address or port.

## Chat History Memory

The chat history memory feature allows the AI to maintain context across multiple interactions. When enabled:

- The last four question-answer pairs are stored in memory.
- These pairs are included in the context for new questions, allowing for more coherent and contextual conversations.
- You can toggle this feature on or off at any time using the "Memory" button in the interface.
- When disabled, the chat history is cleared, and each question is treated independently.

This feature is particularly useful for in-depth discussions or multi-step analyses of screen content.



