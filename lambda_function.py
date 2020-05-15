import json
import sys, os
# so all the dependencies are in the folder, if not here then cant, idk why, should learn
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'dependencies')))
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util
import math
from datetime import date
import requests
import boto3
from botocore.exceptions import ClientError
from spotipy import SpotifyException
import decimal
import time

# LOGIN
# get required info from environment variables
# more secure
username = os.environ['username']
cid = os.environ['cid']
secret = os.environ['secret']
redirect_uri = os.environ['redirect_uri']
refreshToken = os.environ['refresh_token'] # do i need this
last_fm_api_key = os.environ['last_fm_api_key']
url = "https://accounts.spotify.com/api/token"
USER_AGENT = "GenreGetter-geloprojects"
# HOW TO login AND GET ACCESS TOKEN HMMMMM
#for avaliable scopes see https://developer.spotify.com/web-api/using-scopes/
scope = 'user-library-read playlist-modify-public playlist-read-private'

client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret) 
# spotify object
sp1 = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
#token = util.prompt_for_user_token(username, scope, cid, secret, redirect_uri)
token = ''
#to dynamodb
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('Spotify')
genreTable = dynamodb.Table('SpotifyGenre')
response = table.get_item(Key = {'user' : 'MxMk'})
token = response['Item']['accessToken']

today = date.today()
# dd/mm/YY
dateToday = today.strftime("%d/%m/%Y")

outStatusCode = 200 # default status code, returns successfulyl, 222 if error in playlist update
outResponse = '' # default body of output of lambda function
# get new access token using refresh token
def refresh_access_token():
    #https://developer.spotify.com/documentation/general/guides/authorization-guide/
    body = {    'grant_type':'refresh_token',
                'refresh_token':refreshToken
    }
    r = requests.post(url, data = body, auth=(cid,secret))
    request = r.json()
    # put into table
    table.put_item(Item = {'user':'MxMk', 'accessToken':request['access_token']})
    print('updated database with new access token')
    return request['access_token']

def login():
    try:
        if token:
            sp1 = spotipy.Spotify(auth=token)
            sp1.current_user() # test if valid if not go to except
            print('valid access token')
        else:
            print("Can't get token for", username)
    except SpotifyException as s: # check if invalid authorization, if so then refresh token
        newToken = refresh_access_token()
        print('renewed access token')
        sp1 = spotipy.Spotify(auth = newToken)
    return sp1

def getUserPlaylistID(sp, name):
    playlists = sp.current_user_playlists()
    total = playlists['total']
    i = 0
    while(i < total):
        playlists = sp.current_user_playlists(offset = i)
        for playlist in playlists['items']:
            if playlist['name'] == name:
                return playlist['id']
            i += 1
    return False

def divideList(arr, n): # n is the size to divide by, n = 50 makes teh arr into 50 size arrays in a list
    for i in range(0, len(arr), n):
        yield arr[i : i + n]

def roundDownToTens(x):
    return int(math.floor(x / 10.0)) * 10

def roundDown(n, decimals = 0): # decimals is where to round down to, if 0, then just integer, 2.4 -> 2, if 1, then 1.37 -> 1.3
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier

def get_genre(id, songName, artist):
    # only one artist name, might skew the search a bit but whatev
    genres = []
    # check if id in dynamodb, if so dont do any of this
    checkSong = genreTable.get_item(Key = {'songID' : id})
    try:
        genresInTable = checkSong['Item']['genres']
        return genresInTable # already have genre, or already tried to find using last fm api so return
    except: # not in table, so follow through with this method
        pass
    time.sleep(1) # seconds for each call
    fmheaders = {"user-agent" : last_fm_api_key}
    fmpayload = {
        'api_key': last_fm_api_key,
        'method': 'track.getTopTags',
        'track' : songName,
        'artist' : artist,
        'format': 'json'
    }
    r = requests.get('http://ws.audioscrobbler.com/2.0/', headers=fmheaders, params=fmpayload)
    data = r.json()
    try:
        tags = data['toptags']['tag']
        # get top 5 tags
        for i in range(0, 5):
            genres.append(tags[i]['name'].lower()) # turns all to lowercase in case tags might have different capitilizaitons but still same tag
    except: # error in finding the track
        pass # nothing so empty list
    # if got the tags, save to dynamodb
    # even if didnt get anything, save id in database
    # so it doesnt go through all of this again each time to result with nothing again
    if len(genres) > 0:
        genreTable.put_item(Item = {'songID' : id, 'genres': set(genres)})
    else:
        genreTable.put_item(Item = {'songID' : id, 'genres' : set(['NotFound'])})
    return genres

