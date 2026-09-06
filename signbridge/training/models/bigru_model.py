import torch
import torch.nn as nn

class BiGRUModel(nn.Module):
    def __init__(self,
                 input_size = 258,
                 hidden_size = 128,
                 num_layers = 2,
                 num_classes = 61,
                 dropout = 0.3):

        super().__init__()

        self.bigru = nn.GRU(
            input_size = input_size,
            hidden_size = hidden_size,
            num_layers = num_layers,
            batch_first = True,
            bidirectional = True,
            dropout = dropout
        )

        self.dropout = nn.Dropout(dropout)

        self.fc = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x):
        output, hidden = self.bigru(x)
        last_output = output[:,-1,:]

        last_output = self.dropout(last_output)
        logits = self.fc(last_output)

        return logits


