import numpy as np
import pandas as pd
import os
import shutil

# Paths
SMAP_MSL_DIR = os.path.join('data', 'SMAP_MSL')
TRAIN_DIR    = os.path.join(SMAP_MSL_DIR, 'train')
TEST_DIR     = os.path.join(SMAP_MSL_DIR, 'test')
LABELS_FILE  = os.path.join(SMAP_MSL_DIR, 'labeled_anomalies.csv')

SMAP_OUT = os.path.join('processed', 'SMAP')
MSL_OUT  = os.path.join('processed', 'MSL')

os.makedirs(SMAP_OUT, exist_ok=True)
os.makedirs(MSL_OUT,  exist_ok=True)

# Load labels CSV
labels_df = pd.read_csv(LABELS_FILE)
print(f"Labels loaded: {len(labels_df)} rows")
print(labels_df.head())

# Separate SMAP and MSL channels
# SMAP channels start with: A,B,D,E,F,G,P,R,S,T
# MSL  channels start with: C, M
SMAP_PREFIX = ['A','B','D','E','F','G','P','R','S','T']
MSL_PREFIX  = ['C','M']

def get_labels_array(channel, labels_df, test_length):
    label_array = np.zeros(test_length)
    chan_labels = labels_df[labels_df['chan_id'] == channel]
    for _, row in chan_labels.iterrows():
        try:
            seqs = eval(row['anomaly_sequences'])
            for start, end in seqs:
                label_array[start:end+1] = 1
        except:
            pass
    return label_array

train_files = [f for f in os.listdir(TRAIN_DIR) if f.endswith('.npy')]

smap_count = 0
msl_count  = 0

for fname in sorted(train_files):
    channel = fname.replace('.npy', '')
    prefix  = channel.split('-')[0]

    train_data = np.load(os.path.join(TRAIN_DIR, fname))
    test_path  = os.path.join(TEST_DIR, fname)

    if not os.path.exists(test_path):
        print(f"Skipping {channel} — no test file found")
        continue

    test_data = np.load(test_path)
    label_arr = get_labels_array(channel, labels_df, test_data.shape[0])

    if prefix in SMAP_PREFIX:
        out_dir = SMAP_OUT
        smap_count += 1
    elif prefix in MSL_PREFIX:
        out_dir = MSL_OUT
        msl_count += 1
    else:
        print(f"Unknown prefix for channel {channel}, skipping")
        continue

    np.save(os.path.join(out_dir, f'{channel}_train.npy'),  train_data)
    np.save(os.path.join(out_dir, f'{channel}_test.npy'),   test_data)
    np.save(os.path.join(out_dir, f'{channel}_labels.npy'), label_arr)
    print(f"Processed {channel} -> train{train_data.shape} test{test_data.shape} labels{label_arr.shape}")

print(f"\nDone! SMAP channels: {smap_count}, MSL channels: {msl_count}")
print(f"Total files in processed/SMAP: {len(os.listdir(SMAP_OUT))}")
print(f"Total files in processed/MSL:  {len(os.listdir(MSL_OUT))}")