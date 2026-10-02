#!/bin/bash
# Manage Tdarr Nodes - List and Stop Running Nodes
#
# This script helps you view and manage running Tdarr nodes started
# with the auto-generated unique names.
#
# Usage:
#   ./scripts/utilities/manage_tdarr_nodes.sh [command]
#
# Commands:
#   list       List all running Tdarr nodes (default)
#   stop ID    Stop a specific node by its container ID or unique ID
#   stop-all   Stop all additional Tdarr nodes (keeps main node running)
#   help       Show this help message
#
# Examples:
#   ./scripts/utilities/manage_tdarr_nodes.sh list
#   ./scripts/utilities/manage_tdarr_nodes.sh stop 1735436123456
#   ./scripts/utilities/manage_tdarr_nodes.sh stop tdarr-node-1735436123456
#   ./scripts/utilities/manage_tdarr_nodes.sh stop-all

set -e

# Function to list all Tdarr nodes
list_nodes() {
  echo "=========================================="
  echo "Running Tdarr Nodes"
  echo "=========================================="

  # Get all tdarr-node containers
  NODES=$(docker ps --filter "name=tdarr-node" --format "table {{.Names}}\t{{.Status}}\t{{.ID}}" 2>/dev/null || true)

  if [ -z "$NODES" ] || [ "$(echo "$NODES" | wc -l)" -eq 1 ]; then
    echo "No additional Tdarr nodes running (only main node)"
  else
    echo "$NODES"
    echo ""
    echo "To stop a specific node:"
    echo "  ./scripts/utilities/manage_tdarr_nodes.sh stop <container-name>"
  fi
  echo "=========================================="
}

# Function to extract unique ID from container name
extract_unique_id() {
  local container_name="$1"
  # Extract ID from tdarr-node-XXXXXXXX format
  echo "${container_name#tdarr-node-}"
}

# Function to stop a specific node
stop_node() {
  local identifier="$1"

  if [ -z "$identifier" ]; then
    echo "Error: Please specify a container name or unique ID to stop"
    echo "Usage: $0 stop <container-name or unique-id>"
    exit 1
  fi

  # Check if identifier is just the numeric ID or full container name
  if [[ "$identifier" =~ ^[0-9]+$ ]]; then
    # It's just the numeric ID, prepend tdarr-node-
    CONTAINER_NAME="tdarr-node-${identifier}"
  else
    # It might be the full container name or container ID
    CONTAINER_NAME="$identifier"
  fi

  # Check if container exists
  if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: Container '${CONTAINER_NAME}' not found"
    echo ""
    echo "Available nodes:"
    list_nodes
    exit 1
  fi

  echo "Stopping Tdarr node: ${CONTAINER_NAME}"

  # Extract unique ID for project name
  UNIQUE_ID=$(extract_unique_id "$CONTAINER_NAME")
  PROJECT_NAME="tdarr-node-${UNIQUE_ID}"

  # Stop using docker-compose to properly clean up
  export TDARR_NODE_CONTAINER_NAME="${CONTAINER_NAME}"
  docker compose -f docker-compose.tdarr-node.yml --project-name "${PROJECT_NAME}" down

  echo "✓ Node stopped and removed successfully"
}

# Function to stop all additional nodes (not the main one)
stop_all_nodes() {
  echo "=========================================="
  echo "Stopping All Additional Tdarr Nodes"
  echo "=========================================="

  # Get all tdarr-node containers except the main one
  NODES=$(docker ps --filter "name=tdarr-node-" --format "{{.Names}}" | grep -v "^tdarr-node$" || true)

  if [ -z "$NODES" ]; then
    echo "No additional Tdarr nodes to stop"
    return
  fi

  echo "Found nodes to stop:"
  echo "$NODES"
  echo ""

  read -p "Are you sure you want to stop all these nodes? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
  fi

  # Stop each node
  for node in $NODES; do
    echo "Stopping: $node"
    UNIQUE_ID=$(extract_unique_id "$node")
    PROJECT_NAME="tdarr-node-${UNIQUE_ID}"
    export TDARR_NODE_CONTAINER_NAME="$node"
    docker compose -f docker-compose.tdarr-node.yml --project-name "${PROJECT_NAME}" down 2>/dev/null || true
  done

  echo ""
  echo "✓ All additional nodes stopped successfully"
  echo "  (Main tdarr-node container is still running)"
}

# Main command handling
COMMAND="${1:-list}"

case "$COMMAND" in
  list)
    list_nodes
    ;;
  stop)
    stop_node "$2"
    ;;
  stop-all)
    stop_all_nodes
    ;;
  help|--help|-h)
    grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //'
    ;;
  *)
    echo "Unknown command: $COMMAND"
    echo "Use 'help' for usage information"
    exit 1
    ;;
esac
