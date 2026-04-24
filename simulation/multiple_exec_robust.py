import numpy as np
import csv

# Simulation Parameters
TOLERANCE = 1e-4
REQUIRED_STABLE_CHECKS = 5
NUM_RUNS_PER_CONFIG = 100

NODE_SIZES = [4, 8, 16, 32, 64, 128]
PACKET_LOSS_RATES = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]

MIN_DELAY_MS = 800
MAX_DELAY_MS = 1200
CHECK_INTERVAL_MS = 1000
MAX_SIMULATION_TIME_MS = 5000000

ACCEPTABLE_ERROR_THRESHOLD = 0.05
MIN_SENSOR_VAL = 10.0
MAX_SENSOR_VAL = 100.0

WEIGHT_FLOOR = 1e-30
HARDWARE_UNDERFLOW_LIMIT = 1e-15

def simulation_loop(num_nodes, packet_loss, rng: np.random.Generator):
    node_values = rng.integers(int(MIN_SENSOR_VAL), int(MAX_SENSOR_VAL) + 1, size=num_nodes).astype(float)
    node_weights = np.ones(num_nodes, dtype=float)

    true_mean = np.mean(node_values)
    initial_total_mass = np.sum(node_values)

    next_wake_up = rng.uniform(0, MAX_DELAY_MS, num_nodes)

    # Robust tracking tables
    # rows: sender (tx), cols: receiver (rx)
    cum_sent_val = np.zeros((num_nodes, num_nodes), dtype=float)
    cum_sent_weight = np.zeros((num_nodes, num_nodes), dtype=float)
    
    cum_rcvd_val = np.zeros((num_nodes, num_nodes), dtype=float)
    cum_rcvd_weight = np.zeros((num_nodes, num_nodes), dtype=float)

    current_time_ms = 0.0
    next_check_time = 0.0
    stability_counter = 0
    total_messages = 0

    while current_time_ms < MAX_SIMULATION_TIME_MS:
        tx_node_id = int(np.argmin(next_wake_up))
        current_time_ms = next_wake_up[tx_node_id]

        # Convergence check
        if current_time_ms >= next_check_time:
            # Check for float precision overflow (esp uses float32)
            if np.any(node_weights < HARDWARE_UNDERFLOW_LIMIT):
                return {
                    "converged": False,
                    "total_messages": total_messages,
                    "true_mean": true_mean,
                    "final_consensus_mean": float('inf'),
                    "mean_rel_error": float('inf'),
                    "remaining_mass": np.sum(node_values),
                    "mass_loss_pct": 100.0 * (1.0 - np.sum(node_values) / initial_total_mass)
                }

            estimates = np.where(node_weights > WEIGHT_FLOOR, node_values / node_weights, 0.0)
            current_network_mean = np.mean(estimates)

            if abs(current_network_mean) > WEIGHT_FLOOR:
                consensus_spread = np.max(np.abs(estimates - current_network_mean)) / abs(current_network_mean)
            else:
                consensus_spread = float('inf')

            if consensus_spread < TOLERANCE:
                stability_counter += 1
                if stability_counter >= REQUIRED_STABLE_CHECKS:
                    mean_rel_error = np.mean(np.abs(true_mean - estimates) / true_mean)
                    
                    in_transit_mass = np.sum(cum_sent_val - cum_rcvd_val)
                    current_total_mass = np.sum(node_values) + in_transit_mass
                    
                    return {
                        "converged": True,
                        "total_messages": total_messages,
                        "true_mean": true_mean,
                        "final_consensus_mean": current_network_mean,
                        "mean_rel_error": mean_rel_error,
                        "remaining_mass": current_total_mass,
                        "mass_loss_pct": 100.0 * (1.0 - current_total_mass / initial_total_mass)
                    }
            else:
                stability_counter = 0

            next_check_time = current_time_ms + CHECK_INTERVAL_MS

        # Robust Flow Gossip logic
        rx_node_id = int(rng.integers(0, num_nodes))
        while rx_node_id == tx_node_id:
            rx_node_id = int(rng.integers(0, num_nodes))

        # Halve the mass and weight locally
        sent_val = node_values[tx_node_id] / 2.0
        sent_weight = node_weights[tx_node_id] / 2.0

        node_values[tx_node_id] -= sent_val
        node_weights[tx_node_id] -= sent_weight

        # Add to cumulative sent table
        cum_sent_val[tx_node_id, rx_node_id] += sent_val
        cum_sent_weight[tx_node_id, rx_node_id] += sent_weight

        total_messages += 1  # 1 message per interaction

        # Transmission with probabilistic packet loss
        if rng.random() >= packet_loss:
            # Reception: calculate delta from what was previously successfully received
            received_cum_val = cum_sent_val[tx_node_id, rx_node_id]
            received_cum_weight = cum_sent_weight[tx_node_id, rx_node_id]

            delta_val = received_cum_val - cum_rcvd_val[tx_node_id, rx_node_id]
            delta_weight = received_cum_weight - cum_rcvd_weight[tx_node_id, rx_node_id]

            # Apply the delta and update local receive tables 
            node_values[rx_node_id] += delta_val
            node_weights[rx_node_id] += delta_weight

            cum_rcvd_val[tx_node_id, rx_node_id] = received_cum_val
            cum_rcvd_weight[tx_node_id, rx_node_id] = received_cum_weight

        next_wake_up[tx_node_id] += rng.uniform(MIN_DELAY_MS, MAX_DELAY_MS)

    # Timeout 
    estimates = np.where(node_weights > WEIGHT_FLOOR, node_values / node_weights, 0.0)
    mean_rel_error = np.mean(np.abs(true_mean - estimates) / true_mean)
    
    in_transit_mass = np.sum(cum_sent_val - cum_rcvd_val)
    current_total_mass = np.sum(node_values) + in_transit_mass

    return {
        "converged": False,
        "total_messages": total_messages,
        "true_mean": true_mean,
        "final_consensus_mean": np.mean(estimates),
        "mean_rel_error": mean_rel_error,
        "remaining_mass": current_total_mass,
        "mass_loss_pct": 100.0 * (1.0 - current_total_mass / initial_total_mass)
    }

