import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from tqdm import tqdm


class Encoder(nn.Module):
    def __init__(self, input_dim, hidden_dims, latent_dim):
        super(Encoder, self).__init__()
        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.1))
            prev_dim = hidden_dim

        layers.append(nn.Linear(prev_dim, latent_dim))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


class Decoder(nn.Module):
    def __init__(self, latent_dim, hidden_dims, output_dim):
        super(Decoder, self).__init__()
        layers = []
        prev_dim = latent_dim

        for hidden_dim in reversed(hidden_dims):
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.1))
            prev_dim = hidden_dim

        layers.append(nn.Linear(prev_dim, output_dim))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


class Autoencoder(nn.Module):
    def __init__(self, input_dim, hidden_dims=[64, 32], latent_dim=16):
        super(Autoencoder, self).__init__()
        self.encoder = Encoder(input_dim, hidden_dims, latent_dim)
        self.decoder = Decoder(latent_dim, hidden_dims, input_dim)

    def forward(self, x):
        z = self.encoder(x)
        x_recon = self.decoder(z)
        return x_recon, z


class AutoencoderTrainer:
    def __init__(self, input_dim, hidden_dims=[64, 32], latent_dim=16,
                 learning_rate=1e-3, device='cpu'):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.model = Autoencoder(input_dim, hidden_dims, latent_dim).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()
        self.is_trained = False
        self.reconstruction_errors = None

    def train(self, data, epochs=100, batch_size=32, verbose=True):
        self.model.train()

        if isinstance(data, np.ndarray):
            data = torch.FloatTensor(data)

        dataset = TensorDataset(data)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        losses = []
        progress_bar = tqdm(range(epochs), disable=not verbose)

        for epoch in progress_bar:
            epoch_loss = 0
            for batch in dataloader:
                x = batch[0].to(self.device)

                self.optimizer.zero_grad()
                x_recon, _ = self.model(x)
                loss = self.criterion(x_recon, x)
                loss.backward()
                self.optimizer.step()

                epoch_loss += loss.item()

            avg_loss = epoch_loss / len(dataloader)
            losses.append(avg_loss)

            if verbose:
                progress_bar.set_description(f'Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.6f}')

        self.is_trained = True
        return losses

    def get_reconstruction_errors(self, data):
        self.model.eval()

        if isinstance(data, np.ndarray):
            data = torch.FloatTensor(data).to(self.device)

        with torch.no_grad():
            x_recon, _ = self.model(data)
            errors = torch.mean((data - x_recon) ** 2, dim=1).cpu().numpy()

        return errors

    def get_latent_representations(self, data):
        self.model.eval()

        if isinstance(data, np.ndarray):
            data = torch.FloatTensor(data).to(self.device)

        with torch.no_grad():
            _, z = self.model(data)

        return z.cpu().numpy()

    def save_model(self, path):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict()
        }, path)

    def load_model(self, path):
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.is_trained = True
