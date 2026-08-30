# Plex Ratings Dischook
Plex has a neat feature of giving any media a rating, 0-5 stars, BUT managed users cannot see what
other managed users rated a particular piece of content.
[Tautulli](https://github.com/Tautulli/Tautulli/) handles _almost_ every possible Plex trigger for
notification agents, with the exception of these user ratings which DO have a payload in Plex webhooks.
Since I already have a Discord #plex channel webhook for PMS updates, having
an embed send user ratings as they happen is a great way to keep up with what
other users think of certain movies/shows and get conversation started!

<img width="617" height="603" alt="image" src="https://github.com/user-attachments/assets/58f5fd6e-f66e-44d2-82b1-df28738de7d0" />

## Usage
```sh
docker create \
  --name=plex-ratings-dischook \
  -e PGID=<gid> -e PUID=<uid> \
  -e TZ=<timezone> \
  -e FLASK_RUN_PORT=3000 \
  -e IMGUR_CLIENT_ID=<imgur_client_id> \
  -e DISCORD_WEBHOOK=<webhook_url> \
  -e PLEX_HOSTNAME_PORT=<hostname:port> \ /* (i.e. http://172.0.0.1:32400) */
  -e X_PLEX_TOKEN=<xplextoken> \
  -p 3000:3000 \
  ghcr.io/notchum/plex-ratings-dischook:main
```
