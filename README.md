# Spotipy program for your playlists
A program that will allow you to organize and create playlists.\
The program uses Spotify API and Last.fm API (to get genres of songs)\
To start the program, first populate the required components such as client id, client secret, spotify username, redirect_uri (can be anything), and last_fm_api_key either directly in the source code, or in a csv file in the format: 
```
username,cid,secret,redirect_uri,last_fm_api_key
xxxxxxx,yyyyy,zzzzz,google.com,aaaaaaaaaaaaaaaaaaa
```
Then run spotify.py and follow the instructions on the command line.

# AWS Lambda
The script will run once a week and update certain playlists. The playlists to be updated are hardcoded in and has all the relevant info needed. Using AWS SNS, I also set it up so that when the script fails, it will send an email to me.

# Set up in AWS Lambda
Set up the dynamodb tables called Spotify and SpotifyGenre. Spotify table has user and accessKey. SpotifyGenre table has songID and genres (stringSet).\
Insert the lambda_function.py and all the relevant dependencies in one folder and then zip. Import the zip to a function in AWS Lambda.\
Set the environment variables (spotify cid, redirect_uri, refresh_token, secret, username, and also Last.fm api key)\
Add a trigger for the function (CloudWatch Events for timers such as every week)\
Optional - Add a destination such as Amazon SNS to email you on success/failure of the function