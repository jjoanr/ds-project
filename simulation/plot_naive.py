import pandas as pd
import matplotlib.pyplot as plt

# Load the simulation results
DATA_FILE = 'push_sum_naive_experiments.csv'
try:
    df = pd.read_csv(DATA_FILE)
except FileNotFoundError:
    print(f"Error: Could not find '{DATA_FILE}'. Ensure it is in the same directory.")
    exit()

print("--- Aligned Asynchronous Push-Sum Analysis ---\n")

# 1. Generate Summary Statistics
summary = df.groupby(['num_nodes', 'packet_loss']).agg(
    convergence_rate=('converged', 'mean'),
    avg_error=('mean_relative_error', 'mean'),
    success_within_5pct=('within_5_percent_error', 'mean'),
    avg_mass_loss_pct=('mass_loss_pct', 'mean'),
    avg_traffic=('total_unicasts', 'mean') # <--- ADDED TRAFFIC
).reset_index()

# Filter for converged runs only for time/rounds stats
converged_only = df[df['converged'] == True]
time_rounds_summary = converged_only.groupby(['num_nodes', 'packet_loss']).agg(
    avg_time_s=('time_to_converge_ms', lambda x: x.mean() / 1000.0),
    avg_virtual_rounds=('virtual_rounds', 'mean')
).reset_index()

# Merge back into the main summary
summary = pd.merge(summary, time_rounds_summary, on=['num_nodes', 'packet_loss'], how='left')

# Format columns for console output
print_summary = summary.copy()
print_summary['conv_rate'] = (print_summary['convergence_rate'] * 100).round(1).astype(str) + '%'
print_summary['reliability'] = (print_summary['success_within_5pct'] * 100).round(1).astype(str) + '%'
print_summary['avg_error'] = (print_summary['avg_error'] * 100).round(2).astype(str) + '%'
print_summary['avg_sec'] = print_summary['avg_time_s'].round(1)
print_summary['mass_lost'] = print_summary['avg_mass_loss_pct'].round(1).astype(str) + '%'

cols_to_show = ['num_nodes', 'packet_loss', 'conv_rate', 'reliability', 'avg_error', 'avg_sec', 'mass_lost']
print(print_summary[cols_to_show].to_string(index=False))

print("\nGenerating separate plots...")

# 2. Plotting Setup
node_sizes = sorted(df['num_nodes'].unique())
colors = ['b', 'g', 'r', 'c', 'm', 'gray', 'k'] # Added extra colors just in case

# ---------------------------------------------------------
# Plot A: Average Time to Converge (Seconds) vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(8, 6))
for idx, size in enumerate(node_sizes):
    data = time_rounds_summary[time_rounds_summary['num_nodes'] == size]
    plt.plot(data['packet_loss'] * 100, data['avg_time_s'], marker='o',
             color=colors[idx % len(colors)], label=f'{size} Nodes')

plt.xlabel('Packet Loss (%)')
plt.ylabel('Avg. Seconds to Converge')
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig('push_sum_naive_time.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot B: Mean Relative Error (%) vs Packet Loss
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
plt.legend()
plt.ylim(0, 10)
plt.tight_layout()
plt.savefig('push_sum_naive_accuracy.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot C: Reliability (Runs within 5% threshold) vs Packet Loss
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
plt.savefig('push_sum_naive_reliability.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot D: Mass Conservation Error (%) vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(8, 6))
for idx, size in enumerate(node_sizes):
    data = summary[summary['num_nodes'] == size]
    plt.plot(data['packet_loss'] * 100, data['avg_mass_loss_pct'], marker='x',
             color=colors[idx % len(colors)], label=f'{size} Nodes')

plt.axhline(y=0.0, color='black', linestyle=':', label='Perfect Conservation')
plt.xlabel('Packet Loss (%)')
plt.ylabel('Mass Conservation Error (%)')
plt.ylim(-5, 105) # Naive only loses mass, so it goes from 0 up to 100
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig('push_sum_naive_mass_error.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot E: Network Traffic Generated vs Packet Loss (NAIVE)
# ---------------------------------------------------------
plt.figure(figsize=(8, 6))
for idx, size in enumerate(node_sizes):
    data = summary[summary['num_nodes'] == size]
    plt.plot(data['packet_loss'] * 100, data['avg_traffic'] / size, marker='D',
             color=colors[idx % len(colors)], label=f'{size} Nodes')

plt.xlabel('Packet Loss (%)')
plt.ylabel('Average Messages per Node')
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()
plt.ylim(0, 150) # Locked to match the max of the Robust script 
plt.tight_layout()
plt.savefig('push_sum_naive_traffic.png', dpi=300)
plt.close()

print("All 5 plots saved successfully in the current directory.")
