import numpy as np
import random
import csv

# Simulation Parameters
TOLERANCE = 1e-4
REQUIRED_STABLE_CHECKS = 5
NUM_RUNS_PER_CONFIG = 1000

NODE_SIZES = [4, 8, 16, 32, 64, 128]
PACKET_LOSS_RATES = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]

MIN_DELAY_MS = 800
MAX_DELAY_MS = 1200
CHECK_INTERVAL_MS = 1000
MAX_SIMULATION_TIME_MS = 1500000

ACCEPTABLE_ERROR_THRESHOLD = 0.05
MIN_SENSOR_VAL = 10.0
MAX_SENSOR_VAL = 100.0

# Robus version parameters
MAX_RETRIES = 3 # max retries before giving up
TIMEOUT_MS = 200 # timeout for retry
ACK_RTT_MS = 10  # assumed RTT for a successful ACK

def simulation_loop(num_nodes, packet_loss):
    node_values = np.array([float(random.randint(int(MIN_SENSOR_VAL), int(MAX_SENSOR_VAL))) for _ in range(num_nodes)], dtype=float)
    node_weights = np.ones(num_nodes, dtype=float)
    true_mean = np.mean(node_values)
    initial_total_mass = np.sum(node_values)

    next_wake_up = np.random.uniform(0, MAX_DELAY_MS, num_nodes)

    # Robust state tracking 
    seq_nums = np.ones(num_nodes, dtype=int)
    last_seen_seq = np.zeros((num_nodes, num_nodes), dtype=int)

    current_time_ms = 0.0
    next_check_time = 0
    stability_counter = 0
    total_messages = 0  # Track all packets sent

    while current_time_ms < MAX_SIMULATION_TIME_MS:
        tx_node_id = np.argmin(next_wake_up)
        current_time_ms = next_wake_up[tx_node_id]

        # Check for convergence (i.e. all nodes have aprox. same value for a certain num of rounds)
        if current_time_ms >= next_check_time:
            estimates = np.where(node_weights > 1e-30, node_values / node_weights, 0.0)
            current_network_mean = np.mean(estimates)
            consensus_spread = np.max(np.abs(estimates - current_network_mean)) / abs(current_network_mean)

            if consensus_spread < TOLERANCE:
                stability_counter += 1
                if stability_counter >= REQUIRED_STABLE_CHECKS:
                    virtual_rounds = current_time_ms / ((MIN_DELAY_MS + MAX_DELAY_MS) / 2)
                    mean_rel_error = np.mean(np.abs(true_mean - estimates) / true_mean)
                    remaining_mass = np.sum(node_values)
                    return {
                        "converged": True,
                        "time_ms": current_time_ms,
                        "rounds": virtual_rounds,
                        "total_messages": total_messages,
                        "true_mean": true_mean,
                        "final_consensus_mean": current_network_mean,
                        "mean_rel_error": mean_rel_error,
                        "remaining_mass": remaining_mass,
                        "mass_loss_pct": 100.0 * (1.0 - remaining_mass / initial_total_mass)
                    }
            else:
                stability_counter = 0

            next_check_time = current_time_ms + CHECK_INTERVAL_MS

        # Robust Push-Sum logic
        rx_node_id = random.randint(0, num_nodes - 1)
        while rx_node_id == tx_node_id:
            rx_node_id = random.randint(0, num_nodes - 1)

        sent_val = node_values[tx_node_id] / 2.0
        sent_weight = node_weights[tx_node_id] / 2.0

        node_values[tx_node_id] -= sent_val
        node_weights[tx_node_id] -= sent_weight
        
        current_seq = seq_nums[tx_node_id]
        seq_nums[tx_node_id] += 1

        ack_received = False
        transaction_time_spent = 0

        # Retransmission logic
        for attempt in range(MAX_RETRIES + 1):
            total_messages += 1
            if random.random() >= packet_loss:
                # Packet arrived at Rx
                if current_seq > last_seen_seq[rx_node_id][tx_node_id]:
                    # Non-seen message, update local state
                    node_values[rx_node_id] += sent_val
                    node_weights[rx_node_id] += sent_weight
                    last_seen_seq[rx_node_id][tx_node_id] = current_seq
                
                # Rx sends ACK back
                total_messages += 1 
                if random.random() >= packet_loss:
                    # ACK arrived at Tx
                    ack_received = True
                    transaction_time_spent += ACK_RTT_MS
                    break
            
            # If packet or ACK dropped, timeout
            transaction_time_spent += TIMEOUT_MS

        # 
        if not ack_received:
            # Reached max retries without an ACK, restore local state
            node_values[tx_node_id] += sent_val
            node_weights[tx_node_id] += sent_weight

        # Schedule next gossip
        next_wake_up[tx_node_id] += transaction_time_spent + random.uniform(MIN_DELAY_MS, MAX_DELAY_MS)

    # Timeout (algorithm did not converge)
    estimates = np.where(node_weights > 1e-30, node_values / node_weights, 0.0)
    final_mean = np.mean(estimates)
    mean_rel_error = np.mean(np.abs(true_mean - estimates) / true_mean)
    remaining_mass = np.sum(node_values)

    return {
        "converged": False,
        "time_ms": MAX_SIMULATION_TIME_MS,
        "rounds": MAX_SIMULATION_TIME_MS / ((MIN_DELAY_MS + MAX_DELAY_MS) / 2),
        "total_messages": total_messages,
        "true_mean": true_mean,
        "final_consensus_mean": final_mean,
        "mean_rel_error": mean_rel_error,
        "remaining_mass": remaining_mass,
        "mass_loss_pct": 100.0 * (1.0 - remaining_mass / initial_total_mass)
    }

def run_experiments():
    output_filename = 'push_sum_robust_experiments.csv'
    total_configs = len(NODE_SIZES) * len(PACKET_LOSS_RATES)
    config_num = 0

    with open(output_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "num_nodes", "packet_loss", "run_id", "converged",
            "time_to_converge_ms", "virtual_rounds", "total_messages",
            "true_mean", "final_consensus_mean", "mean_relative_error",
            "within_5_percent_error", "remaining_mass", "mass_loss_pct"
        ])

        for num_nodes in NODE_SIZES:
            for packet_loss in PACKET_LOSS_RATES:
                config_num += 1
                print(f"[{config_num}/{total_configs}] Nodes={num_nodes}, Loss={packet_loss*100:.1f}%")

                for run_id in range(1, NUM_RUNS_PER_CONFIG + 1):
                    res = simulation_loop(num_nodes, packet_loss)
                    within_threshold = res["mean_rel_error"] <= ACCEPTABLE_ERROR_THRESHOLD

                    writer.writerow([
                        num_nodes, packet_loss, run_id, res["converged"],
                        res["time_ms"], res["rounds"], res["total_messages"],
                        res["true_mean"], res["final_consensus_mean"],
                        res["mean_rel_error"], within_threshold,
                        res["remaining_mass"], res["mass_loss_pct"]
                    ])

    print(f"\nSaved results to {output_filename}.")

if __name__ == "__main__":
    run_experiments()