def run_experiments(seed: int = 42):
    output_filename = 'push_sum_robust_experiments.csv'
    total_configs = len(NODE_SIZES) * len(PACKET_LOSS_RATES)
    config_num = 0

    rng = np.random.default_rng(seed)

    print(f"Starting experiments: {total_configs} configurations x {NUM_RUNS_PER_CONFIG} runs = "
          f"{total_configs * NUM_RUNS_PER_CONFIG} total simulations.\n")

    with open(output_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "num_nodes", "packet_loss", "run_id",
            "converged", "total_messages",
            "true_mean", "final_consensus_mean",
            "mean_relative_error", "within_5pct_of_true",
            "remaining_mass", "mass_loss_pct"
        ])

        for num_nodes in NODE_SIZES:
            for packet_loss in PACKET_LOSS_RATES:
                config_num += 1
                print(f"[{config_num}/{total_configs}] Nodes={num_nodes}, Loss={packet_loss*100:.1f}%")
                for run_id in range(1, NUM_RUNS_PER_CONFIG + 1):
                    res = simulation_loop(num_nodes, packet_loss, rng)
                    writer.writerow([
                        num_nodes, packet_loss, run_id,
                        res["converged"], res["total_messages"],
                        res["true_mean"], res["final_consensus_mean"],
                        res["mean_rel_error"],
                        res["mean_rel_error"] <= ACCEPTABLE_ERROR_THRESHOLD,
                        res["remaining_mass"], res["mass_loss_pct"]
                    ])

    print(f"\nSaved results to '{output_filename}'.")

if __name__ == "__main__":
    run_experiments()
