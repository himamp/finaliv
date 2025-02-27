import os
import time
import sqlite3
import streamlit as st
import pandas as pd
import speech_recognition as sr
import requests
import subprocess
import os
import subprocess

# Install missing dependencies dynamically
required_packages = ["speechrecognition", "pydub", "requests", "pandas", "openpyxl"]

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        subprocess.run(["pip", "install", package])

# Download ffmpeg dynamically
if not os.path.exists("ffmpeg"):
    subprocess.run(["apt-get", "update"])
    subprocess.run(["apt-get", "install", "-y", "ffmpeg"])

import streamlit as st
OPENROUTER_API_KEY = "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"

import streamlit as st

# Load API key from Streamlit secrets
openrouter_api_key = st.secrets["OPENROUTER_API_KEY"]

if not openrouter_api_key:
    st.error("⚠️ OpenRouter API Key is missing! Set it in secrets.toml or Streamlit Cloud settings.")
    st.stop()

# ✅ Step 1: Ensure all required packages are installed
required_packages = ["speechrecognition", "pydub", "requests", "pandas", "openpyxl"]

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        subprocess.run(["pip", "install", package])

# ✅ Step 2: Ensure OpenRouter API Key is Set Securely
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_api_key:
    st.error("⚠️ OpenRouter API Key is missing! Set OPENROUTER_API_KEY in your environment.")
    st.stop()

# ✅ Step 3: OpenRouter API URL
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ✅ Step 4: Load Questions & Answers from Excel
@st.cache_data
def load_questions():
    file_path = "/Users/himamp/Documents/questions.xlsx"  # Adjust this path as needed
    if not os.path.exists(file_path):
        st.error(f"⚠️ Error: The file '{file_path}' was not found.")
        st.stop()

    df = pd.read_excel(file_path)
    df.rename(columns=lambda x: x.strip(), inplace=True)  # Strip column names

    if "Question" not in df.columns or "Answer" not in df.columns:
        st.error(f"⚠️ Error: Expected columns 'Question' and 'Answer', but found: {df.columns.tolist()}")
        st.stop()

    return df

# ✅ Step 5: Transcribe Audio Using Google Speech Recognition
def transcribe_audio(audio_data):
    recognizer = sr.Recognizer()
    
    try:
        response_text = recognizer.recognize_google(audio_data)
        return response_text.strip()
    except sr.UnknownValueError:
        return "❌ Could not understand the audio."
    except sr.RequestError:
        return "❌ Error connecting to Google Speech-to-Text API."

# ✅ Step 6: AI-based Answer Scoring with OpenRouter (GPT-4o)
def score_response(user_answer, correct_answer, use_ai=True):
    if use_ai:
        prompt = f"""
        You are an interview evaluator. Compare the candidate's response to the correct answer.
        - Candidate Response: {user_answer}
        - Model Answer: {correct_answer}
        Give a score **between 0-10** based on relevance, completeness, and correctness.
        **Only return a numeric score between 0-10** with no extra text.
        """

        headers = {
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "openai/gpt-4o",
            "messages": [{"role": "system", "content": prompt}],
            "max_tokens": 5
        }

        response = requests.post(OPENROUTER_URL, json=data, headers=headers)

        if response.status_code == 200:
            result = response.json()
            score_text = result["choices"][0]["message"]["content"].strip()

            try:
                score = int(score_text)
                return min(max(score, 0), 10)  # Ensure it's between 0-10
            except ValueError:
                return 0  # Default to 0 if AI gives non-numeric output
        else:
            return 0

    return 10 if user_answer.lower().strip() == correct_answer.lower().strip() else 0

# ✅ Step 7: Save Results to SQLite Database
def save_results(candidate_name, responses):
    conn = sqlite3.connect("interviews.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS results (name TEXT, question TEXT, response TEXT, score INTEGER)")
    for question, (response, score) in responses.items():
        cursor.execute("INSERT INTO results VALUES (?, ?, ?, ?)", (candidate_name, question, response, score))
    conn.commit()
    conn.close()

# ✅ Step 8: Main Streamlit UI
def main():
    st.title("🎙️ AI-Powered Interview System")
    questions_df = load_questions()
    candidate_name = st.text_input("Enter Candidate Name")

    if candidate_name:
        responses = {}

        for idx, row in questions_df.iterrows():
            st.subheader(f"🔹 Question {idx+1}: {row['Question']}")
            
            # ✅ Record Answer (Mic Only) - 30 seconds response time
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                st.write("🎤 Listening... Speak now! (You have **30 seconds**)")
                try:
                    audio = recognizer.listen(source, timeout=30)  # ⏳ 30 seconds to respond
                    st.write("🔄 Processing your response...")
                    response_text = transcribe_audio(audio)

                    if response_text:
                        st.write(f"📝 **Transcribed Answer:** {response_text}")
                    else:
                        st.warning("❌ No speech detected. Please ensure your microphone is working.")
                        response_text = ""

                except sr.WaitTimeoutError:
                    st.warning("⏳ No response detected. Please try again.")
                    response_text = ""
                except Exception as e:
                    st.error(f"❌ Error capturing audio: {e}")
                    response_text = ""

            # ✅ Score the response
            score = score_response(response_text, row["Answer"])
            responses[row["Question"]] = (response_text, score)
            st.write(f"✅ **Score:** {score}/10")

            time.sleep(1)  # Short delay before next question

        # ✅ Save to Database
        save_results(candidate_name, responses)

        # ✅ Show Final Report
        total_score = sum(score for _, score in responses.values())
        st.success(f"🏆 **Final Score:** {total_score}/{len(questions_df) * 10}")

        st.write("📜 **Interview Transcript:**")
        for question, (answer, score) in responses.items():
            st.write(f"**Q:** {question}\n**A:** {answer} (Score: {score}/10)")

if __name__ == "__main__":
    main()
