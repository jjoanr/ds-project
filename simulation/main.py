import os
import numpy as np
import random
import matplotlib.pyplot as plt

NUM_STEPS = 5000
NUM_NODES = 100
PACKET_LOSS = 0.10

node_values = np.array([float(random.randint(0, 1000)) for _ in range(NUM_NODES)])
node_weights = np.array([1.0 for _ in range(NUM_NODES)])
error_history = [] # Store the MAE error of the network at each iteration

# True network average
true_mean = np.mean(node_values)

# Simulation of the Push-Sum algorithm
def simulation_loop():
    for round in range(NUM_STEPS):
        if (round % NUM_NODES) == 0:
            error = np.mean(np.abs(true_mean - (node_values / node_weights)))
            error_history.append(error)
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

