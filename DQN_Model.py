## Design Basic DQN using Pytorch
## Experience Replay
## Clip Rewards
## Train for ieee-2 and ieee-4

import torch.nn as nn
import torch.nn.functional as F

class ieee4_net(nn.Module):
    def __init__(self, in_channels=4, num_actions=200):

        super(ieee4_net, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, 8, kernel_size=3, stride=1,padding =1)
        self.conv2 = nn.Conv2d(8, 16, kernel_size=4, stride=2)
        self.conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=1)
        self.fc4 = nn.Linear(7 * 7 * 64, 512)
        self.fc5 = nn.Linear(512, num_actions)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.fc4(x.view(x.size(0), -1)))
        return self.fc5(x)

class ieee2_net(nn.Module):
    def __init__(self, inputs, num_actions,p=0.3):
        super(ieee2_net, self).__init__()
        self.fc1 = nn.Linear(inputs, 24);
        self.fc2 = nn.Linear(24, 36);
        self.fc3 = nn.Linear(36, 72);
        self.fc4 = nn.Linear(72, num_actions)
        self.drop_layer = nn.Dropout(p=p)

    def forward(self, x):
        x = F.relu(self.fc1(x));
        x = F.relu(self.fc2(x));
        x=self.drop_layer(x);
        x = F.relu(self.fc3(x));
        return self.fc4(x);
