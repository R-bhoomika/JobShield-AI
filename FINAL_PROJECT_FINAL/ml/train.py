import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report

from xgboost import XGBClassifier


# Load processed dataset
df = pd.read_csv("../dataset/processed_jobs.csv")

# Features and target
X = df["combined_text"]
y = df["fraudulent"]

print("Dataset Loaded Successfully")
print("Total Records:", len(df))

# TF-IDF Vectorization
vectorizer = TfidfVectorizer(
    max_features=5000,
    stop_words="english"
)

X_vectorized = vectorizer.fit_transform(X)

print("TF-IDF Completed")

# Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X_vectorized,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("Train-Test Split Completed")

# XGBoost Model
model = XGBClassifier(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    scale_pos_weight=20,
    eval_metric="logloss",
    random_state=42
)

print("Training Started...")
model.fit(X_train, y_train)

print("Training Completed!")

# Predictions
y_pred = model.predict(X_test)

# Evaluation
accuracy = accuracy_score(y_test, y_pred)

print("\nAccuracy:")
print(round(accuracy * 100, 2), "%")

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Save model
joblib.dump(model, "model/job_detector.pkl")

# Save vectorizer
joblib.dump(vectorizer, "model/vectorizer.pkl")

print("\nModel Saved Successfully!")