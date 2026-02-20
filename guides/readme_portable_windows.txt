# Everyone's got a basic bitch nearby, right? The bare minimum needed to run the script.

python_postar.exe -p "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" -a "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c red -m 59457 -o test_v51.txt

# This command increases the post to 2 series/seasons. Most of the commands allow more than one btw.

python_postar.exe -p "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_1080p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_1080p]" -a "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue red -m 42310 59457 -o test_v51.txt

# This command increases the post to 3 series/seasons.

python_postar.exe -p "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_1080p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_1080p]" -a "https://i.imgur.com/Y4aH7ZB.jpg" "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue green red -m 41623 42310 59457 -o test_v51.txt

# This command shows 3 series/seasons and multiple donation images. Only the first donation image remains visible outside of the button.

python_postar.exe -p "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_1080p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_1080p]" -a "https://i.imgur.com/Y4aH7ZB.jpg" "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" "https://i.imgur.com/3ZRmC6U.jpg" "https://i.imgur.com/XZEGRLv.jpg" -c blue green red -m 41623 42310 59457 -o test_v51.txt

# This command shows the seasonal argument
python_postar.exe -p "F:\test\[Hi10]_Airings_Folder_[1080p]" -a "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue -m 42310 -s -o test_v51_airing.txt

# This command will show the version of the script running.

python_postar.exe -v

# This command will add a crc32 hash column to the episodes table. By default, this option is off since crc32 hashes are included in the files directly.

python_postar.exe -p "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" -a "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c red -m 59457 -crc -o test_v51.txt

# This command shows the configure argument

python_postar.exe -p "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" -a "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c red -m 59457 -configure -o test_v51.txt

# This command shows the kage argument. This can be used with BD posts as well.

python_postar.exe -p "F:\test\[Hi10]_Airings_Folder_[1080p]" -a "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue -m 42310 -kage -o test_v51_kage.txt

# Lastly, what in the holy fuck sort of black magic is this? Definitely not -8πα xD
# This is the only BD post example, but you can use multiple donation images with this command as well.
# As I stated in the args section, the bi images function as pairs. If you don't have enough images for all the seasons, it will loop the last two images to ensure something is there.

python_postar.exe -p1080 "F:\(Hi10)_Isekai_Maou_Omega_(BD_1080p)" "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_1080p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_1080p]" -p720 "F:\(Hi10)_Isekai_Maou_Omega_(BD_720p)" "F:\(Hi10)_Cyberpunk_Edgerunners_(BD_720p)" "F:\[Hi10]_Haite_Kudasai_Takamine_San_[BD_720p]" -a "https://i.imgur.com/Y4aH7ZB.jpg" "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" "https://i.imgur.com/9yUGQIF.jpg" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue green red -m 41623 42310 59457 -b -bi "https://imgur.com/vEZOJr3.jpg" "https://imgur.com/lKLs0hN.jpg" "https://imgur.com/Ho3EZDh.jpg" "https://imgur.com/BI8chCK.jpg" "https://imgur.com/y3hHGFU.jpg" "https://imgur.com/1yntsON.jpg" -o test_v51.txt
