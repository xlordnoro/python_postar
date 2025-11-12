# python_postar
A modern version of postar written in python

# Version
The script is currently at version **32**.

# Installation
Any modern stable version of python will work with this project. At the time of writing this guide, it's currently 3.13.9.

I've included a written guide and command readme in the guides folder which will break things down more than the version below which covers the bare minimum needed to get the project running on windows or linux.

**Linux users are unaffected by system path issues since python is automatically added to the system path by default and can skip the notice below.**

**IMPORTANT NOTICE FOR WINDOWS USERS!**
**MAKE SURE YOU CHECK THE BOX LABELED "ADD PYTHON TO SYSTEM PATH" IN THE PYTHON INSTALLER. WITHOUT THAT SETUP, YOU WON'T BE ABLE TO CALL PYTHON OR PIP GLOGALLY ON YOUR SYSTEM.**

Once python is fully installed, run the following command in cmd, powershell, or terminal if you're running windows 11 to install the required pip libraries.
NOTE: You can also run pip install -r requirements.txt if you're running the terminal window in the same location as the folder containing python postar to achieve the same result.

**pip install requests pymediainfo**

If you get a message about updating pip after install requests and pymediainfo, feel free to update that while the terminal window is still active. However, it's not required for postar to function properly.

# Args breakdown
**The script does have some required arguments that are needed for it to run.**
**It needs -p -a -d -m -c and if one or more is missing it will produce an error stating what is required to run.**

 -p is the paths argument for non-BD's and that will point to the folder(s) you want to make a post for on the site.
 -p1080 & -p720 are also path arguments, but these are strictly meant for BD posts since I needed a way for the script to map where the folders should be placed in the post code.
 -a is for the airing/cover image.
 -d is for the donation image.
 -m is for the mal-id which is used to grab the titles and synopsis directly from mal's API backend.
 e.g. https://myanimelist.net/anime/42310/Cyberpunk__Edgerunners the id is: 42310
 -c is for the span color on the table headers for the title of the series/season.
 -b is used to tell the script that it's a bd post vs a non-BD post
 -bi is for the resolution button images which function in pairs 1080p 720p, 1080p 720p, etc. The order does matter if u want them to be in the proper place!
 -s is used to tell the script that it's a seasonal airings post and to sort the entries by series instead of the episode number first (Pcool airings)
 -o allows you to change the filename of the txt file that is going to be generated.

# Windows Command Examples
python python_postar_v32.py -p "F:/test/(Hi10)_Airings_Folder_(1080p)/" -a "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue -m 42310 -o test_v32_airing.txt

# Linux Command Examples
python3 python_postar_v32.py -p "/home/noro/(Hi10)_Airings_Folder_(1080p)/" -a "https://cdnb.artstation.com/p/assets/images/images/054/613/745/large/indy-kaunang-lucy.jpg?1664941163" -d "https://i.imgur.com/Hb0yVs1.jpg" -c blue -m 42310 -o test_v32_airing.txt