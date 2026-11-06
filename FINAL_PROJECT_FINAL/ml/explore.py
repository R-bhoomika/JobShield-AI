import pandas as pd

df = pd.read_csv("../dataset/fake_job_postings.csv")

print(df.head())

print("\nShape:")
print(df.shape)

print("\nColumns:")
print(df.columns)

print("\nMissing Values:")
print(df.isnull().sum())

print("\nFraud Distribution:")
print(df["fraudulent"].value_counts())