import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DATA_PATH = Path("./logs/")

# Load data from path to dictionary
def load_data(data_path, data_dict, algo_type):
    if not data_path.exists():
        print(f"Warning: Path {data_path} not found. Skipping.")
        return

    for packet_loss_results in data_path.iterdir():
        if not packet_loss_results.is_dir(): 
            continue
        
        packet_loss = int(packet_loss_results.stem)
        csv_file = packet_loss_results / f"{algo_type}_summary_{packet_loss}_loss.csv"
        
        if csv_file.exists():
            df = pd.read_csv(csv_file)
            # Compute mean MRE, reliability and avg. traffic
            mre = df["MRE_Percent"].mean()
            reliability = (df["Acceptable"].mean()) * 100
            avg_traffic = df["Avg_Traffic"].mean()
            data = [mre, reliability, avg_traffic]
            # Append to dict
            data_dict[packet_loss] = data

# Helper function to extract sorted lists for plotting
def extract_plot_data(data_dict, metric_index):
    packet_loss_values = sorted(data_dict.keys())
    metric_values = [data_dict[key][metric_index] for key in packet_loss_values]
    return packet_loss_values, metric_values

# Plot
def plot_unified_results(naive_4, naive_8, robust_4, robust_8):
    # Metric Indices: 0 = MRE, 1 = Reliability, 2 = Traffic
    ## PLOT MRE
    plt.figure(figsize=(8, 6))
    pl_n4, mre_n4 = extract_plot_data(naive_4, 0)
    pl_n8, mre_n8 = extract_plot_data(naive_8, 0)
    pl_r4, mre_r4 = extract_plot_data(robust_4, 0)
    pl_r8, mre_r8 = extract_plot_data(robust_8, 0)

    plt.plot(pl_n4, mre_n4, marker='s', color='b', linestyle='--', markerfacecolor='none', label='Naive - 4 Nodes')
    plt.plot(pl_n8, mre_n8, marker='s', color='g', linestyle='--', markerfacecolor='none', label='Naive - 8 Nodes')
    plt.plot(pl_r4, mre_r4, marker='s', color='b', linestyle='-', label='Robust - 4 Nodes')
    plt.plot(pl_r8, mre_r8, marker='s', color='g', linestyle='-', label='Robust - 8 Nodes')
    
    plt.xlabel('Packet Loss (%)')
    plt.ylabel('Mean Relative Error (%)')
    plt.ylim(0, 10)
    plt.axhline(y=5.0, color='black', linestyle=':', label='5% Threshold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(handlelength=4.0, handletextpad=1.0)
    plt.tight_layout()
    plt.savefig("unified_mre_testbed.png")
    plt.close()

    ## PLOT RELIABILITY
    plt.figure(figsize=(8, 6))
    pl_n4, rel_n4 = extract_plot_data(naive_4, 1)
    pl_n8, rel_n8 = extract_plot_data(naive_8, 1)
    pl_r4, rel_r4 = extract_plot_data(robust_4, 1)
    pl_r8, rel_r8 = extract_plot_data(robust_8, 1)

    plt.plot(pl_n4, rel_n4, marker='^', color='b', linestyle='--', markerfacecolor='none', label='Naive - 4 Nodes')
    plt.plot(pl_n8, rel_n8, marker='^', color='g', linestyle='--', markerfacecolor='none', label='Naive - 8 Nodes')
    plt.plot(pl_r4, rel_r4, marker='^', color='b', linestyle='-', label='Robust - 4 Nodes')
    plt.plot(pl_r8, rel_r8, marker='^', color='g', linestyle='-', label='Robust - 8 Nodes')
    
    plt.xlabel('Packet Loss (%)')
    plt.ylabel('Success Rate (%)')
    plt.ylim(-5, 105)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(handlelength=4.0, handletextpad=1.0)
    plt.tight_layout()
    plt.savefig("unified_reliability_testbed.png")
    plt.close()

    ## PLOT TRAFFIC
    plt.figure(figsize=(8, 6))
    pl_n4, trf_n4 = extract_plot_data(naive_4, 2)
    pl_n8, trf_n8 = extract_plot_data(naive_8, 2)
    pl_r4, trf_r4 = extract_plot_data(robust_4, 2)
    pl_r8, trf_r8 = extract_plot_data(robust_8, 2)

    plt.plot(pl_n4, trf_n4, marker='D', color='b', linestyle='--', markerfacecolor='none', label='Naive - 4 Nodes')
    plt.plot(pl_n8, trf_n8, marker='D', color='g', linestyle='--', markerfacecolor='none', label='Naive - 8 Nodes')
    plt.plot(pl_r4, trf_r4, marker='D', color='b', linestyle='-', label='Robust - 4 Nodes')
    plt.plot(pl_r8, trf_r8, marker='D', color='g', linestyle='-', label='Robust - 8 Nodes')
    
    plt.xlabel('Packet Loss (%)')
    plt.ylabel('Avg. Messages per Node')
    plt.ylim(bottom=0) 
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(handlelength=4.0, handletextpad=1.0)
    plt.tight_layout()
    plt.savefig("unified_traffic_testbed.png")
    plt.close()

if __name__ == "__main__":
    # Dictionaries to store dataframe data
    naive_4_node = {}
    naive_8_node = {}
    robust_4_node = {}
    robust_8_node = {}

    # Paths
    N_FOUR_PATH = DATA_PATH / "logs_naive-4-node"
    N_EIGHT_PATH = DATA_PATH / "logs_naive-8-node"
    R_FOUR_PATH = DATA_PATH / "logs_robust-4-node"
    R_EIGHT_PATH = DATA_PATH / "logs_robust-8-node"

    # Load data for both algorithms and sizes
    load_data(N_FOUR_PATH, naive_4_node, "naive")
    load_data(N_EIGHT_PATH, naive_8_node, "naive")
    load_data(R_FOUR_PATH, robust_4_node, "robust")
    load_data(R_EIGHT_PATH, robust_8_node, "robust")

    # Generate unified plots
    plot_unified_results(naive_4_node, naive_8_node, robust_4_node, robust_8_node)
