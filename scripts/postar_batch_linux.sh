#!/usr/bin/sh
# Make sure you run sudo chmod +x postar_batch_linux.sh before running the script or you'll receive an execute permissions error.
# Example path /home/noro/(Hi10)_Isekai_Maou_Omega_(BD_1080p)

python3 python_postar.py -p "/path/to/folder" -a "https://i.imgur.com/Y4aH7ZB.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue -m 41623 -o isekai_maou_omega.txt
python3 python_postar.py -p "/path/to/folder" -a "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" -d "https://i.imgur.com/Hb0yVs1.jpg" -c green -m 42310 -o cyberpunk_edgerunners.txt
python3 python_postar.py -p "/path/to/folder" -a "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c red -m 59457 -o takamine_san.txt
python3 python_postar.py -p "/path/to/folder" -a "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c red -m 10087 -o fate_zero.txt
python3 python_postar.py -p "/path/to/folder" -a "https://i.imgur.com/Y4aH7ZB.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue -m 41623 -o isekai_maou_omega_test.txt
python3 python_postar.py -p "/path/to/folder" -a "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" -d "https://i.imgur.com/Hb0yVs1.jpg" -c green -m 42310 -o cyberpunk_edgerunners_test.txt
python3 python_postar.py -p "/path/to/folder" -a "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c red -m 59457 -o takamine_san_test.txt
python3 python_postar.py -p "/path/to/folder" -a "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c red -m 10087 -o fate_zero_test.txt

#Add a pause in the event an error is triggered so the user can debug the problem instead of closing immediately.
read -s -n 1 -p "Press any key to continue . . ."