def get_generated_playlists(sp):
    # gets saved songs, while also making list for the popularity and year playlists to update the playlists
    saved = sp.current_user_saved_tracks()
    generated = {"Year" : {}, "Genre" : {}, "Popularity" : {}, "Audio" : {}}
    i = 0
    savedSongs = []
    while saved['total'] > i:
        saved = sp.current_user_saved_tracks(offset = i) # limit max default 20 so need offset each time
        for song in saved['items']:
            savedSongs.append(song['track']['id'])
            i += 1
            # GET GENRE
            songName = song['track']['name']
            songArtist = song['track']['artists'][0]['name'] # get first artist
            genres = get_genre(song['track']['id'], songName, songArtist)
            time.sleep(0.05)
            for genre in genres:
                # adds to dict
                if genre in generated['Genre']:
                    generated['Genre'][genre].append(song['track']['id'])
                else:
                    generated['Genre'][genre] = [song['track']['id']]
            # GET YEARS
            year = 0 # unknown default if somehow couldnt parse or whatev
            # parses release date and rounds down to 10s
            if(song['track']['album']['release_date_precision'] == 'year'):
                year = roundDownToTens(int(song['track']['album']['release_date']))
            elif(song['track']['album']['release_date_precision'] == 'day' or song['track']['album']['release_date_precision'] == 'month'):
                year = roundDownToTens(int(song['track']['album']['release_date'][:4])) # get first four characters, which is the year
            
            # adds to dict
            if year in generated['Year']:
                generated['Year'][year].append(song['track']['id'])
            else:
                generated['Year'][year] = [song['track']['id']]

            # GET POPULARITY
            pop = roundDownToTens(int(song['track']['popularity']))
            # adds to dict
            if pop in generated['Popularity']: # check if range of popularity is in dictionary already, ex 10s is 10 - 20 pop
                generated['Popularity'][pop].append(song['track']['id']) # if its already there, appends to the current list
            else: # if not , then makes one and with a list
                generated['Popularity'][pop] = [song['track']['id']]

    # GET AUDIO STATS
    # https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/
    characteristics = ['Acousticness', 'Danceability', 'Energy', 'Instrumentalness', 'Loudness', 'Valence', 'Tempo']
    for characteristic in characteristics:
        generated['Audio'][characteristic] = {} # adds another dict layer into dict
    audioSongs = divideList(savedSongs, 100)
    for listOfSongs in audioSongs:
        temp1 = sp.audio_features(listOfSongs)
        for song in temp1:
            charVals = []
            charVals.append(roundDown(song['acousticness'], 1))
            charVals.append(roundDown(song['danceability'], 1))
            charVals.append(roundDown(song['energy'], 1))
            charVals.append(roundDown(song['instrumentalness'], 1))
            charVals.append(roundDown(song['loudness'], 0))
            charVals.append(roundDown(song['valence'], 1))
            charVals.append(roundDown(song['tempo'], -1))
            for i in range(0, len(characteristics)):
                if charVals[i] in generated['Audio'][characteristics[i]]:
                    generated['Audio'][characteristics[i]][charVals[i]].append(song['id'])
                else:
                    generated['Audio'][characteristics[i]][charVals[i]] = [song['id']]
    return generated

