#!/usr/bin/bash
docker stop skolmaten
docker rm skolmaten
docker build -t skolmaten .
docker run -d -p 8000:8000 -v ./database.db:/app/database.db --name skolmaten skolmaten
