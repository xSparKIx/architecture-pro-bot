#!/bin/bash

ollama serve &
pid=$!
sleep 5
ollama pull mistral:7b-instruct
wait $pid