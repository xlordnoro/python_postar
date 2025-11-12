# Modifications needed inside the script (very few are required)
To edit the python script, you can use IDLE which is installed alongside python by default, but you can use notepad++ as well.
Near the top of the script, you'll see a bunch of variables (B2_SHOWS_BASE, B2_TORRENTS_BASE). You'll need to update the b2 paths to reflect where you store the files in your b2 bucket.
I put mine in shows and torrents to keep the main files and torrents separate from each other.
The last thing you'll need to change is the ENCODER_NAME variable to match your name. That's used when creating the encoding settings table. Otherwise, it'll
always show my name instead of yours.

# Everyone's got a basic bitch nearby, right? The bare minimum needed to run the script.

python python_postar_v32.py -p "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" -a "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c red -m 59457 -o test_v32.txt

# This command increases the post to 2 series/seasons. Most of the commands allow more than one btw.

python python_postar_v32.py -p "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_1080p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_1080p]" -a "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue red -m 42310 59457 -o test_v32.txt

# This command increases the post to 3 series/seasons.

python python_postar_v32.py -p "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_1080p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_1080p]" -a "https://i.imgur.com/Y4aH7ZB.jpg" "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue green red -m 41623 42310 59457 -o test_v32.txt

# This command shows 3 series/seasons and multiple donation images. Only the first donation image remains visible outside of the button.

python python_postar_v32.py -p "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_1080p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_1080p]" -a "https://i.imgur.com/Y4aH7ZB.jpg" "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" "https://i.imgur.com/3ZRmC6U.jpg" "https://i.imgur.com/XZEGRLv.jpg" -c blue green red -m 41623 42310 59457 -o test_v32.txt

# This command shows the seasonal argument
python python_postar_v32.py -p "F:\test\[Hi10]_Airings_Folder_[1080p]" -a "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue -m 42310 -s -o test_v32_airing.txt

# Lastly, what in the holy fuck sort of black magic is this? Definitely not -8πα xD
# This is the only BD post example, but you can use multiple donation images with this command as well.
# As I stated in the args section, the bi images function as pairs. If you don't have enough images for all the seasons, it will loop the last two images to ensure something is there.

python python_postar_v32.py -p1080 "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_1080p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_1080p]" -p720 "F:\(Hi10)_Isekai_Maou_Omega_(BD_720p)" "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_720p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_720p]" -a "https://i.imgur.com/Y4aH7ZB.jpg" "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue green red -m 41623 42310 59457 -b -bi "https://imgur.com/vEZOJr3.jpg" "https://imgur.com/lKLs0hN.jpg" "https://imgur.com/Ho3EZDh.jpg" "https://imgur.com/BI8chCK.jpg" "https://imgur.com/y3hHGFU.jpg" "https://imgur.com/1yntsON.jpg" "https://imgur.com/c8YPCYN.jpg" "https://raw.githubusercontent.com/xlordnoro/xlordnoro.github.io/master/playcool_images/button_images/Hi10_Kanojo_S2_button_720p.jpg" -o test_v32.txt