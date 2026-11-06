import pandas as pd

# Load dataset
df = pd.read_csv("../dataset/fake_job_postings.csv")

# Fill missing values
text_columns = [
    "title",
    "company_profile",
    "description",
    "requirements",
    "benefits"
]

for col in text_columns:
    df[col] = df[col].fillna("")

# Merge all text columns
df["combined_text"] = (
    df["title"] + " " +
    df["company_profile"] + " " +
    df["description"] + " " +
    df["requirements"] + " " +
    df["benefits"]
)

# Keep only required columns
processed_df = df[["combined_text", "fraudulent"]]

print(processed_df.head())

print("\nDataset Shape:")
print(processed_df.shape)

# Save cleaned dataset
processed_df.to_csv(
    "../dataset/processed_jobs.csv",
    index=False
)

print("\nProcessed dataset saved successfully!")