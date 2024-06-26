#!/usr/bin/env python
import argparse
import configparser
import spotipy
import requests
import spotipy.util as util
from pprint import pprint
from datetime import datetime, timedelta
from os import getenv
from spotipy.oauth2 import SpotifyOAuth


def get_tracks_from_station(since, station_id="abr", skip_before=None):
    """This uses the planetradio API to get all songs played on a given station id
    from now backwards until the datetime passed in `since`.

    Station ids can be found here: https://listenapi.planetradio.co.uk/api9.2/stations/GB?premium=1

    It returns a unique list of tuples containing the artist and track name
    """
    ar_playlist = set()
    if since < (datetime.now() - timedelta(days=7)):
        print("Warning: Data is only available from the past 7 days")
        since = datetime.now() - timedelta(days=7)

    query_date = datetime.now()
    print(f"Pulling station data for {station_id} since {since}")
    if skip_before:
        print(f"Skiping songs aired before {skip_before}:00")
    # get data from now and paginating backwards until `last_update`
    while query_date > since:
        query = query_date.strftime("%Y-%m-%d %H:%M:%S")
        url = f"https://listenapi.planetradio.co.uk/api9.2/events/{station_id}/{query}/100"
        # print(url)
        ar = requests.get(url)
        ar.raise_for_status()

        for track in ar.json():
            nowPlayingTime = datetime.strptime(
                track["nowPlayingTime"], "%Y-%m-%d %H:%M:%S"
            )
            artist = track["nowPlayingArtist"]
            trackname = track["nowPlayingTrack"]
            if skip_before and nowPlayingTime.hour < skip_before:
                continue
            if nowPlayingTime < since:
                break
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

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--playlist-id", help="Override the playlist")
    parser.add_argument("--station-code", help="Override the station")
    args = parser.parse_args()

    username = config["absolutespotify"]["username"]

    skip_before_hour = None
    if args.playlist_id:
        playlist_id = args.playlist_id
    else:
        playlist_id = config["absolutespotify"]["playlist_id"]
        if "skip_before_hour" in config["absolutespotify"]:
            skip_before_hour = int(config["absolutespotify"]["skip_before_hour"])

    if args.station_code:
        bauer_station_ids = args.station_code.split(",")
    elif "station_codes" in config["absolutespotify"]:
        bauer_station_ids = config["absolutespotify"]["station_codes"].split(",")
    else:
        bauer_station_ids = ["abr"]  # absolute radio

    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            username=username,
            scope="playlist-modify-private,playlist-modify-public",
            client_id=config["absolutespotify"]["client_id"],
            client_secret=config["absolutespotify"]["client_secret"],
            redirect_uri=config["absolutespotify"]["redirect_uri"],
            open_browser=False,
        )
    )

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

    if config["absolutespotify"].getboolean("replace_playlist"):
        print("Removing all song from existing playlist")
        sp.playlist_replace_items(playlist_id=playlist_id, items=[])

    existing_spotify_tracks = get_spotify_playlist_tracks(username, playlist_id)
    radio_tracks = []
    for bauer_station_id in bauer_station_ids:
        station_tracks = get_tracks_from_station(
            since=pl_last_update,
            station_id=bauer_station_id,
            skip_before=skip_before_hour,
        )
        radio_tracks.extend(station_tracks)

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
        description=f"Songs from {', '.join(bauer_station_ids)}. Updated by potchin/absolutespotify on {datetime.now()}",
    )

    print(
        f"Processed {len(radio_tracks)} songs since {pl_last_update}. ",
        f"Added {len(new_tracks)} new tracks to playlist. ",
        f"Playlist now has {len(existing_spotify_tracks) + len(new_tracks)} items.",
    )
