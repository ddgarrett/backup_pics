# Backup Pics
Automatically backup pictures. [config.json](config.json) defines image sources and secondary backup drives.
Workflow is to attach a phone or camera SD card. Any new pictures will be copied to a backup directory 
on the Raspberry Pi 5 SSD. Secondary backup drives can then be attached to the Raspberry Pi
and new pictures will be copied to those drives.

Created for Raspberry Pi 5 (RPi5) with 2 TB SSD.

Backup program automatically starts when RPi5 is booted.

Multiple external backup drives can be used, such as a travel SSD 
and a home based magnetic hard drive.

Optionally, deleting pictures from the photo/video source can be done after photos have been
backed up to RPi5 or backed up to a given external backup drive.

---

* Autostart backup currently runs `main.py`

* In process: adding menu to allow start/stop processes for backup and image quality evaluation
    * `cursor` prompts defining menu in [v001.000.001 notes](notes/v001.000.001%20add%20menu%20for%20backup%20and%20pic%20review.md)
    * `menu.py` displays menu and starts backup process defined in `backup_process.py`
    * `backup_process.py` - starts/stops `main.py`
    * `pic_quality_review.py` - currently placeholder for quality review
    

* Image eval testing version 1 uses **CLIP-IQA** and **MUSIQ**
    * `cursor` prompts in [v001.000.002 notes](notes/v001.000.002_cursor_image_evaluation.md)
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

