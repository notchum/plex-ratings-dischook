FROM python:latest
RUN mkdir -p /opt/plex_webhook_discord
WORKDIR /opt/plex_webhook_discord
COPY ./ /opt/plex_webhook_discord
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT python /opt/plex_webhook_discord/plex_webhook_discord.py
