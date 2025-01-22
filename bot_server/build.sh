#!/bin/bash

# Script to build and run the bot server container
# Should be placed in the project root directory

# Set the container name
CONTAINER_NAME="echobridgebot"
IMAGE_NAME="echobridgebot_image"

echo "Starting bot server deployment..."

# Navigate to the bot_server directory
cd ./bot_server || exit 1

# Check if the container is already running
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "Container is already running. Stopping and removing..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# Check if the container exists but is stopped
if [ "$(docker ps -aq -f status=exited -f name=$CONTAINER_NAME)" ]; then
    echo "Removing stopped container..."
    docker rm $CONTAINER_NAME
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Docker image built successfully."
else
    echo "Error building Docker image. Exiting..."
    exit 1
fi