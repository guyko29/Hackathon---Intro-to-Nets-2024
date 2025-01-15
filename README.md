# Hackathon---Intro-to-Nets-2024

A Python-based network performance testing tool that allows users to measure network throughput using both TCP and UDP protocols simultaneously. The application consists of a server component that can handle multiple concurrent connections and a client that can initiate multiple TCP and UDP connections for comprehensive speed testing.

## Features

- Dual protocol support (TCP and UDP)
- Multiple concurrent connections
- Configurable file size for testing
- Real-time speed measurements
- UDP packet loss tracking
- Color-coded console output for better readability

## Prerequisites

- Python 3.x
- Required Python packages:
  - colorama
  - click

Install dependencies using:
```bash
pip install colorama click
```

## Server Setup

The server component (`SpeedTestServer.py`) handles incoming connections and manages data transfer for speed testing.

### Starting the Server

```bash
python SpeedTestServer.py
```

The server will:
- Start broadcasting on UDP port 13118
- Listen for TCP connections on port 12345
- Handle UDP requests on port 13117
- Display its IP address on startup

## Client Usage

The client component (`ClientState.py`) allows users to configure and run speed tests.

### Starting the Client

```bash
python ClientState.py
```

### Configuration Parameters

When starting the client, you'll need to provide:
1. Server IP address
2. Server UDP port (default: 13117)
3. Server TCP port (default: 12345)
4. File size for testing (in bytes)
5. Number of TCP connections
6. Number of UDP connections

## How It Works

### Server Side
- Broadcasts offer messages to discover clients
- Handles multiple concurrent TCP and UDP connections
- Sends test data based on client requests
- Provides real-time transfer status updates

### Client Side
- Connects to server using provided parameters
- Creates specified number of TCP and UDP connections
- Measures transfer speeds and packet loss
- Displays detailed performance metrics for each connection

## Performance Metrics

The application measures and displays:
- Total transfer time
- Transfer speed (bits per second)
- UDP packet success rate
- Individual connection performance

## Console Output

The application uses color-coded console output for better readability:
- Green: Success messages and TCP transfer results
- Yellow: UDP transfer results and prompts
- Cyan: Timestamps
- Red: Error messages

## Error Handling

The application includes comprehensive error handling for:
- Network connectivity issues
- Invalid input parameters
- Connection timeouts
- Resource allocation failures

## Contributing
Guy Korenfeld 

Yuval Livshits
