# 🚀 Project Codexa: AI-Powered Gamified Learning Platform

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Project Codexa** is a fully-featured, gamified AI learning platform built with Streamlit. It leverages a local, offline-first large language model (`gpt-oss:20b` via Ollama) to provide personalized educational content for students from Class 6 to 12 in India. The platform is designed to make learning interactive, engaging, and fun through a rich set of gamification mechanics.

The centerpiece of the experience is the **"Doodle Map Quiz Adventure,"** a unique, visually-driven quiz system where correct answers move you forward on a map, and incorrect answers push you back, creating a challenging and rewarding journey.

> 💡 **Suggestion:** Add a GIF of the app in action (especially the Doodle Map Quiz) to showcase the experience.

---

## ✨ Key Features

### 🧠 Core Learning & AI Engine
- **Personalized Lessons:** AI-generated lessons tailored to class, subject, chapter, and specific sub-parts.  
- **AI-Generated Quizzes:** Dynamic quizzes created by the AI based on the lesson content.  
- **Doodle Map Quiz Adventure:** Interactive quiz format where progress is visualized on a map. You must achieve 80% accuracy to pass.  
- **"Ask a Question":** A contextual chatbot that answers student questions about the current chapter.  
- **Multi-Language Support:** Designed to provide content in multiple Indian languages.  
- **Text-to-Speech (TTS):** Listen to lessons with configurable voice, rate, and volume.  

### 🎮 Complete Gamification System
- **XP, Levels & Ranks:** Earn XP to level up and achieve ranks from "Rookie" to "Grandmaster".  
- **In-Game Economy:** Earn **Coins** and **Credits** for completing activities.  
- **Daily & Weekly Quests:** Objectives like *Complete 3 quizzes* or *Score 80%+ in a quiz* for bonus rewards.  
- **Streaks:** Maintain a **Daily Streak** for logging in and a **Correct Answer Streak** for flawless performance.  
- **Achievements & Badges:** Unlock dozens of achievements like "Flawless" (100% quiz score) or "Marathon" (50 correct answers).  
- **Shop & Unlocks:** Spend coins to unlock new **Avatars** or purchase credit packs.  
- **Mini-Games:** Play a fully-functional **Sudoku** game using game credits to earn extra XP.  

### 📊 Advanced Analytics & Progress Tracking
- **Activity Heatmap:** GitHub-style calendar heatmap of daily quiz activity.  
- **Mastery Heatmap:** Visual breakdown of quiz accuracy across subjects and chapters.  
- **Progress Timeline:** Charts tracking cumulative XP, quizzes completed, and daily accuracy.  
- **Detailed Stats:** Track quizzes taken, average accuracy, subjects studied, and learning badges.  

---

## 🛠️ Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/)  
- **AI Backend:** [Ollama](https://ollama.ai/) serving `gpt-oss:20b`  
- **Data Visualization:** [Plotly](https://plotly.com/)  
- **Data Handling:** [Pandas](https://pandas.pydata.org/)  
- **Text-to-Speech:** [pyttsx3](https://pypi.org/project/pyttsx3/)  

---

## 🔧 Getting Started

### Prerequisites
1. **Python:** Install Python 3.9+  
2. **Git:** Required to clone the repository  
3. **Ollama:** Install and run [Ollama](https://ollama.ai/) to serve the LLM  

### Installation & Setup

1. **Clone the Repository**
    ```bash
    git clone https://github.com/AR-Anirudhan/SIH-Codexa-V2.git
    cd SIH-Codexa-V2
    ```

2. **Set Up Virtual Environment (Recommended)**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install Dependencies**  
    Create `requirements.txt`:
    ```txt
    streamlit
    pandas
    pyttsx3
    ollama
    plotly
    calplot
    ```
    Install packages:
    ```bash
    pip install -r requirements.txt
    ```

    > ⚠️ **Note:** `pyttsx3` may require additional system libraries (e.g., `espeak` on Linux).

4. **Download the AI Model**
    ```bash
    ollama pull gpt-oss:20b
    ```

5. **Run the App**
    ```bash
    streamlit run app.py
    ```

Visit: [http://localhost:8501](http://localhost:8501)

---

## ⚙️ Project Structure

```text
SIH-Codexa-V2/
├── app.py           # Streamlit frontend & gamification logic
├── tutor_engine.py  # AI engine (prompts, lessons, quizzes)
├── requirements.txt
└── README.md
```


---

## 🤝 Contributing

Contributions are welcome!  

1. Fork the repository  
2. Create a feature branch  
   ```bash
   git checkout -b feature/AmazingFeature
   ```

Commit your changes

git commit -m "Add some AmazingFeature"


Push to your branch

git push origin feature/AmazingFeature


Open a Pull Request

📜 License

This project is licensed under the MIT License – see the LICENSE
 file for details.

📧 Contact

AR Anirudhan
📧 Email: anirudhanksr59@gmail.com

🔗 GitHub: github.com/AR-Anirudhan/SIH-Codexa-V2

💼 LinkedIn: www.linkedin.com/in/ar-anirudhan-data

