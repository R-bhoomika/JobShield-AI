# JobShield AI – AI-Powered Fake Job Detection and Company Verification System

## 📌 Project Overview

**JobShield AI** is an intelligent web-based application designed to detect potentially fake job postings and help users verify company information.

The system combines Machine Learning, Artificial Intelligence, rule-based checking, and company verification to analyze job descriptions, job URLs, and job-posting images. It generates a detailed analysis report to help job seekers identify suspicious recruitment activities and make safer career decisions.

## 🎯 Objectives

- Detect potentially fraudulent job postings using Machine Learning.
- Identify suspicious words, phrases, and recruitment patterns.
- Analyze job descriptions using AI.
- Extract job information from URLs and images.
- Verify company details and official website information.
- Display analysis results through an interactive dashboard.

## ✨ Key Features

### 1. Job Fraud Detection
Uses a trained Machine Learning model to classify job postings as potentially fake or genuine.

### 2. AI-Powered Analysis
Uses the Groq API to analyze job descriptions and provide explanations, risk scores, and suspicious indicators.

### 3. Rule-Based Detection
Checks for suspicious recruitment indicators such as:
- Requests for registration or security fees.
- Unusual salary promises.
- Requests for sensitive personal information.
- Suspicious contact details.
- Unrealistic job offers.

### 4. Job URL Analysis
Accepts job-posting URLs and attempts to extract relevant job details for analysis.

### 5. Image-Based Job Analysis
Allows users to submit job-posting screenshots for text extraction and analysis.

### 6. Company Verification
Checks available company information, website details, and related online information to support company verification.

### 7. Interactive Dashboard
Displays analysis results, risk information, company details, and analytical insights.

### 8. Analysis History
Stores previous analysis results in the browser's Local Storage for convenient access.

## 🛠️ Technologies Used

| Category | Technologies |
|---|---|
| Frontend | React.js, Vite, JavaScript |
| Backend | Python, FastAPI |
| Machine Learning | TF-IDF, XGBoost |
| AI Integration | Groq API |
| Web Scraping | Requests, BeautifulSoup |
| Company Search | Tavily Search API |
| Data Processing | Python |
| Model Storage | Joblib |
| Local Storage | Browser Local Storage |

## ⚙️ System Architecture

The application follows a client-server architecture.

1. **Frontend:** Users enter job descriptions, URLs, or job-posting images.
2. **Backend:** FastAPI receives the input and processes the request.
3. **Machine Learning:** The trained model predicts the job classification.
4. **Rule-Based Analysis:** Suspicious indicators are identified.
5. **AI Analysis:** Groq provides additional analysis and explanations.
6. **Company Verification:** Available company and website information is checked.
7. **Results:** The frontend displays the combined analysis through the dashboard.

## 🔄 Project Workflow

```text
User Input
    |
    v
Job Description / URL / Image
    |
    v
Backend Processing
    |
    v
Text Extraction and Preprocessing
    |
    v
Machine Learning Prediction
    |
    v
Rule-Based Detection
    |
    v
Groq AI Analysis
    |
    v
Company Verification
    |
    v
Final Analysis Report
    |
    v
Interactive Dashboard
```

## 📂 Project Structure

The project contains separate frontend, backend, and machine learning components.

```text
JobShield-AI/
│
├── backend/
│   └── app/
│       ├── main.py
│       ├── routes/
│       └── services/
│
├── ml/
│   └── model/
│       ├── job_detector.pkl
│       └── vectorizer.pkl
│
├── src/
│   ├── components/
│   ├── App.jsx
│   └── main.jsx
│
├── .env.example
├── .gitignore
├── requirements.txt
├── package.json
└── README.md
```

*Note: The structure above is a general overview. Your actual project may contain additional files and folders.*

## 💻 Installation and Setup

### Prerequisites

Install the following before running the project:

- Python
- Node.js and npm
- Visual Studio Code
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/R-bhoomika/JobShield-AI.git
```

### Step 2: Open the Project

```bash
cd JobShield-AI
```

### Step 3: Set Up the Backend

Create a virtual environment:

```bash
python -m venv venv
```

Activate it in Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Step 4: Configure API Keys

Create a `.env` file in the location expected by the backend configuration.

Add your API keys:

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Replace the example values with your own API keys. Never upload your actual `.env` file or expose API keys publicly.

### Step 5: Start the Backend

From the project root, run:

```bash
python -m uvicorn backend.app.main:app --reload
```

### Step 6: Set Up the Frontend

Open another terminal and navigate to the frontend directory containing `package.json`.

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the local URL displayed in the terminal to access the application.

## 🤖 Machine Learning Approach

JobShield AI uses a trained XGBoost classification model with TF-IDF text vectorization.

**TF-IDF:** Converts textual job descriptions into numerical features that can be processed by a Machine Learning model.

**XGBoost:** Uses the extracted features to predict whether a job posting is potentially fake or genuine.

The application also uses rule-based checks and AI analysis to provide additional information beyond the ML prediction.

## 🔐 Security and Limitations

- API keys should be stored securely in environment variables.
- Company verification depends on the availability and accuracy of online information.
- Dynamic websites may not always provide extractable job details.
- AI-generated analysis may not always be accurate.
- A low-risk result does not guarantee that a job offer is genuine.
- Users should independently verify job offers before sharing personal information or making payments.

## 🚀 Future Enhancements

- Improve model accuracy using larger and more diverse datasets.
- Add real-time job portal integration.
- Improve company verification using trusted data sources.
- Support additional languages.
- Add user authentication and cloud-based analysis history.
- Improve screenshot text extraction.
- Develop a browser extension for checking job postings.

## 🎓 Project Information

**Project Name:** JobShield AI    
**Domain:** Artificial Intelligence and Machine Learning  
**GitHub Repository:** https://github.com/R-bhoomika/JobShield-AI

## 👩‍💻 Author

**Bhoomika R**
