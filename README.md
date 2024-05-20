# Distributed Audio Playback System

## Overview

This project involves the design and implementation of a distributed system for audio playback. The system includes an audio playback client and a distributed backend that serves audio files and provides user authentication. 
The backend is designed to support load distribution among multiple nodes.

## Features

### Client Features
- **Connect to a User-Specified IP Address**: The client can connect to the bootstrap node using a user-specified IP address.
- **Login/Authentication**: Users can log in or register through the authentication node.
- **Retrieve List of Audio Files**: The client can fetch and display a list of available audio files through the file distribution node.
- **Audio Playback**: Users can download and play selected audio files through the file distribution node.

### Server Features
- **Bootstrap Node**: Manages connections and node registration, handles dynamic spawning of functional nodes based on system needs.
- **Authentication Node**: Handles user login and registration, verifies user credentials.
- **File Distribution Node**: Provides a list of available audio files and transfers selected files to the client.

### Advanced Features
- **Dynamic Load Balancing**: Nodes can be spawned dynamically on both local and remote machines to manage load effectively.
- **Microservices Architecture**: Functional nodes are replaced with load-balanced microservices that share data and functions.
- **Error Checking**: Implemented using MD5 checksum to ensure file integrity.
- **Additional Features**:
  - Dynamic spawning and termination of microservices based on load and client connections.

## Project Structure
The project directory is structured as follows: <br>
├── authentication node<br>
├── bootstrap node <br>
├── client node <br>
├── content node <br>
└── file distribution node

## Installation and Setup

### Prerequisites
- Python 3.x
- Flask
- Pygame (for audio playback)
- Any additional libraries specified in `requirements.txt`

### Instructions
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/sys-MWell/distributed-systems.git
   cd distributed-audio-playback
2. **Start bootstrap node**:
   On the machine designated to run the bootstrap node, execute:
   ```bash
   python BootstrapNode.py
3. **Start Content Nodes:**:
   On separate machines, start the content nodes which will dynamically spawn authentication and file distribution nodes:
   ```bash
   python ContentNode.py
4. **Start Client:**:
   On the client machine, start the client application:
   ```bash
   python ClientNode.py

