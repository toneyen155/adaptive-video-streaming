#!/usr/bin/env python3

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib

df = pd.read_csv('data/training_data.csv')

# Group by network params AND quality, scale, fps
grouped = df.groupby(['loss_rate', 'delay_ms', 'jitter_ms', 'quality', 'scale', 'fps']).agg({
    'frame_size_bytes': 'mean',
    'encode_time_ms': 'mean',
    'send_time_ms': 'mean',
    'was_dropped': 'sum',
    'was_delayed': 'sum',
    'frame_id': 'count'
}).reset_index()

# Rename columns
grouped.columns = [
    'loss_rate', 'delay_ms', 'jitter_ms', 'quality', 'scale', 'fps',
    'avg_frame_size', 'avg_encode_time', 'avg_send_time',
    'total_dropped', 'total_delayed', 'total_frames'
]

# Compute derived metrics
grouped['drop_rate'] = grouped['total_dropped'] / grouped['total_frames']
grouped['bitrate_kbps'] = (grouped['avg_frame_size'] * 8 * grouped['fps']) / 1000  # use actual fps

# Compute a QoE score for each experiment
grouped['qoe'] = (
    (grouped['quality'] / 100) * 0.4 +
    (1 - grouped['drop_rate']) * 0.3 +
    (grouped['bitrate_kbps'] / 5000) * 0.2 +
    (1 - grouped['avg_send_time'] / 200) * 0.1
)

# For each network state, pick the combination with the highest QoE
best = grouped.loc[grouped.groupby(['loss_rate', 'delay_ms', 'jitter_ms'])['qoe'].idxmax()]
best = best[['loss_rate', 'delay_ms', 'jitter_ms', 'quality', 'scale', 'fps']]

print(f"Number of unique network states: {len(best)}")

X = best[['loss_rate', 'delay_ms', 'jitter_ms']]
y = best[['quality', 'scale', 'fps']]   

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
joblib.dump(model, 'models/quality_predictor.pkl')
print("Model saved to models/quality_predictor.pkl")

print("Train R²:", r2_score(y_train, model.predict(X_train)))
print("Test R²:", r2_score(y_test, model.predict(X_test)))
print("CV R² (5-fold):", cross_val_score(model, X, y, cv=5).mean())