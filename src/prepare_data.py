import pandas as pd
import os

curr_dir = os.getcwd()
data = os.path.join(curr_dir, "data", "mtsamples.csv")

RANDOM_STATE = 42
SAMPLE_SIZE = 10

df = pd.read_csv(data)
print(f"Before: {len(df)}")
df.drop(columns='Unnamed: 0', inplace=True)
df = df[(df['medical_specialty'].str.contains("discharge summary", case=False))
        | (df['sample_name'].str.contains("discharge", case=False))]
df = df[(df["transcription"].notna()) 
        & (df["transcription"] != "")
        & (df["transcription"].str.len() > 200)]

print(f"Duplicated transcriptions: {df["transcription"].duplicated().sum()}")

df.drop_duplicates(subset="transcription", inplace=True)
df["transcription"] = df["transcription"].str.strip()
print(f"After: {len(df)}")

# shuffle the notes so that they are randomized (not keeping original order - not representative of entire dataset)
df = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
dev = df[:SAMPLE_SIZE]
test = df[SAMPLE_SIZE:]

# dev.to_csv("data/dev.csv", index=False)
# test.to_csv("data/test.csv", index=False)

print(f"Dev: {len(dev)} notes | Test: {len(test)} notes")
print(df.sample(5, random_state=1)[["medical_specialty", "sample_name"]])