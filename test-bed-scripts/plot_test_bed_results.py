import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.figure(figsize=(8, 6))

DATA_PATH = Path("./logs_robust/")

# Dictionary for storing dataframe for each packet loss csv
results = {}

# Load data
for packet_loss_results in DATA_PATH.iterdir():
    packet_loss = int(packet_loss_results.stem)
    df = pd.read_csv(packet_loss_results / f"robust_summary_{packet_loss}_loss.csv")
    # Compute mean MRE, reliability and avg. traffic
    mre = df["MRE_Percent"].mean()
    reliability = (df["Acceptable"].mean())*100
    avg_traffic = df["Avg_Traffic"].mean()
    data = [mre, reliability, avg_traffic]
    # Append to dict
    results[packet_loss] = data

# Plot
packet_loss_values = sorted(results.keys())
print(packet_loss_values)
mre_values = [results[key][0] for key in packet_loss_values]
reliability_values = [results[key][1] for key in packet_loss_values]
traffic_values = [results[key][2] for key in packet_loss_values]

## PLOT MRE 
plt.plot(packet_loss_values, mre_values, marker='s', color='b', label=f'4 Nodes')
plt.xlabel('Packet Loss (%)')
# plt.yscale("log")
plt.ylabel('Mean Relative Error (%)')
plt.ylim(0, 10)
plt.axhline(y=5.0, color='black', linestyle=':', label='5% Threshold')
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig("robust_mre_testbed.png")
plt.close()

## PLOT RELIABILITY
plt.plot(packet_loss_values, reliability_values, marker='^', color='b', label=f'4 Nodes')
plt.xlabel('Packet Loss (%)')
# plt.yscale("log")
plt.ylabel('Success Rate (%)')
plt.ylim(-5, 105)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig("robust_reliability_testbed.png")
plt.close()

## PLOT TRAFFIC 
plt.plot(packet_loss_values, traffic_values, marker='D', color='b', label=f'4 Nodes')
plt.xlabel('Packet Loss (%)')
# plt.yscale("log")
plt.ylabel('Avg. Messages per Node')
plt.ylim([0, 73])
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig("robust_traffic_testbed.png")
plt.close()

