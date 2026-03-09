# backup_pics
Automatically backup pictures.

Created for Raspberry Pi 5 (RPi5) with 2 TB SSD.

Program automatically starts when RPi5 is booted.

When a known photo/video source, such as a cell phone or sd card,
is mounted via USB, copy images/videos from specified
folder(s) into a backup folder.

When a known external backup drive is attached to the RPi5, copy any new 
files from the backup folder on RPi5 to the external backup drive.

Multiple external backup drives can be used, such as a travel SSD 
and a home based magnetic hard drive.

Optionally, deleting pictures from the photo/video source can be done after photos have been
backed up to RPi5 or backed up to a given external backup drive.

---

* Above is run from `main.py`

* Adding Menu to allow start/stop 2 processes: backup and quality eval 
    * `cursor` prompts in [notes](notes/v001.000.001%20add%20menu%20for%20backup%20and%20pic%20review.md)
    * `menu.py` displays menu and starts backup process defined in `backup_process.py`
    * `backup_process.py` - starts/stops `main.py`
    * `pic_quality_review.py` - currently placeholder for quality review
    

* Image eval testing version 1 uses **CLIP-IQA** and **MUSIQ**
    * `cursor` prompts in [notes](notes/v001.000.002_cursor_image_evaluation.md)
    * description of install and running is in `IMAGE_EVALUATOR_README.md`
    * pip install details in `requirements_image_evaluator.txt`
    * `image_evaluator.py` is the image evaluator python program 
    * to run use
        * `python image_evaluator.py /home/dgarrett/Documents/pictures/MEDIA_BACKUP/yyyy-mm-dd_backup`
        * optional parm to speed up evaluation: `--max-size 384`
        * default is `--max-size 512`
        * use full size: `--max-size 0`
        * want to try 1024 and 768 to see affect on scores

* Image eval v2 - use **NIMA**
    * test speed
    * may eventually use a combination, with fast initial review followed by more detailed review
    * see [Claude AI Comparison](https://claude.ai/share/c3d85d17-36ee-4b79-a74b-419d551396dc)