def update_playlist(sp, generated, playlistInfo):
    playlistName = playlistInfo['name']
    playlistID = getUserPlaylistID(sp, playlistName)
    global outResponse, outStatusCode
    if playlistID is False:
        outResponse += 'Unable to get playlist ID of {}\n'.format(playlistName)
        outStatusCode = 222 # idk made up status code lol
        return
    # default gate
    gate = 'or'
    if 'gate' in playlistInfo:
        gate = playlistInfo['gate']
    # get description info
    descr = [] # default none
    toAdd = []
    if 'genres' in playlistInfo:
        for genre in playlistInfo['genres']:
            descr.append(genre)
            if gate == 'or':
                toAdd.extend(generated['Genre'][genre])
            else: # and, so track has to have all these genres
                toAdd = list(set(toAdd) & set(generated['Genre'][genre])) # intersection
    if 'years' in playlistInfo:
        for year in playlistInfo['years']:
            descr.append('{}s'.format(year))
            if gate == 'or':
                toAdd.extend(generated['Year'][year])
            else:
                toAdd = list(set(toAdd) & set(generated['Year'][year]))
    if 'characteristics' in playlistInfo:
        for characteristic in playlistInfo['characteristics']:
            restr = playlistInfo['characteristics'][characteristic].split(' ')
            descr.append('{} {}'.format(characteristic, ' '.join(restr)))
            for numbers in generated['Audio'][characteristic]:
                if len(restr) == 3: # x > 5
                    if restr[1] == '>':
                        if numbers >= float(restr[2]):
                            if gate == 'or':
                                toAdd.extend(generated['Audio'][characteristic][numbers])
                            else:
                                toAdd = list(set(toAdd) & set(generated['Audio'][characteristic][numbers]))
                    elif restr[1] == '<':
                        if numbers < float(restr[2]):
                            if gate == 'or':
                                toAdd.extend(generated['Audio'][characteristic][numbers])
                            else:
                                toAdd = list(set(toAdd) & set(generated['Audio'][characteristic][numbers]))
                    else:
                        outResponse += 'Wrong formatting of characteristic info of playlist'
                        outStatusCode = 222
                        return
                elif len(restr) == 5: # 5 < x < 6
                    if restr[1] == '<' and restr[3] == '<':
                        if numbers >= float(restr[0]) and numbers < float(restr[4]):
                            if gate == 'or':
                                toAdd.extend(generated['Audio'][characteristic][numbers])
                            else:
                                toAdd = list(set(toAdd) & set(generated['Audio'][characteristic][numbers]))
                    elif restr[1] == '>' and restr[3] == '>':
                        if numbers < float(restr[0]) and numbers >= float(restr[4]):
                            if gate == 'or':
                                toAdd.extend(generated['Audio'][characteristic][numbers])
                            else:
                                toAdd = list(set(toAdd) & set(generated['Audio'][characteristic][numbers]))
                    else:
                        outResponse += 'Wrong formatting of characteristic info of playlist'
                        outStatusCode = 222
                        return
                else:
                    outResponse += 'Wrong formatting of characteristic info of playlist'
                    outStatusCode = 222
                    return
    if 'popularity' in playlistInfo:
        restr = playlistInfo['popularity'].split(' ')
        descr.append('Popularity {}'.format(' '.join(restr)))
        for numbers in generated['Popularity']:
            if len(restr) == 3: # x > 5
                if restr[1] == '>':
                    if numbers >= float(restr[2]):
                        if gate == 'or':
                            toAdd.extend(generated['Popularity'][numbers])
                        else:
                            toAdd = list(set(toAdd) & set(generated['Popularity'][numbers]))
                elif restr[1] == '<':
                    if numbers < float(restr[2]):
                        if gate == 'or':
                            toAdd.extend(generated['Popularity'][numbers])
                        else:
                            toAdd = list(set(toAdd) & set(generated['Popularity'][numbers]))
                else:
                    outResponse += 'Wrong formatting of characteristic info of playlist'
                    outStatusCode = 222
                    return
            elif len(restr) == 5: # 5 < x < 6
                if restr[1] == restr[3] and restr[3] == '<':
                    if numbers >= float(restr[0]) and numbers < float(restr[4]):
                        if gate == 'or':
                            toAdd.extend(generated['Popularity'][numbers])
                        else:
                            toAdd = list(set(toAdd) & set(generated['Popularity'][numbers]))
                elif restr[1] == restr[3] and restr[3] == '>':
                    if numbers < float(restr[0]) and numbers >= float(restr[4]):
                        if gate == 'or':
                            toAdd.extend(generated['Popularity'][numbers])
                        else:
                            toAdd = list(set(toAdd) & set(generated['Popularity'][numbers]))
                else:
                    outResponse += 'Wrong formatting of characteristic info of playlist'
                    outStatusCode = 222
                    return
            else:
                outResponse += 'Wrong formatting of characteristic info of playlist'
                outStatusCode = 222
                return
    #remove duplicates
    toAdd1 = list(dict.fromkeys(toAdd))
    # update playlist
    songsToAdd = divideList(toAdd1, 100)
    sp.user_playlist_replace_tracks(username, playlistID, []) # clears playlist
    for songs in songsToAdd:
        sp.user_playlist_add_tracks(username, playlistID, songs)
        time.sleep(2)
    if gate == 'or':
        descr = '|'.join(descr)
    elif gate == 'and':
        descr = ','.join(descr)
    else:
        descr = '/'.join(descr)
    sp.user_playlist_change_details(username, playlistID, 
                                    description = '{} -- Updated on {}'.format(descr, dateToday))
    
