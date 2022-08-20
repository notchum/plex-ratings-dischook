FROM python:latest
RUN mkdir -p /opt/plex_ratings_dischook
WORKDIR /opt/plex_ratings_dischook
COPY ./ /opt/plex_ratings_dischook
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT python /opt/plex_ratings_dischook/plex_ratings_dischook.py
