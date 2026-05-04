import pandas as pd
import matplotlib.pyplot as plt

NAIVE_FILE = 'push_sum_naive_experiments.csv'
ROBUST_FILE = 'push_sum_robust_experiments.csv'

def load_and_summarize(filepath):
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"Warning: Could not find '{filepath}'. Make sure it is in the same directory.")
        return pd.DataFrame(), pd.DataFrame()

    # Handle the different traffic column names between naive and robust CSVs
    traffic_col = 'total_unicasts' if 'total_unicasts' in df.columns else 'total_messages'

    summary = df.groupby(['num_nodes', 'packet_loss']).agg(
        convergence_rate=('converged', 'mean'),
        avg_error=('mean_relative_error', 'mean'),
        success_within_5pct=('within_5pct_of_true', 'mean'),
        avg_mass_loss_pct=('mass_loss_pct', 'mean'),
        avg_traffic=(traffic_col, 'mean')
    ).reset_index()
    
    return df, summary

def print_console_summary(summary, algo_name):
    if summary.empty: return
    print(f"\n--- {algo_name.upper()} SUMMARY ---")
    print_summary = summary.copy()
    print_summary['conv_rate'] = (print_summary['convergence_rate'] * 100).round(1).astype(str) + '%'
    print_summary['reliability'] = (print_summary['success_within_5pct'] * 100).round(1).astype(str) + '%'
    print_summary['avg_error_pct'] = (print_summary['avg_error'] * 100).round(2).astype(str) + '%'
    print_summary['mass_lost'] = print_summary['avg_mass_loss_pct'].round(1).astype(str) + '%'
    print_summary['avg_msgs_per_node'] = (print_summary['avg_traffic'] / print_summary['num_nodes']).round(1)

    cols_to_show = ['num_nodes', 'packet_loss', 'conv_rate', 'reliability', 'avg_error_pct', 'mass_lost', 'avg_msgs_per_node']
    print(print_summary[cols_to_show].to_string(index=False))

# Load data
df_naive, summary_naive = load_and_summarize(NAIVE_FILE)
df_robust, summary_robust = load_and_summarize(ROBUST_FILE)

print_console_summary(summary_naive, "Naive")
print_console_summary(summary_robust, "Robust")

print("\nGenerating simulation plots...")

# Determine node sizes
node_sizes = set()
if not summary_naive.empty: node_sizes.update(summary_naive['num_nodes'].unique())
if not summary_robust.empty: node_sizes.update(summary_robust['num_nodes'].unique())
node_sizes = sorted(list(node_sizes))

colors = ['b', 'g', 'r', 'c', 'm', 'orange', 'purple', 'brown']

# ---------------------------------------------------------
# Plot A: Mean Relative Error (%) vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(9, 6))
for idx, size in enumerate(node_sizes):
    color = colors[idx % len(colors)]
    
    if not summary_naive.empty and size in summary_naive['num_nodes'].values:
        data_n = summary_naive[summary_naive['num_nodes'] == size]
        plt.plot(data_n['packet_loss'] * 100, data_n['avg_error'] * 100, marker='s',
                 color=color, linestyle='--', markerfacecolor='none', label=f'Naive - {size} Nodes')
                 
    if not summary_robust.empty and size in summary_robust['num_nodes'].values:
        data_r = summary_robust[summary_robust['num_nodes'] == size]
        plt.plot(data_r['packet_loss'] * 100, data_r['avg_error'] * 100, marker='s',
                 color=color, linestyle='-', label=f'Robust - {size} Nodes')

plt.axhline(y=5.0, color='black', linestyle=':', label='5% Threshold')
plt.xlabel('Packet Loss (%)')
plt.ylabel('Mean Relative Error (%)')
plt.grid(True, which="both", linestyle='--', alpha=0.4)
plt.legend(ncol=2, fontsize='small', handlelength=4.0, handletextpad=1.0)
plt.ylim(0, 10)
plt.tight_layout()
plt.savefig('unified_sim_accuracy.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot B: Reliability (% runs within 5% error) vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(9, 6))
for idx, size in enumerate(node_sizes):
    color = colors[idx % len(colors)]
    
    if not summary_naive.empty and size in summary_naive['num_nodes'].values:
        data_n = summary_naive[summary_naive['num_nodes'] == size]
        plt.plot(data_n['packet_loss'] * 100, data_n['success_within_5pct'] * 100, marker='^',
                 color=color, linestyle='--', markerfacecolor='none', label=f'Naive - {size} Nodes')
                 
    if not summary_robust.empty and size in summary_robust['num_nodes'].values:
        data_r = summary_robust[summary_robust['num_nodes'] == size]
        plt.plot(data_r['packet_loss'] * 100, data_r['success_within_5pct'] * 100, marker='^',
                 color=color, linestyle='-', label=f'Robust - {size} Nodes')

plt.xlabel('Packet Loss (%)')
plt.ylabel('Success Rate (%)')
plt.ylim(-5, 105)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(ncol=2, fontsize='small', handlelength=4.0, handletextpad=1.0)
plt.tight_layout()
plt.savefig('unified_sim_reliability.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot C: Network Traffic (avg messages per node) vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(9, 6))
for idx, size in enumerate(node_sizes):
    color = colors[idx % len(colors)]
    
    if not summary_naive.empty and size in summary_naive['num_nodes'].values:
        data_n = summary_naive[summary_naive['num_nodes'] == size]
        plt.plot(data_n['packet_loss'] * 100, data_n['avg_traffic'] / size, marker='D',
                 color=color, linestyle='--', markerfacecolor='none', label=f'Naive - {size} Nodes')
                 
    if not summary_robust.empty and size in summary_robust['num_nodes'].values:
        data_r = summary_robust[summary_robust['num_nodes'] == size]
        plt.plot(data_r['packet_loss'] * 100, data_r['avg_traffic'] / size, marker='D',
                 color=color, linestyle='-', label=f'Robust - {size} Nodes')

plt.xlabel('Packet Loss (%)')
plt.ylabel('Avg. Messages per Node (Log Scale)')
plt.yscale('log')
# plt.ylim(bottom=0)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(ncol=2, fontsize='small', handlelength=4.0, handletextpad=1.0)
plt.tight_layout()
plt.savefig('unified_sim_traffic.png', dpi=300)
plt.close()

# ---------------------------------------------------------
# Plot D: Mass Loss (%) vs Packet Loss
# ---------------------------------------------------------
plt.figure(figsize=(9, 6))
for idx, size in enumerate(node_sizes):
    color = colors[idx % len(colors)]
    
    if not summary_naive.empty and size in summary_naive['num_nodes'].values:
        data_n = summary_naive[summary_naive['num_nodes'] == size]
        plt.plot(data_n['packet_loss'] * 100, data_n['avg_mass_loss_pct'], marker='o',
                 color=color, linestyle='--', markerfacecolor='none', label=f'Naive - {size} Nodes')
                 
    if not summary_robust.empty and size in summary_robust['num_nodes'].values:
        data_r = summary_robust[summary_robust['num_nodes'] == size]
        plt.plot(data_r['packet_loss'] * 100, data_r['avg_mass_loss_pct'], marker='o',
                 color=color, linestyle='-', label=f'Robust - {size} Nodes')

plt.axhline(y=0.0, color='black', linestyle=':', label='Perfect Conservation')
plt.xlabel('Packet Loss (%)')
plt.ylabel('Average Mass Loss (%)')
plt.ylim(-5, 105)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(ncol=2, fontsize='small', handlelength=4.0, handletextpad=1.0)
plt.tight_layout()
plt.savefig('unified_sim_mass_loss.png', dpi=300)
plt.close()
