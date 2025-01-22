# Set the container name
CONTAINER_NAME="echobridgebot"
IMAGE_NAME="echobridgebot_image"

# Run the container
echo "Starting container..."
sudo docker run -d \
    --name $CONTAINER_NAME \
    -p 4222:4222 \
    --restart unless-stopped \
    -v "$(pwd)/data:/app/data" \
    $IMAGE_NAME

# Check if container started successfully
if [ "$(sudo docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "Container started successfully!"
    echo "Bot server is running on port 4222"
else
    echo "Error: Container failed to start."
    exit 1
fi