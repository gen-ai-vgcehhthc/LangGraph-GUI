# Use the official pre-built Ollama image.
# The old approach (curl install.sh inside nvidia/cuda) fails in many
# Docker build environments because the script detects it's not on a real
# Linux system or cannot reach the network during build.
FROM ollama/ollama:latest

# ollama/ollama already has the binary; just expose the port and serve.
EXPOSE 11434
CMD ["serve"]
