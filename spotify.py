import spotipy
import json
import csv
import os
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util
import math
from datetime import date

# auto populated if put into a csv file with these
cid ='' # Client ID
secret = '' # Client Secret
username = '' # Spotify username
redirect_uri='' # redirect url

# get info needed from a text file
# so more secure
def getInfo(textFile):
    global username, cid, secret, redirect_uri
    with open(textFile, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            username = row['username']
            cid = row['cid']
            secret = row['secret']
            redirect_uri = row['redirect_uri']
            return

# reads text file with the info and populates the variables needed
# text file should have the first line (no spaces, separated by commas)
# username,cid,secret,redirect_uri
# second line would be the corresponding values
# example of a csv file:
# username,cid,secret,redirect_uri
# 324ESDF,0539ESDF,342049SDFEWR,https://www.google.com
textFileWithInfo = 'info.csv'
getInfo(textFileWithInfo)

#for avaliable scopes see https://developer.spotify.com/web-api/using-scopes/
scope = 'user-library-read playlist-modify-public playlist-read-private'

client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret) 

# spotify object
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

token = util.prompt_for_user_token(username, scope, cid, secret, redirect_uri)
# validates token
if token:
    sp = spotipy.Spotify(auth=token)
else:
    print("Can't get token for", username)

# checks if the id in parameter is in saved songs csv
def inSaved(id):
    with open('savedSongs.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['id'] == id:
                return True
    return False

# returns list of saved songs
def savedToList():
    out = []
    with open('savedSongs.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            out.append(row['id'])
    return out

# output saved songs id to a csv file
# check if it ouputs all saved songs
def writeSaved():
    saved = sp.current_user_saved_tracks()
    i = 0
    with open('savedSongs.csv', 'w', newline = '') as file:
        writer = csv.DictWriter(file, fieldnames = ['id']) #in case i wanna add more stuff in csv, add to field names and to writerow
        writer.writeheader()
        while(saved['total'] > i):
            saved = sp.current_user_saved_tracks(offset = i) # limit max default 20 so need offset each time
            for song in saved['items']:
                writer.writerow({'id' : song['track']['id']}) # in the form of a dictionary
                i += 1

def showFunctions():
    out = '''\
        0 - Exit
        1 - Show user info
        2 - Show playlists
        3 - Copy a playlist
        4 - Remove already liked songs in a playlist
        5 - Playlist generator
        S - Save liked songs to csv
        '''
    print(out)

# prints out user info
def showUserInfo():
    user = sp.current_user()
    print()
    print('Name: ' + user['display_name'])
    print('ID: ' + user['id'])
    print()

# prints out the playlists
def showPlaylists():
    playlists = sp.current_user_playlists()
    total = playlists['total']
    i = 0
    print()
    print('Playlist Names: ')
    while(i < total):
        playlists = sp.current_user_playlists(offset = i) # limit default 50 so need offset
        for playlist in playlists['items']:
            print(playlist['name'])
            print('\t Total Songs: {}'.format(playlist['tracks']['total']))
            print('\t Saved Songs: {}'.format(numSavedSongs(playlist['name'])))
            i += 1
    print()

# get number of saved songs already in playlist specified
def numSavedSongs(name):
    savedSongs = savedToList()
    playlistSongs = playlistToList(name)
    savedInPlaylist = [x for x in playlistSongs if x in savedSongs]
    return len(savedInPlaylist)
    raise NotImplementedError

# copys playlists to new playlist with option to remove already liked songs
def copyPlaylists(name, description = "", remove = True, public = True):
    playlists = sp.user_playlists(username) # max 50 playlists - need to make another method just to get user playlists
    toCopy = []
    currentPlaylists = currentPlaylistsToList()
    # check if what user typed is actually a playlist they have saved
    while True:
        print('Type in name of saved Playlist name to copy')
        print('Type ~ to stop')
        user = input()
        if user == '~':
            break
        else:
            toCopy.append(user)
    # check if name is taken - just so easier to navigate
    while name in currentPlaylists:
        name = input('Please type a new unique name for ur new playlist ')
    sp.user_playlist_create(username, name, public, description)

    # get new playlist id
    newPlaylistID = getUserPlaylistID(name)
    if(newPlaylistID is False):
        print('Unable to get new Playlist ID')
        return

    # put songs in list and remove duplicates
    finalTracks = []
    for playlist in toCopy:
        currentTracks = playlistToList(playlist)
        notDuplicate = [x for x in currentTracks if x not in finalTracks]
        # copy notDuplicate to finalTracks
        for x in notDuplicate:
            finalTracks.append(x)
    i = 0
    current = []
    # put songs in playlist
    while(i < len(finalTracks)):
        current.append(finalTracks[i])
        if len(current) == 100:
            sp.user_playlist_add_tracks(username, newPlaylistID, current)
            current = []
        elif i == len(finalTracks) - 1:
            sp.user_playlist_add_tracks(username, newPlaylistID, current)
            current = []
        i += 1
        
    # update new playlist to remove already liked songs
    if remove:
        updatePlaylist(name)
    
def getUserPlaylistID(name):
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
    
def currentPlaylistsToList():
    out = []
    playlists = sp.current_user_playlists()
    total = playlists['total']
    i = 0
    while(i < total):
        playlists = sp.current_user_playlists(offset = i)
        for playlist in playlists['items']:
            out.append(playlist['name'])
            i += 1
    return out

# removes already liked songs from the playlist
# no leftover liked songs
def updatePlaylist(playlist):
    savedSongs = savedToList()
    songsInPlaylist = playlistToList(playlist)
    toRemove = [x for x in songsInPlaylist if x in savedSongs]
    listss = []
    lists = []
    for i in range(len(toRemove)):
        if (i != 0 and i % 99 == 0): # think 100 is limit hmm 99 looks better
            i == 0
            listss.append(lists)
            lists = []
        lists.append(toRemove[i])
    listss.append(lists) # append the last list

    playlistID = getUserPlaylistID(playlist)
    for songsToRemove in listss:
        sp.user_playlist_remove_all_occurrences_of_tracks(username, playlistID, songsToRemove, snapshot_id=None)

def playlistToList(*playlist):
    out = []
    i = 0
    # y error when i add the while loop and totalsongs
    for playlists in playlist:
        totalSongs = sp.user_playlist(username, getUserPlaylistID(playlists))['tracks']['total']
        while i < totalSongs:
            playlistSongs = sp.user_playlist_tracks(username, getUserPlaylistID(playlists), offset = i)
            for songs in playlistSongs['items']:
                try: # dont do this, think its cuz foreign lang on name
                    if songs['track']['id'] is None:
                        pass
                    else:
                        out.append(songs['track']['id'])
                    i += 1
                except:
                    # maybe spotify removed this songs, which is why error... hmmmm
                    print('u suck, fix this')
                    i += 1
    return out

def start():
    print('Some things you can do...')
    print('If you want to update or copy playlists, you should input the option to save liked songs to csv first.')
    while True:
        showFunctions()
        choice = input("Type what you want to do ")
        if(choice == '0'):
            break
        elif(choice == '1'):
            showUserInfo()
        elif(choice == '2'):
            showPlaylists()
        elif(choice == '3'):
            name = input('What would you like the name of the new playlist to be? ')
            description = input('Input a description if you want ')
            removeTF = input('True/False if you want to remove saved songs from the playlists ')
            publicTF = input('True/False if you want to make it public or private respectively ')
            if(removeTF == 'True'):
                remove = True
            elif removeTF == 'False':
                remove = False
            else: # default
                remove = True
            if(publicTF == 'True'):
                public = True
            elif publicTF == 'False':
                public = False
            else: # default
                public = True
            # yo am i stupid, but why can it reference the remove and public, if its inside the if statemtn
            copyPlaylists(name, description, remove, public)
        elif(choice == '4'):
            playlist = input('Input the playlist you want to remove saved songs ')
            updatePlaylist(playlist)
        elif(choice == '5'):
            playlistGenerator()
        elif(choice == 'S'):
            writeSaved()
        else:
            print('Invalid choice dimwit')
            break
def divideList(arr, n): # n is the size to divide by, n = 50 makes teh arr into 50 size arrays in a list
    for i in range(0, len(arr), n):
        yield arr[i : i + n]

def roundDownToTens(x):
    return int(math.floor(x / 10.0)) * 10

def roundDown(n, decimals = 0): # decimals is where to round down to, if 0, then just integer, 2.4 -> 2, if 1, then 1.37 -> 1.3
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier

def playlistGenerator():
    generated = {"Year" : {}, "Genre" : {}, "Popularity" : {}, "Audio" : {}}
    description = []
    savedSongs = savedToList() # put all ids of saved songs in this var

    songs = divideList(savedSongs, 50) # 50 max ids
    for listsOfSongs in songs:
        temp1 = sp.tracks(listsOfSongs) # temp var of tracks
        for track in temp1['tracks']:
            # GET YEARS
            year = 0 # unknown default if somehow couldnt parse or whatev
            # parses release date and rounds down to 10s
            if(track['album']['release_date_precision'] == 'year'):
                year = roundDownToTens(int(track['album']['release_date']))
            elif(track['album']['release_date_precision'] == 'day' or track['album']['release_date_precision'] == 'month'):
                year = roundDownToTens(int(track['album']['release_date'][:4])) # get first four characters, which is the year
            
            # adds to dict
            if year in generated['Year']:
                generated['Year'][year].append(track['id'])
            else:
                generated['Year'][year] = [track['id']]

            # GET POPULARITY
            pop = roundDownToTens(int(track['popularity']))
            # adds to dict
            if pop in generated['Popularity']: # check if range of popularity is in dictionary already, ex 10s is 10 - 20 pop
                generated['Popularity'][pop].append(track['id']) # if its already there, appends to the current list
            else: # if not , then makes one and with a list
                generated['Popularity'][pop] = [track['id']]
            
            # GET GENRE
            # but how tho
            # web scraping? 
            # or machine learning pogu but have to scrape for audio lmao or could use spotifys api full audio analysis to learn from
            # https://towardsdatascience.com/music-genre-prediction-with-spotifys-audio-features-8a2c81f1a22e
    
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

    # iterate over dictionary and checking lengths of lists and display to user
    for types in generated:
        print('{}: '.format(types))
        for subCat in generated[types]:
            # take out categories that dont have 50+ or more songs
            if isinstance(subCat, str):
                print('\t{}:'.format(subCat))
                for subCat1 in generated[types][subCat]:
                    amtOfSongs = len(generated[types][subCat][subCat1])
                    if(amtOfSongs >= 50):
                        print('\t\t{} - {} songs'.format(subCat1, amtOfSongs))
            else:
                amtOfSongs = len(generated[types][subCat])
                if(amtOfSongs >= 50):
                    print('\t{} - {} songs'.format(subCat, amtOfSongs))
        print() # skip a line
    # ask user for a playlist they want, or multiple, and add to acc
    toAdd = []
    userInput = 'yes' # default
    while(userInput == 'yes'):
        userToAdd = input('Which category? Ex. Year 2020 or Popularity 70 or Audio Acousticness 0.6 or Audio Acousticness x < 0.2 or Audio Acousticness 0.4 < x < 0.7 \n')
        keys = userToAdd.split()
        if(keys[0] == 'Year'):
            toAdd.extend(generated[keys[0]][int(keys[1])])
            description.append('Year {}'.format(int(keys[1])))
        elif(keys[0] == 'Genre'):
            toAdd.extend(generated[keys[0]][keys[1]])
            description.append(keys[1])
        elif(keys[0] == 'Popularity'):
            toAdd.extend(generated[keys[0]][int(keys[1])])
            description.append('Popularity {}'.format(int(keys[1])))
        elif(keys[0] == 'Audio'):
            #keys 2 and above cna be int or string - 0.2 or x < 0.2 or 0.2 < x < 0.3
            if len(keys) == 3: # Audio Tempo 0.2
                toAdd.extend(generated[keys[0]][keys[1]][float(keys[2])])
                description.append('{} {}'.format(keys[1], float(keys[2])))
            elif len(keys) == 5: # Audio Tempo x < 0.2
                #iterate over generated[keys[0]][keys[1]] and if lessthan or greater than keys[4]
                # then add
                if keys[3] == '<':
                    description.append('{} less than {}'.format(keys[1], float(keys[4])))
                else:
                    description.append('{} greater than {}'.format(keys[1], float(keys[4])))

                for numbers in generated[keys[0]][keys[1]]:
                    if keys[3] == '<':
                        if numbers < float(keys[4]):
                            toAdd.extend(generated[keys[0]][keys[1]][numbers])
                    elif keys[3] == '>':
                        if numbers > float(keys[4]):
                            toAdd.extend(generated[keys[0]][keys[1]][numbers])
                    else:
                        return
            elif len(keys) == 7: # Audio Tempo 0.3 < x < 0.5
                description.append('{} ({}, {})'.format(keys[1], keys[2], keys[6]))
                for numbers in generated[keys[0]][keys[1]]:
                    # assume both are < cuz otherwise stupid
                    if keys[3] == keys[5] and keys[5] == '<':
                        if numbers < float(keys[6]) and numbers > float(keys[2]):
                            toAdd.extend(generated[keys[0]][keys[1]][numbers])
                    else:
                        print('Wrong format, left to right dumbo, _ < _ < _ -> format like 0.3 < x < 0.5')
        userInput = input('Add more? (yes or no) ')

    #remove duplicates
    removedDuplicates = list(dict.fromkeys(toAdd)) # makes a dictionary of the ids, so removes duplicates
    
    title = input('Name of the playlist: ')
    today = date.today()
    # dd/mm/YY
    dateToday = today.strftime("%d/%m/%Y")
    description.append('Created on {}'.format(dateToday))
    outDescription = '; '.join(description)
    # create a playlist and add these songs
    sp.user_playlist_create(username, title, True, outDescription)

    # get new playlist id
    newPlaylistID = getUserPlaylistID(title)
    if(newPlaylistID is False):
        print('Unable to get new Playlist ID')
        return
    
    addingSongs = divideList(removedDuplicates, 100) # divide to size 100, lists
    # add songs to playlist
    for lists in addingSongs:
        sp.user_playlist_add_tracks(username, newPlaylistID, lists)


# starts the program
if __name__ == "__main__":
    start()

# some saved songs dont update - not in csv even after saving - have to unlike and then like again then save for it to update
# SOME SONGS ARE UNAVAILABLE, gREYED OUT ON SPOTIFY, NOT AVAILABLE IN US?? IS THAT WHY NOT ALL SONGS GET SAVED TO A PLAYLIST OR WHATEV??
