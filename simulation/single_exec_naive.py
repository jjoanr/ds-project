import os
import numpy as np
import random
import matplotlib.pyplot as plt

NUM_STEPS = 1000000
NUM_NODES = 4
PACKET_LOSS = 0.00

TOLERANCE = 1e-4  # 0.01% relative error
stability_counter = 0
REQUIRED_STABLE_ROUNDS = 5

# node_values = np.array([float(random.randint(0, 1000)) for _ in range(NUM_NODES)])
node_values = np.array([5.0, 10.0, 30.0, 50.0])
node_weights = np.array([1.0 for _ in range(NUM_NODES)])
error_history = [] # Store the MAE error of the network at each iteration

# True network average
true_mean = np.mean(node_values)

# Simulation of the Push-Sum algorithm
def simulation_loop():
    global stability_counter
    for round in range(NUM_STEPS):
        if (round % NUM_NODES) == 0:
            # Calculate the mean relative error across all nodes
            estimates = node_values / node_weights
            # Log the drift from the true mean
            relative_errors = np.abs(true_mean - estimates) / np.abs(true_mean)
            mean_relative_error = np.mean(relative_errors)
            error_history.append(mean_relative_error)
            # 2. Check for convergence (nodes agreement on a value, even if it is wrong)
            current_network_mean = np.mean(estimates)
            consensus_spread = np.max(np.abs(estimates - current_network_mean)) / np.abs(current_network_mean)
            if (consensus_spread < TOLERANCE):
                stability_counter += 1
                if (stability_counter >= REQUIRED_STABLE_ROUNDS):
                    print(f"Converged after {round} total steps ({(round // NUM_NODES)} rounds).")
                    print(f"Final Consensus Value: {current_network_mean}")
                    break
            else:
                stability_counter = 0

        # chose at random a tx and rx node
        tx_node_id = random.randint(0, NUM_NODES-1)
        rx_node_id = random.randint(0, NUM_NODES-1)
        while(tx_node_id == rx_node_id): # avoid having tx and rx as the same node
            rx_node_id = random.randint(0, NUM_NODES-1)
        
        # update tx node value/weight
        node_values[tx_node_id] /= 2
        node_weights[tx_node_id] /= 2
        # Simulated packet loss
        if (random.random() >= PACKET_LOSS): 
            # update rx node value/weight
            node_values[rx_node_id] += node_values[tx_node_id]
            node_weights[rx_node_id] += node_weights[tx_node_id]
        # Else, packet is lost.
        # Naive: Do nothing
        # Robust: If no ACK, "refund" values to the Tx node
        """
        else:
            node_values[tx_node_id] *= 2
            node_weights[tx_node_id] *= 2
        """

    # Compute Mean Absolute Error for last round
    error_last_round = np.mean(np.abs(true_mean - (node_values / node_weights))) 
    print(f"Mean Absolute Error (MAE) after {len(error_history)} rounds: {error_last_round}")

    plt.figure()
    ratio = node_values / node_weights
    plt.plot(error_history)
    plt.show()

if __name__ == "__main__": 
    print("Simulation of Push-Sum Algorithm Consensus in a Mesh Network of IoT Nodes\n")
    print(f"True average value: {true_mean}")
    simulation_loop()
    for i in range(NUM_NODES):
        print(f"{node_values[i] / node_weights[i]}")

