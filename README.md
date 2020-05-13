# Spotipy program for your playlists
A program that will allow you to somewhat organize and create playlists.\
To start the program, first populate the required components such as client id, client secret, spotify username, and redirect_uri (can be anything) either directly in the source code, or in a csv file in the format: 
```
username,cid,secret,redirect_uri
xxxxxxx,yyyyy,zzzzz,google.com
```
Then run spotify.py and follow the instructions on the command line.\

# AWS Lambda
The script will run once a week and update certain playlists. The code is simple but all over the place because I was lazy at the time. Maybe I will organize it and make it beautiful in the future. It does what I want it to do, and at the time, that's all that I want. (05-13-2020)