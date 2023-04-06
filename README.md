# Absolutespotify

I like radio, I hate ads and I'm not that bothered about presenters. So I made absolutespotify.

Absolutespotify pulls the playlist of a bauer-media radio station (defaults to Absolute Radio) and adds all songs to a given spotify playlist.

If you're just interested in listening to the playlist then [here you go](https://open.spotify.com/playlist/7ojHfeLSzqGrNwx6MUwIS7?si=8be23abb37b6493e). Excuse the playlist name, Google Assistant is easily confused.


## Config

Here's an example config file which needs to be named `config.ini`.
You will need to create a spotify app to get a `client_id` and `client_secret`, see the [spotipy docs](https://spotipy.readthedocs.io/en/master/#getting-started) for details.

```
[absolutespotify]
username = spotify_username
client_id = blah
client_secret = some_secret
playlist_id = get_this_from_spotify
redirect_uri = https://localhost
station_codes = abr,ab9
skip_before_hour = 7
```

Note that the `playlist_id` is not the playlist name, you can get the id by going to "Share -> Copy Link to playlist" in the spotify app.

`station_codes`s (including 'Premium' stations) can be found [here](https://listenapi.planetradio.co.uk/api9.2/stations/GB?premium=1), add in comma separated if you want tracks from multiple stations.

`skip_before_hour` can optionally be added to skip adding songs from early hours of the day (they play some odd stuff in the night). Eg setting it to `7` means that anything played between midnight and 7am wont be added.

## Behavior

Tracks will be added to the given playlist with these restrictions:

- only tracks from the past 7 days (or since you last ran the script) will be added (Bauer's API only gives data for the last 7 days)
- tracks will only be added once (no duplicates)
- the last update time is saved in the playlist description

