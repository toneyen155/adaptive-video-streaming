#!/usr/bin/env python3

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib

# # Load raw data
# df = pd.read_csv('data/training_data.csv')

# # Group by network state and quality to compute average QoE
# df['qoe'] = (df['quality'] / 100) * 0.5 - (df['loss_rate'] / 100) * 0.3 - (df['delay_ms'] / 500) * 0.2

# # For each combination of network metrics, find the best quality
# best_per_state = df.loc[df.groupby(['loss_rate', 'delay_ms', 'jitter_ms'])['qoe'].idxmax()]
# best_per_state = best_per_state[['loss_rate', 'delay_ms', 'jitter_ms', 'quality']]

# # This is your training data
# X = best_per_state[['loss_rate', 'delay_ms', 'jitter_ms']]
# y = best_per_state['quality']

# print(f"Dataset shape: {X.shape}")
# print(X.head())


# # Split into train/test (80/20)
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# # 
# models = {
#     'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42),
#     'ExtraTrees': ExtraTreesRegressor(n_estimators=100, random_state=42)
# }

# for name, model in models.items():
#     model.fit(X_train, y_train)
#     y_pred = model.predict(X_test)
    
#     r2 = r2_score(y_test, y_pred)
#     rmse = np.sqrt(mean_squared_error(y_test, y_pred))
#     mae = mean_absolute_error(y_test, y_pred)
    
#     print(f"{name} Results:")
#     print(f"  R²: {r2:.3f}")
#     print(f"  RMSE: {rmse:.2f}")
#     print(f"  MAE: {mae:.2f}")
    
#     # Cross-validation score
#     cv_score = cross_val_score(model, X_train, y_train, cv=5, scoring='r2')
#     print(f"  Cross-val R²: {cv_score.mean():.3f} (+/- {cv_score.std():.3f})")
#     print()

# # Choose the best model (e.g., ExtraTrees)
# best_model = ExtraTreesRegressor(n_estimators=100, random_state=42)
# best_model.fit(X, y)  # Train on all data
# joblib.dump(best_model, 'models/quality_predictor.pkl')
# print("Model saved to models/quality_predictor.pkl")

# # Feature importance
# importances = best_model.feature_importances_
# feature_names = X.columns
# for name, imp in zip(feature_names, importances):
#     print(f"{name}: {imp:.2%}")

# Load your CSV (adjust filename)
df = pd.read_csv('data/training_data.csv')   # or whatever your file is

# Group by network params and quality
grouped = df.groupby(['loss_rate', 'delay_ms', 'jitter_ms', 'quality', 'scale']).agg({
    'frame_size_bytes': 'mean',
    'encode_time_ms': 'mean',
    'send_time_ms': 'mean',
    'was_dropped': 'sum',
    'was_delayed': 'sum',
    'frame_id': 'count'
}).reset_index()

# Rename columns
grouped.columns = [
    'loss_rate', 'delay_ms', 'jitter_ms', 'quality', 'scale',
    'avg_frame_size', 'avg_encode_time', 'avg_send_time',
    'total_dropped', 'total_delayed', 'total_frames'
]

# Compute derived metrics
grouped['drop_rate'] = grouped['total_dropped'] / grouped['total_frames']
grouped['bitrate_kbps'] = (grouped['avg_frame_size'] * 8 * 30) / 1000  # assuming 30 fps

# Compute a QoE score for each experiment
grouped['qoe'] = (
    (grouped['quality'] / 100) * 0.4 +
    (1 - grouped['drop_rate']) * 0.3 +
    (grouped['bitrate_kbps'] / 5000) * 0.2 +
    (1 - grouped['avg_send_time'] / 200) * 0.1
)

# For each network state, pick the quality with the highest QoE
best = grouped.loc[grouped.groupby(['loss_rate', 'delay_ms', 'jitter_ms'])['qoe'].idxmax()]
best = best[['loss_rate', 'delay_ms', 'jitter_ms', 'quality']]

print(f"Number of unique network states: {len(best)}")

X = best[['loss_rate', 'delay_ms', 'jitter_ms']]
y = best['quality']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

print("Train R²:", r2_score(y_train, model.predict(X_train)))
print("Test R²:", r2_score(y_test, model.predict(X_test)))
print("CV R² (5-fold):", cross_val_score(model, X, y, cv=5).mean())