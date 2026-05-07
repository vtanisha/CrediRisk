import logging
import os
import warnings

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# Native Tabular PyTorch approximation for FT-Transformer
class TabularDeepModel(nn.Module):
    def __init__(self, d_in, d_out):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, 128),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(64, d_out),
            nn.Sigmoid()
        )
        
    def forward(self, x_num, x_cat=None):
        out = self.net(x_num)
        return out

def train_model():
    csv_path = "Bank Data Sources/application_data.csv"
    if not os.path.exists(csv_path):
        print(f"Dataset missing: {csv_path}")
        return

    logger.info("Loading empirical data...")
    # Load 5000 rows for rapid local training demonstration
    df = pd.read_csv(csv_path, nrows=5000)
    
    # 4 distinct features required by the frontend risk model
    features = ['AMT_INCOME_TOTAL', 'AMT_CREDIT', 'DAYS_BIRTH', 'EXT_SOURCE_2']
    
    logger.info("Preprocessing tabular features...")
    df['EXT_SOURCE_2'] = df['EXT_SOURCE_2'].fillna(df['EXT_SOURCE_2'].mean())
    df['DAYS_BIRTH'] = df['DAYS_BIRTH'] / -365.0 # Transform to positive Age in years

    X = df[features].values
    y = df['TARGET'].values
    
    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    # PyTorch Data structures
    X_tr = torch.tensor(X_train_scaled, dtype=torch.float32)
    y_tr = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
    
    logger.info("Initializing model architecture...")
    try:
        import rtdl
        logger.info("RTDL loaded — using FT-Transformer")
        class RTDLWrapper(nn.Module):
            def __init__(self):
                super().__init__()
                self.ft = rtdl.FTTransformer.make_default(
                    n_num_features=len(features),
                    cat_cardinalities=None,
                    last_layer_query_expected_dim=8,
                    d_out=1
                )
                self.sig = nn.Sigmoid()
            def forward(self, x_num, x_cat=None):
                return self.sig(self.ft(x_num, x_cat))
        model = RTDLWrapper()
    except Exception as e:
        logger.info("Fallback to native PyTorch model: %s", e)
        model = TabularDeepModel(len(features), 1)

    criterion = nn.BCELoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.005)
    
    logger.info("Training for %d epochs...", epochs)
    epochs = 40
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        
        # Train pass
        outputs = model(X_tr)
        
        # Compute loss
        loss = criterion(outputs, y_tr)
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 10 == 0:
            logger.info("Epoch %d/%d | Loss: %.4f", epoch + 1, epochs, loss.item())

    os.makedirs("models", exist_ok=True)
    
    logger.info("Exporting model weights and scaler...")
    torch.save(model.state_dict(), "models/model.pt")
    joblib.dump(scaler, "models/scaler.pkl")
    logger.info("Training complete — model saved to models/model.pt")

if __name__ == "__main__":
    train_model()
