import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
data = ROOT / "data" / "mtsamples.csv"

RANDOM_STATE = 42
SAMPLE_SIZE = 10

df = pd.read_csv(data)
print(f"Before: {len(df)}")
df.drop(columns='Unnamed: 0', inplace=True)
# stable ID = original row index in mtsamples.csv, so outputs never depend on list position
df["note_id"] = df.index
df = df[(df['medical_specialty'].str.contains("discharge summary", case=False))
        | (df['sample_name'].str.contains("discharge", case=False))]
df = df[(df["transcription"].notna()) 
        & (df["transcription"].str.len() > 200)]

for col in df.columns:
    if str(df[col].dtype) in ["object", "str", "string"]:
        df[col] = df[col].str.strip()

print(f"Duplicated transcriptions: {df['transcription'].duplicated().sum()}")
df.drop_duplicates(subset="transcription", inplace=True)
print(f"After: {len(df)}")

# shuffle the notes so that they are randomized (not keeping original order - not representative of entire dataset)
df = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
dev = df.iloc[:SAMPLE_SIZE]
test = df.iloc[SAMPLE_SIZE:]

# drop death summaries after the split (no discharge instructions for a patient)
dev_death = dev["sample_name"].str.contains("death", case=False)
test_death = test["sample_name"].str.contains("death", case=False)
print(f"Death summaries removed: dev {dev_death.sum()} | test {test_death.sum()}")
dev = dev[~dev_death]
test = test[~test_death]

dev.to_csv(ROOT/"data"/"dev.csv", index=False)
test.to_csv(ROOT/"data"/"test.csv", index=False)

print(f"Dev: {len(dev)} notes | Test: {len(test)} notes")
# print(df.sample(5, random_state=1)[["medical_specialty", "sample_name"]])