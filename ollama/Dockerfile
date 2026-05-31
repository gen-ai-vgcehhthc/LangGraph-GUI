FROM ollama/ollama:latest

# Install zstd so the entrypoint can decompress models if needed
RUN apt-get update && apt-get install -y zstd && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/bin/ollama"]
CMD ["serve"]
