import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import dgl
import dgl.nn.pytorch as dglnn
from torch.utils.data import Dataset, DataLoader
import sys
import os
from sklearn.metrics import mean_squared_error, mean_absolute_error

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GNN_PARAMS, MODEL_DIR, PRED_LEN, NUM_ROADS, RANDOM_SEED

torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


class TrafficGNN(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, pred_len, dropout=0.2):
        super(TrafficGNN, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.pred_len = pred_len
        self.output_scale = 10.0

        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)

        self.gat_layers = nn.ModuleList()
        for i in range(num_layers):
            in_dim = hidden_dim * 2 if i == 0 else hidden_dim
            self.gat_layers.append(
                dglnn.GATConv(in_dim, hidden_dim, num_heads=4, feat_drop=dropout, attn_drop=dropout, residual=True)
            )

        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, pred_len)
        )

    def forward(self, g, features):
        batch_size, num_nodes, history_len, feat_dim = features.shape

        x = features.reshape(batch_size * num_nodes, history_len, feat_dim)
        lstm_out, _ = self.lstm(x)
        lstm_out = lstm_out[:, -1, :]
        lstm_out = self.dropout(lstm_out)
        lstm_out = lstm_out.reshape(batch_size, num_nodes, -1)

        h = lstm_out
        for gat in self.gat_layers:
            h = gat(g, h)
            h = h.flatten(2)
            h = F.elu(h)
            h = self.dropout(h)

        out = self.fc(h)
        out = torch.sigmoid(out) * self.output_scale
        return out


class TrafficDataset(Dataset):
    def __init__(self, sequences, targets, road_ids, num_roads=NUM_ROADS):
        self.sequences = sequences
        self.targets = targets
        self.road_ids = road_ids
        self.num_roads = num_roads
        self.unique_samples = len(sequences) // num_roads

    def __len__(self):
        return self.unique_samples

    def __getitem__(self, idx):
        start_idx = idx * self.num_roads
        end_idx = start_idx + self.num_roads

        seq = self.sequences[start_idx:end_idx]
        target = self.targets[start_idx:end_idx]

        return torch.FloatTensor(seq), torch.FloatTensor(target)


class GNNPredictor:
    def __init__(self, input_dim, params=None):
        self.params = params if params else GNN_PARAMS
        self.input_dim = input_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.graph = None

    def build_model(self):
        self.model = TrafficGNN(
            input_dim=self.input_dim,
            hidden_dim=self.params["hidden_dim"],
            num_layers=self.params["num_layers"],
            pred_len=PRED_LEN,
            dropout=self.params["dropout"]
        ).to(self.device)
        return self.model

    def set_graph(self, g):
        self.graph = g.to(self.device)

    def train(self, train_sequences, train_targets, train_road_ids,
              val_sequences=None, val_targets=None, val_road_ids=None):
        self.build_model()

        train_dataset = TrafficDataset(train_sequences, train_targets, train_road_ids)
        train_loader = DataLoader(train_dataset, batch_size=self.params["batch_size"], shuffle=True)

        val_loader = None
        if val_sequences is not None:
            val_dataset = TrafficDataset(val_sequences, val_targets, val_road_ids)
            val_loader = DataLoader(val_dataset, batch_size=self.params["batch_size"], shuffle=False)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.params["lr"])
        criterion = nn.MSELoss()

        best_val_loss = float("inf")
        patience = 10
        counter = 0

        for epoch in range(self.params["epochs"]):
            self.model.train()
            total_loss = 0.0

            for batch_seq, batch_target in train_loader:
                batch_seq = batch_seq.to(self.device)
                batch_target = batch_target.to(self.device)

                optimizer.zero_grad()
                output = self.model(self.graph, batch_seq)
                loss = criterion(output, batch_target)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()

            avg_train_loss = total_loss / len(train_loader)

            if val_loader is not None:
                self.model.eval()
                val_loss = 0.0
                with torch.no_grad():
                    for batch_seq, batch_target in val_loader:
                        batch_seq = batch_seq.to(self.device)
                        batch_target = batch_target.to(self.device)
                        output = self.model(self.graph, batch_seq)
                        val_loss += criterion(output, batch_target).item()
                avg_val_loss = val_loss / len(val_loader)

                print(f"Epoch {epoch + 1}/{self.params['epochs']} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")

                if avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    counter = 0
                    self.save()
                else:
                    counter += 1
                    if counter >= patience:
                        print("Early stopping!")
                        break
            else:
                print(f"Epoch {epoch + 1}/{self.params['epochs']} - Train Loss: {avg_train_loss:.4f}")
                if avg_train_loss < best_val_loss:
                    best_val_loss = avg_train_loss
                    self.save()

        self.load()

    def predict(self, sequences, road_ids):
        self.model.eval()
        dataset = TrafficDataset(sequences, np.zeros_like(sequences[:, 0, :PRED_LEN]), road_ids)
        loader = DataLoader(dataset, batch_size=self.params["batch_size"], shuffle=False)

        predictions = []
        with torch.no_grad():
            for batch_seq, _ in loader:
                batch_seq = batch_seq.to(self.device)
                output = self.model(self.graph, batch_seq)
                output = output.cpu().numpy()
                predictions.append(output.reshape(-1, PRED_LEN))

        return np.concatenate(predictions, axis=0)

    def evaluate(self, sequences, targets, road_ids):
        y_pred = self.predict(sequences, road_ids)
        mse = mean_squared_error(targets, y_pred)
        mae = mean_absolute_error(targets, y_pred)
        print(f"GNN Evaluation - MSE: {mse:.4f}, MAE: {mae:.4f}")
        return mse, mae

    def save(self, path=os.path.join(MODEL_DIR, "gnn_model.pt")):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(self.model.state_dict(), path)
        print(f"Saved GNN model to {path}")

    def load(self, path=os.path.join(MODEL_DIR, "gnn_model.pt")):
        self.build_model()
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.eval()
        print(f"Loaded GNN model from {path}")
