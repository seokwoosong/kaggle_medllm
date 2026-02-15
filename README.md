# 🏥 Medical LLM Demo App (Kaggle MedLLM Competition)

This repository contains a demo application designed to showcase a solution for the **Kaggle Medical LLM Competition**. It leverages Google's Medical LLM capabilities to simulate clinical reasoning, Q&A, and patient data analysis.

---

## 🚀 Key Features
* **Clinical Q&A**: Generates expert-level responses to complex medical queries using Google Medical LLM.
* **Scenario-Based Reasoning**: Simulates inference results based on specific clinical scenarios (`assets/scenario.py`).
* **Patient Data Visualization**: Interactive dashboard functionality fueled by sample patient datasets (`assets/patients.py`).
* **Medical UI/UX**: A clean, medical-grade interface styled with custom CSS (`assets/style.css`).

## 🛠 Tech Stack
* **Language**: Python 3.14+
* **Framework**: Streamlit
* **Model**: Google Gemini / Med-PaLM 2 (via Kaggle MedLLM API)
* **Styling**: CSS3

## 📂 Project Structure
```text
.
├── app.py              # Main application entry point
├── requirements.txt    # Python dependencies
├── assets/
│   ├── patients.py     # Sample patient datasets
│   ├── scenario.py     # Clinical scenario data
│   └── style.css       # Application stylesheet
└── README.md           # Project documentation
