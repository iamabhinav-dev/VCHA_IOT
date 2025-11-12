# VCHA IoT Dashboard

React-based dashboard for Voice-Controlled Home Automation system.

## Features

- 📱 Real-time device monitoring
- 🎨 Manual LED color control
- 📊 Energy consumption tracking
- 📈 Interactive charts and graphs
- 🔌 WebSocket live updates
- 📜 Command history
- 📉 Energy statistics

## Installation

```bash
cd frontend
npm install
```

## Configuration

The dashboard connects to the backend server at `http://localhost:5000` by default.

To change this, create a `.env` file:

```
REACT_APP_API_URL=http://your-server-ip:5000
REACT_APP_WS_URL=ws://your-server-ip:5000/ws
```

## Running

```bash
npm start
```

The app will open at `http://localhost:3000`

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build` folder.

## Components

- **DeviceCard**: Displays device status and control buttons
- **CommandHistory**: Shows recent voice/manual commands
- **EnergyStats**: Displays energy consumption statistics
- **EnergyChart**: Interactive charts for energy over time

## Usage

1. Start the backend server first (`python server/main.py`)
2. Start the React app (`npm start`)
3. The dashboard will automatically connect via WebSocket
4. Click color buttons to manually control devices
5. Monitor energy consumption and command history in real-time