def lambda_handler(event, context):
    spotify = login() # spotify obj
    generated = get_generated_playlists(spotify)
    # scuffed - hard coded the playlists i wanna keep updating
    # added multiple sleep x seconds in the methods, so takes like 6 mins
    # so doesnt reach api rate limit
    # might be overkill but better to be safe than not
    
    # playlists to update, with information on what to have in playlist
    # has name, genres, years, popularity, characteristics, gate ('and' or 'or') -- logic gate
    # str, [str], [int], str, {'Tempo' : str, ... : str}, str
    # gate is for .. example: genres = ['rnb', 'soul'] gate = 'and' ---- default gate is 'or'
    # returns playlist with songs with both genre rnb and soul
    # charactersitic ex: {'Tempo' : ' x > 140'
    # x has to be leftmost
    playlists = [
        {'name': 'Underrated?', 'popularity': '10 < x < 40'},
        {'name': 'Unknown?', 'popularity': 'x < 10'},
        {'name': 'Quiet?', 'characteristics': {'Loudness': 'x < -16.0'}},
        {'name': 'Danceable?', 'characteristics': {'Danceability': 'x > 0.8'}},
        {'name': 'Low Energy?', 'characteristics': {'Energy': 'x < 0.3'}},
        {'name': 'Sad?', 'characteristics': {'Valence': 'x < 0.20'}},
        {'name': 'High Energy?', 'characteristics': {'Energy': 'x > 0.9'}},
        {'name': 'No Vocals?', 'characteristics': {'Instrumentalness': 'x > 0.7'}},
        {'name': 'High Tempo?', 'characteristics': {'Tempo': 'x > 150'}},
        {'name': 'Happy?', 'characteristics': {'Valence': 'x > 0.8'}},
        {'name': '00s', 'years': [2000]},
        {'name': '90s', 'years': [1990]},
        {'name': '80s', 'years': [1980]},
        {'name': '70s', 'years': [1970]},
        {'name': '60s', 'years': [1960]},
        {'name': 'Hip-hop?', 'genres': ['hip-hop']}, # genres are all lowercase
        {'name': 'Rnb?', 'genres': ['rnb']},
        {'name': 'Soul?', 'genres': ['soul']},
        {'name': 'Rock?', 'genres': ['rock']},
        {'name': 'Electronic?', 'genres': ['electronic']},
        {'name': 'Indie?', 'genres': ['indie']},
        {'name': 'Alternative?', 'genres': ['alternative']},
        {'name': 'Pop?', 'genres': ['pop']}
        ]
    today = date.today()
    # dd/mm/YY
    dateToday = today.strftime("%d/%m/%Y")
    
    for playlist in playlists:
        update_playlist(spotify, generated, playlist)
        time.sleep(5)

    global outResponse, outStatusCode
    if outResponse == '':
        outResponse = 'Successfully updated playlists'
    return{
        'statusCode': outStatusCode,
        'body': json.dumps(outResponse)
    }