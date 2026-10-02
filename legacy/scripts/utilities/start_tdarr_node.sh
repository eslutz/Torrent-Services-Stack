#!/bin/bash
# Start Additional Tdarr Node with Auto-Generated Unique Name
#
# This script automatically generates a unique container name for a new Tdarr node
# and starts it without requiring manual project name specification.
#
# Usage:
#   ./scripts/utilities/start_tdarr_node.sh [options]
#
# Options:
#   --cpu-workers N     Number of CPU workers (default: 2)
#   --gpu-workers N     Number of GPU workers (default: 0)
#   --mem-limit SIZE    Memory limit (default: 2g)
#   --cpus N            CPU limit (default: 2.0)
#   --help             Show this help message
#
# Examples:
#   ./scripts/utilities/start_tdarr_node.sh
#   ./scripts/utilities/start_tdarr_node.sh --cpu-workers 4 --mem-limit 4g
#   ./scripts/utilities/start_tdarr_node.sh --gpu-workers 1 --cpus 4.0

set -e

# Default values
CPU_WORKERS=2
GPU_WORKERS=0
MEM_LIMIT="2g"
CPUS="2.0"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --cpu-workers)
      CPU_WORKERS="$2"
      shift 2
      ;;
    --gpu-workers)
      GPU_WORKERS="$2"
      shift 2
      ;;
    --mem-limit)
      MEM_LIMIT="$2"
      shift 2
      ;;
    --cpus)
      CPUS="$2"
      shift 2
      ;;
    --help)
      grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //'
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Generate unique identifier using timestamp + random number
TIMESTAMP=$(date +%s)
RANDOM_ID=$((RANDOM % 10000))
UNIQUE_ID="${TIMESTAMP}${RANDOM_ID}"

# Generate unique container and node names
CONTAINER_NAME="tdarr-node-${UNIQUE_ID}"
NODE_ID="TdarrNode-${UNIQUE_ID}"
PROJECT_NAME="tdarr-node-${UNIQUE_ID}"

echo "=========================================="
echo "Starting New Tdarr Node"
echo "=========================================="
echo "Container Name: ${CONTAINER_NAME}"
echo "Node ID:        ${NODE_ID}"
echo "CPU Workers:    ${CPU_WORKERS}"
echo "GPU Workers:    ${GPU_WORKERS}"
echo "Memory Limit:   ${MEM_LIMIT}"
echo "CPU Limit:      ${CPUS}"
echo "=========================================="

# Export environment variables for docker-compose
export TDARR_NODE_CONTAINER_NAME="${CONTAINER_NAME}"
export TDARR_NODE_ID="${NODE_ID}"
export TDARR_CPU_WORKERS="${CPU_WORKERS}"
export TDARR_GPU_WORKERS="${GPU_WORKERS}"
export TDARR_NODE_MEM_LIMIT="${MEM_LIMIT}"
export TDARR_NODE_CPUS="${CPUS}"

# Start the node
docker compose -f docker-compose.tdarr-node.yml --project-name "${PROJECT_NAME}" up -d

echo ""
echo "✓ Tdarr node started successfully!"
echo ""
echo "To view logs:"
echo "  docker logs ${CONTAINER_NAME} -f"
echo ""
echo "To stop this node:"
echo "  docker compose -f docker-compose.tdarr-node.yml --project-name ${PROJECT_NAME} down"
echo ""
echo "To view all running nodes:"
echo "  docker ps --filter 'name=tdarr-node'"
echo ""
