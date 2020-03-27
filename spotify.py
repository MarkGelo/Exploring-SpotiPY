import spotipy
import json
import csv
import os
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util

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
        3 - Copy a playlist (name, description, remove saved songs, public or private)
        4 - Update a playlist
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
            copyPlaylists(name, description, remove, public)
        elif(choice == '4'):
            playlist = input('Input the playlist you want to remove saved songs ')
            updatePlaylist(playlist)
        elif(choice == 'S'):
            writeSaved()
        else:
            print('Invalid choice dimwit')
            break

# starts the program
if __name__ == "__main__":
    start()

# some saved songs dont update - not in csv even after saving - have to unlike and then like again then save for it to update
