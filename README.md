# Decentralized Systems (DS-MIRI) Project

## Project structure
```
.
├── esp-mesh/                       # ESP-IDF firmware
├── simulation/                     # DES simulation of the algorithms
├── docs/                           # Project documentation
├── test-bed-scripts/               # Python scripts for logging / plotting results from the ESP32 testbed 
└── results/                        # Results of the experiments (simulation, test-bed)
```

## Methodology
The goal of this project is to evaluate two versions of a simple average consensus protocol on an ESP32 mesh network. The protocol itself is known as Push-Sum (Kempe et al., 2003), and it was designed to obtain the average of a value held by the nodes in a fully decentralized and asynchronous network. While Push-Sum is proven to converge on the true average under ideal network conditions (no packet loss, no malfunctioning nodes), a naive implementation fails to achieve correct consensus on unreliable networks. To address this, a robust version (Flow-Updating / Flow Gossip) is implemented, which tracks the cumulative "mass" sent over the network for each peer (Almeida et al., 2011). Naturally, ensuring robust mass conservation increases both algorithmic complexity and network traffic.

**Research Question**: At what point does the error in the consensus result become unacceptable in an unreliable network, thereby justifying the performance overhead and complexity of the robust version?

To answer this, the following tasks are done:
- Discrete-Event Simulation (DES): Implement a simulation engine for both the naive and robust algorithms. This allows us to run experiments and observe behavior at scale across much larger networks.
- Hardware Test-Bed: Implement the algorithms on ESP32 microcontrollers forming a mesh network using ESP-IDF. Because the physical network size is limited by the number of available development boards, this test-bed serves to evaluate real-world hardware behavior and validate our simulation results rather than testing scalability.
- Metric Logging: For both the simulation and the test-bed, log key metrics across varying percentages of packet loss. Primary metrics include Mean Relative Error (MRE) between the consensus value and the true average, as well as total traffic generated (packets transmitted).

**Experimental Evaluation**

To answer the research question, we must define an "acceptable" deviation. Because we are targeting IoT ecosystems where infinitesimal precision is not strictly required, a 5% deviation from the true average is considered acceptable.
From the simulation and hardware results, we compare the naive and robust implementations against the following criteria:

- Accuracy: Mean Relative Error (MRE) from the true network average.
- Reliability: The percentage of runs where the final error remains below the 5% threshold. A 90% reliability rate (9 out of 10 executions staying below 5% error) is considered successful.
- Network Traffic: The total number of packets transmitted through the network to reach consensus.
- Mass Conservation: Tracking the total sum of values in the network. (In the naive approach, when a packet is lost after the sender has updated its local state, that "mass" leaks from the system).

