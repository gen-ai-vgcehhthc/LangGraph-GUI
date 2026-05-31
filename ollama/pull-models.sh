#!/bin/sh
# Run this once after `docker compose up` to pull models into the Ollama container.
# Usage:  docker compose exec ollama sh /pull-models.sh
# Or:     sh ollama/pull-models.sh  (if Ollama is running natively)

MODELS="${@:-llama3.2}"   # default: llama3.2; pass others as args

for model in $MODELS; do
  echo "Pulling $model ..."
  ollama pull "$model"
done
echo "Done. Available models:"
ollama list
