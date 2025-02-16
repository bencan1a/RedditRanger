#!/bin/bash

# Function to kill process on a specific port
kill_port_process() {
    local port=$1
    echo "Checking port $port..."
    
    # Find process using the port
    pid=$(lsof -ti:$port)
    
    if [ ! -z "$pid" ]; then
        echo "Found process $pid using port $port"
        
        # Try graceful termination first
        echo "Attempting graceful termination..."
        kill -15 $pid 2>/dev/null
        
        # Wait briefly and check if process is still running
        sleep 2
        if ps -p $pid > /dev/null 2>&1; then
            echo "Process still running, forcing termination..."
            kill -9 $pid 2>/dev/null
        fi
        
        echo "Process on port $port terminated"
    else
        echo "No process found using port $port"
    fi
}

echo "Starting port cleanup..."

# Kill processes on both ports
kill_port_process 5000
kill_port_process 5002

echo "Port cleanup completed"

# Verify ports are free
if lsof -ti:5000 >/dev/null 2>&1 || lsof -ti:5002 >/dev/null 2>&1; then
    echo "WARNING: Some processes could not be terminated"
    exit 1
else
    echo "SUCCESS: All ports are now free"
    exit 0
fi
