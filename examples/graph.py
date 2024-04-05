# https://new.reddit.com/r/CoinBase/comments/1bv8gxe/comment/kxyonia/
#
# pip install matplotlib
#
import json
import lzma
from datetime import datetime

import matplotlib.pyplot as plt

# Load JSON data from file
with lzma.open("candles.json.xz") as f:
    data = json.load(f)

# Extract data
timestamps = [int(item["start"]) for item in data["candles"]]
opens = [float(item["open"]) for item in data["candles"]]

# Convert UNIX timestamps to datetime objects
dates = [datetime.utcfromtimestamp(ts) for ts in timestamps]

# Plot the graph
plt.figure(figsize=(10, 6))
plt.plot(dates, opens, color="blue", marker="o", linestyle="-")
plt.title("Open Prices Over Time")
plt.xlabel("Time")
plt.ylabel("Open Price (USD)")
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()

# Save the plot as a JPEG file
plt.savefig("open_prices_graph.jpeg")

# Show the plot
plt.show()
