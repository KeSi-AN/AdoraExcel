# 📄 AI-Powered Excel Parser Pro

[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Excel Table Analyzer** is a powerful Streamlit application for analyzing Excel files, extracting tables, and enabling natural language queries against your data.

## Features

- 📤 Upload and process Excel files
- 📊 Extract and view tables from multiple sheets
- 🔍 Browse and search through uploaded files
- 💬 Chat with your data using natural language (coming soon)
- 🗄️ Store and manage files in a PostgreSQL database
- **Persistent Storage**: SQLite database for storing resume data
- **Advanced Search**: Filter and search through Excels using various criteria

## 🚀 Quick Start

### Prerequisites


- [Git](https://git-scm.com/)

### Running with Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Excel-parser-pro.git
   cd resume-parser-pro
   ```

2. **Set up environment variables**
   - Copy `.env.example` to `.env`
   - Add your OPEN_AI API key
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

3. **Build and start the application**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   Open your browser and navigate to:
   ```
   http://localhost:8501
   ```

## 🛠️ Features in Detail

### 📤 Upload Resumes
- Drag and drop or select Excel files
- Automatic duplicate detection
- Batch upload support

### 🔍 Browse & Search
- View all parsed Excels


### 💬 AI Chat Interface
- Ask questions about Excels

## 🧩 Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python 3.10
- **AI/ML**: 
  - LangChain
  - OPENAI_API
  - Hugging Face Transformers
- **Database**: SQLite, PostgreSQL
- **Vector Store**: FAISS


## 🏗️ Project Structure

```
Excel-parser-pro/
├── .env.example
├── .gitignore
├── README.md
├── app.py              # Main application
├── requirements.txt     # Python dependencies
├── uploads/             # Store uploaded resumes
└── Excel_database.db   # SQLite database
```


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  Made with ❤️ using Streamlit and Python
</div>
