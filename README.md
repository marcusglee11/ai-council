# AI Council

A Python tool for consulting a "council" of different Large Language Models (LLMs) to get diverse, synthesized advice on complex topics. This application supports multi-turn, resumable sessions and generates beautifully formatted Markdown reports.

## Features

- **Multi-Model Council**: Query multiple LLMs from various providers simultaneously via OpenRouter.
- **Live Progress**: A real-time terminal dashboard shows the status and response time of each model.
- **Conversational & Resumable**: Engage in multi-turn conversations. Sessions are automatically saved and can be resumed after a crash or interruption.
- **AI-Powered Synthesis**: A powerful "Rapporteur" model synthesizes the council's advice into a structured report.
- **Obsidian-Friendly Export**: Generates clean, well-formatted Markdown files perfect for knowledge management.
- **Modular & Configurable**: Easily change council members, the rapporteur, and all system prompts by editing simple `.toml` files.

## Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/ai-council.git
    cd ai-council
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set API Key**
    You must have an [OpenRouter.ai](https://openrouter.ai/) account and API key. Set it as an environment variable.
    
    *On Windows:*
    ```cmd
    set OPENROUTER_API_KEY="your-key-here"
    ```
    *On macOS/Linux:*
    ```bash
    export OPENROUTER_API_KEY="your-key-here"
    ```

4.  **Configure Your Council**
    Edit `config/models.toml` to select the LLMs you want to include in your council and as your rapporteur.

## Usage

Simply run the main script from the root directory of the project:

```bash
python main.py
```

You will be prompted for a question. Once the council has deliberated, a Markdown report will be saved in the output/ directory.
