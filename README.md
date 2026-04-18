# Decentralized Systems (DS-MIRI) Project

## Project structure
```
.
├── esp-mesh/                       # ESP-IDF firmware
├── docs/                           # Project documentation
│   ├── proposal.pdf                # Project proposal presentation
│   ├── intermediate-results.pdf    # Intermediate results presentation
│   ├── final-presentation.pdf      # Final presentation
│   ├── technical-report.pdf        # Technical report
│   ├── poster.pdf                  # Project poster
│   ├── references.md               # Related work / bibliography
│   └── figures/                    # Figures and diagrams
└── README.md
```

## Methodology
The goal of this project is to evaluate two versions of a simple average consensus protocol on an ESP32 mesh network. The protocol itself is known as Push-Sum (Kempe et al., 2003), and it was designed to obtain the average of a value held by the nodes in a fully decentralized and asynchronous network. The protocol is proved to converge on the true average value under ideal network conditions (i.e. no packet loss, no malfunctioning nodes), but the most basic version of it fails to produce correct consensus on unreliable networks. That is why a robust version of the protocol is implemented, using acknowledgments of the packets sent before updating the local state, and using sequence numbers, retries and timeouts. Obviously, trying to make a robust version of the protocol increases the complexity and network traffic. The Research Question is to answer at which point does the error in the consensed result becomes unacceptable in an unreliable network, and therefore the robust version is justified, with its implications in performance.

To answer this, the following tasks are done:
- Implement a Discrete-Event Simulation engine of the algorithm, for both the naive and robust versions. With this, we can run experiments for much larger networks.
- Implement the algorithms for ESP32, which will form a mesh network over ESP-IDF. The size of the network is limited to the number of available development boards, so this experiment is not to test the algorithms on large networks, but to evaluate it in real hardware and compare it with the simulation results.
- For both the simulation and the test-bed, log the following metrics for different percentages of packet loss: Mean Absolute Error (MAE) bewtween the consensed value and the true average and total traffic generated (packets transmitted).
- To answer the Research Question, an acceptable deviation from the true average has to be defined. For our case, since we are dealing with a network of IoT devices which are not necessarily concerned about infimum error in the results, a 5 % deviation from the true average will be considered acceptable, and above that, unacceptable.

From the simulation results, the idea is to compare the naive and robust versions with respect to:
- Accuracy: Mean error from the true mean.
- Reliability: Percentage of runs where the error stays < 5 %. A 90 % reliability is assumed to be good (9 of every 10 executions, the algorithm stays below 5 % error).
- Traffic generated: Total number of packets transmitted through the network.
- Mass conservation: Mass is the total sum of the values in the network. When a packet is lost but the sender updated its local state, that "mass" is lost.

## Results
