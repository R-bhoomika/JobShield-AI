import joblib

# Load model
model = joblib.load("model/job_detector.pkl")

# Load vectorizer
vectorizer = joblib.load("model/vectorizer.pkl")

print("JobShield AI Started")

while True:

    print("\nPaste Job Description:")
    text = input()

    if text.lower() == "exit":
        break

    vector = vectorizer.transform([text])

    prediction = model.predict(vector)[0]

    probability = model.predict_proba(vector)[0][1]

    if prediction == 1:
        print("\n🚨 FAKE JOB DETECTED")
    else:
        print("\n✅ LEGITIMATE JOB")

    print(f"Risk Score: {probability*100:.2f}%")