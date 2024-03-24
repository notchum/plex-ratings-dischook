FROM python:latest
RUN mkdir -p /app/plex_ratings_dischook
WORKDIR /app/plex_ratings_dischook
COPY ./ /app/plex_ratings_dischook
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT python /app/plex_ratings_dischook/plex_ratings_dischook.py
