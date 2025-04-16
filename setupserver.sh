#!/bin/bash
set -e

apt update
apt install -y wget tmux
wget https://download.oracle.com/java/24/latest/jdk-24_linux-x64_bin.deb
dpkg -i ./jdk-24_linux-x64_bin.deb
wget https://api.papermc.io/v2/projects/paper/versions/1.21.4/builds/173/downloads/paper-1.21.4-173.jar
mv paper-1.21.4-173.jar paperclip.jar
echo eula=true > eula.txt
echo java -Dfile.encoding=UTF-8 -Xmx30G -Xms15G -jar paperclip.jar > start.sh
chmod +x ./start.sh
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xzf ngrok-v3-stable-linux-amd64.tgz
chmod +x ./ngrok
./ngrok config add-authtoken 1sG77Yu0gc4U9QRyEW9BIpjAh1W_LQNFV9NyQWekE68tiHKK
tmux new-sessopn -d -s ngrok './ngrok tcp 25565'
tmux new-session -d -s mcserver './start.sh'