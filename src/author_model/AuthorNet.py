import torch
import torch.nn as nn
import torch.nn.functional as F

import numpy as np

# Define a network.
class AuthorNet(nn.Module):
    
    # We're using a dataset as an argument to get the input size.
    def __init__(self, nontext_size, output_size, vocab):
        
        super(AuthorNet, self).__init__()
        
        #big_embed = torch.cat((embeddings.vectors, torch.normal(0, 1, (2, 200))))
        #self.emb = nn.Embedding.from_pretrained(big_embed)
        self.emb = nn.Embedding(len(vocab), 200)

        self.nontext_input_size = nontext_size # 24
        self.output_size = output_size # 11

        self.conv1 = nn.Conv1d(200, 64, kernel_size = 3, padding = 1)
        self.pool1 = nn.MaxPool1d(kernel_size = 3, padding = 1)
        self.bn1 = nn.BatchNorm1d(64)
        self.conv2 = nn.Conv1d(64, 128, kernel_size = 3, padding = 1)
        self.pool2 = nn.MaxPool1d(kernel_size = 3, padding = 1)
        self.bn2 = nn.BatchNorm1d(128)
        self.conv3 = nn.Conv1d(128, 256, kernel_size = 3, padding = 1)
        self.global_avg_pool = nn.AdaptiveAvgPool1d(8)
        self.bn3 = nn.BatchNorm1d(256)

        self.fc_1 = nn.Linear((256 * 8) + self.nontext_input_size, self.output_size)

    def forward(self, text, nontext):

        batch_size = text.shape[0]

        x = self.emb(text)
        # y tho
        x = x.permute(0, 2, 1)
        x = F.relu(self.conv1(x))
        x = self.pool1(x)
        x = self.bn1(x)
        x = F.relu(self.conv2(x))
        x = self.pool2(x)
        x = self.bn2(x)
        x = F.relu(self.conv3(x))
        x = self.global_avg_pool(x)
        x = self.bn3(x)
        x = x.reshape((batch_size, -1))
        # Concat Nontext and 
        x = F.dropout(torch.cat((x, nontext), dim = 1), p = 0.2, training = self.training)
        x = self.fc_1(x) # No softmax here
        return x

    def num_params(self):

        model_parameters = filter(lambda p: p.requires_grad, self.parameters())
        params = sum([np.prod(p.size()) for p in model_parameters])
        return params

    def unfreeze_embeddings(self):
        self.emb.weight.requires_grad = True

    def freeze_embeddings(self):
        self.emb.weight.requires_grad = False