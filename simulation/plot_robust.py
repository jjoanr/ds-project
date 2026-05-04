import pandas as pd
import matplotlib.pyplot as plt

# Load the simulation results
DATA_FILE = 'push_sum_robust_experiments.csv'
try:
    df = pd.read_csv(DATA_FILE)
except FileNotFoundError:
    print(f"Error: Could not find '{DATA_FILE}'. Ensure it is in the same directory.")
    exit()

# Summary Statistics
summary = df.groupby(['num_nodes', 'packet_loss']).agg(
    convergence_rate=('converged', 'mean'),
    avg_error=('mean_relative_error', 'mean'),
    success_within_5pct=('within_5pct_of_true', 'mean'),
    avg_mass_loss_pct=('mass_loss_pct', 'mean'),
    avg_traffic=('total_messages', 'mean')
).reset_index()

# Format columns for console output
print_summary = summary.copy()
print_summary['conv_rate'] = (print_summary['convergence_rate'] * 100).round(1).astype(str) + '%'
print_summary['reliability'] = (print_summary['success_within_5pct'] * 100).round(1).astype(str) + '%'
print_summary['avg_error_pct'] = (print_summary['avg_error'] * 100).round(2).astype(str) + '%'
print_summary['avg_traffic'] = print_summary['avg_traffic'].round(0).astype(int)
print_summary['mass_lost'] = print_summary['avg_mass_loss_pct'].round(1).astype(str) + '%'

cols_to_show = ['num_nodes', 'packet_loss', 'conv_rate', 'reliability', 'avg_error_pct', 'avg_traffic', 'mass_lost']
print(print_summary[cols_to_show].to_string(index=False))

print("\nGenerating plots...")

# Plotting setup
node_sizes = sorted(df['num_nodes'].unique())
colors = ['b', 'g', 'r', 'c', 'm', 'orange'] 

# ---------------------------------------------------------
# Plot A: Mean Relative Error (%) vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(8, 6))
for idx, size in enumerate(node_sizes):
    data = summary[summary['num_nodes'] == size]
    plt.plot(data['packet_loss'] * 100, data['avg_error'] * 100, marker='s',
             color=colors[idx % len(colors)], label=f'{size} Nodes')

plt.axhline(y=5.0, color='black', linestyle=':', label='5% Threshold')
plt.xlabel('Packet Loss (%)')
plt.ylabel('Mean Relative Error (%)')
plt.grid(True, which="both", linestyle='--', alpha=0.4)
plt.ylim(0, 10)
plt.legend()
plt.tight_layout()
plt.savefig('push_sum_robust_accuracy.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot B: Reliability (Runs within 5% threshold) vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(8, 6))
for idx, size in enumerate(node_sizes):
    data = summary[summary['num_nodes'] == size]
    plt.plot(data['packet_loss'] * 100, data['success_within_5pct'] * 100, marker='^',
             color=colors[idx % len(colors)], label=f'{size} Nodes')

plt.xlabel('Packet Loss (%)')
plt.ylabel('Success Rate (%)')
plt.ylim(-5, 105)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig('push_sum_robust_reliability.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot C: Network Traffic Generated vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(8, 6))
for idx, size in enumerate(node_sizes):
    data = summary[summary['num_nodes'] == size]
    plt.plot(data['packet_loss'] * 100, data['avg_traffic'] / size, marker='D',
             color=colors[idx % len(colors)], label=f'{size} Nodes')

plt.xlabel('Packet Loss (%)')
plt.ylabel('Average Messages per Node')
plt.grid(True, linestyle='--', alpha=0.6)
# traffic ylim removed so matplotlib can autoscale high traffic volumes
plt.legend()
plt.tight_layout()
# plt.yscale("log")
plt.savefig('push_sum_robust_traffic.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot D: Mass Deviation (%) vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(8, 6))
for idx, size in enumerate(node_sizes):
    data = summary[summary['num_nodes'] == size]
    plt.plot(data['packet_loss'] * 100, data['avg_mass_loss_pct'], marker='x',
             color=colors[idx % len(colors)], label=f'{size} Nodes')

plt.axhline(y=0.0, color='black', linestyle=':', label='Perfect Conservation')
plt.xlabel('Packet Loss (%)')
plt.ylabel('Mass Conservation Error (%)')
plt.ylabel('Average Mass Loss (%)')
plt.ylim(-5, 105)
plt.legend()
plt.tight_layout()
plt.savefig('push_sum_robust_mass_deviation.png', dpi=300)
plt.close()
