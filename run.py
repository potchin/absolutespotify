#!/usr/bin/env python
import configparser
import spotipy
import requests
import spotipy.util as util
from pprint import pprint
from datetime import datetime, timedelta


def get_tracks_from_station(since, station_id="abr"):
    """This uses the planetradio API to get all songs played on a given station id
    from now backwards until the datetime passed in `since`.

    Station ids can be found here: https://listenapi.planetradio.co.uk/api9.2/stations

    It returns a unique list of tuples containing the artist and track name
    """
    ar_playlist = set()
    if since < (datetime.now() - timedelta(days=7)):
        print("Warning: Data is only available from the past 7 days")
        since = datetime.now() - timedelta(days=7)

    query_date = datetime.now()
    # get data from now and paginating backwards until `last_update`
    while query_date > since:
        query = query_date.strftime("%Y-%m-%d %H:%M:%S")
        url = f"https://listenapi.planetradio.co.uk/api9.2/events/{station_id}/{query}/100"
        print(url)
        ar = requests.get(url)
        ar.raise_for_status()

        for track in ar.json():
            nowPlayingTime = datetime.strptime(
                track["nowPlayingTime"], "%Y-%m-%d %H:%M:%S"
            )
            if nowPlayingTime < since:
                break
            artist = track["nowPlayingArtist"]
            trackname = track["nowPlayingTrack"]
            ar_playlist.add((artist, trackname))

        query_date = nowPlayingTime
    return list(ar_playlist)


def get_spotify_playlist_tracks(username, playlist_id):
    """This gets the FULL list of tracks in a Spotify playlist and returns
    a list of track ids
    """
    results = sp.user_playlist_tracks(username, playlist_id)
    tracks = results["items"]
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])
    return [track["track"]["id"] for track in tracks]


def add_tracks_to_sp_playlist(new_tracks, playlist_id):
    """The spotify API limits you to adding 100 tracks to a playlist at a time
    so this does some pagination
    """
    new_tracks = list(new_tracks)  # it could be a set
    for i in range(0, len(new_tracks), 100):
        sp.playlist_add_items(playlist_id=playlist_id, items=new_tracks[i : i + 100])


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read_file(open(r"config.ini"))

    username = config["absolutespotify"]["username"]
    playlist_id = config["absolutespotify"]["playlist_id"]
    if "station_id" in config["absolutespotify"]:
        bauer_station_id = config["absolutespotify"]["station_code"]
    else:
        bauer_station_id = "abr"  # absolute radio

    # Setup a connection to Spotify
    token = util.prompt_for_user_token(
        username,
        scope="playlist-modify-private,playlist-modify-public",
        client_id=config["absolutespotify"]["client_id"],
        client_secret=config["absolutespotify"]["client_secret"],
        redirect_uri=config["absolutespotify"]["redirect_uri"],
    )
    sp = spotipy.Spotify(auth=token)

    # try to figure out when we last ran.
    # There should be a date in the playlist description.
    try:
        pl_last_update = " ".join(
            sp.playlist(playlist_id=playlist_id)["description"].split()[-2:]
        )
        pl_last_update = datetime.strptime(pl_last_update, "%Y-%m-%d %H:%M:%S.%f")
    except Exception as e:
        print(
            "Unable to get last playlist update time. Pulling data for the last 7 days"
        )
        pl_last_update = datetime.now() - timedelta(days=7)

    existing_spotify_tracks = get_spotify_playlist_tracks(username, playlist_id)
    radio_tracks = get_tracks_from_station(
        since=pl_last_update, station_id=bauer_station_id
    )
    new_tracks = set()

    for artist, trackname in radio_tracks:
        result = sp.search(limit=1, type="track", q=f'{artist} {trackname}"')
        try:
            trackid = result["tracks"]["items"][0]["id"]
        except Exception as e:
            print(f'WARNING: Unable to find artist:"{artist}" track:"{trackname}"')
            # print(result)
            continue
        if trackid not in existing_spotify_tracks:
            print(f'Adding new track artist:"{artist}" track:"{trackname}"')
            new_tracks.add(trackid)

    add_tracks_to_sp_playlist(new_tracks, playlist_id=playlist_id)

    sp.playlist_change_details(
        playlist_id=playlist_id,
        description=f"Songs from {bauer_station_id}. Updated by potchin/absolutespotify on {datetime.now()}",
    )

    print(
        f"Processed {len(radio_tracks)} songs since {pl_last_update}. ",
        f"Added {len(new_tracks)} new tracks to playlist. ",
        f"Playlist now has {len(existing_spotify_tracks) + len(new_tracks)} items.",
    )
