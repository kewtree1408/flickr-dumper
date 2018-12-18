#!/usr/bin/env python3
'''
Download the whole Flickr library on your local disk.
'''

import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
import webbrowser
from functools import partial

import flickrapi
import requests

logger = logging.getLogger()
# Global session: http://docs.python-requests.org/en/master/user/advanced/
url_photo_session = requests.Session()


def setup_logging():
    """
    Set up info/debug to log
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    format_schema = '[%(levelname)s] [%(filename)s/%(funcName)s]:\n%(asctime)s:%(message)s'
    formatter = logging.Formatter(format_schema)

    output = logging.StreamHandler(sys.stdout)
    output.setLevel(logging.INFO)

    logfile = logging.FileHandler('debug.log')
    logfile.setLevel(logging.DEBUG)

    output.setFormatter(formatter)
    logfile.setFormatter(formatter)

    root.addHandler(output)
    root.addHandler(logfile)


def authorize():
    """
    Get access token and use it for future requests
    :return FlickrAPI object
    """
    api_keys = {}
    with open('api_secrets.json', 'r') as f_api:
        api_keys = json.loads(f_api.read())

    flickr = flickrapi.FlickrAPI(api_keys['api_key'], api_keys['api_secret'], format='parsed-json')
    if not flickr.token_valid(perms='read'):
        flickr.get_request_token(oauth_callback='oob')
        authorize_url = flickr.auth_url(perms='read')
        webbrowser.open_new_tab(authorize_url)
        verifier = str(input('Verifier code: '))
        flickr.get_access_token(verifier)

    logger.info('Authorization was successful')
    return flickr


def create_flickr_url(farm_id, server_id, photo_id, original_secret):
    """
    Build the custom url by rules:
    https://www.flickr.com/services/api/misc.urls.html
    """
    return f'https://farm{farm_id}.staticflickr.com/{server_id}/{photo_id}_{original_secret}_o.jpg'


def save_image(flickr, directory, photo_id, photo_secret):
    """
    Save image on local storage
    """

    # https://www.flickr.com/services/api/flickr.photosets.getInfo.html
    photo_info = flickr.photos.getInfo(photo_id=photo_id, secret=photo_secret)
    photo_data = photo_info['photo']
    original_secret = photo_data['originalsecret']
    url = create_flickr_url(photo_data['farm'], photo_data['server'], photo_id, original_secret)

    response = url_photo_session.get(url, stream=True)
    with open(f'{directory}/img_{photo_id}.jpg', 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response

    with open(f'{directory}/stats.log', 'a+') as f:
        f.write(f'{photo_id}\n')


def save_page(flickr, directory_name, saved_data_set, my_user_id, photoset_id, page, per_page):
    """
    Download all photo from set by current page and save on local storage
    """

    # https://www.flickr.com/services/api/flickr.photosets.getPhotos.html
    photos = flickr.photosets.getPhotos(
        user_id=my_user_id, photoset_id=photoset_id, page=page, per_page=per_page
    )
    photos = photos['photoset']['photo']

    for photo in photos:
        # if the photo was already downloaded,
        # then not save it
        if photo['id'] in saved_data_set:
            continue
        save_image(flickr, directory_name, photo['id'], photo['secret'])

        logger.info('Image %s was saved', photo['id'])
    logger.info('The whole %s page was saved', page)


@asyncio.coroutine
def main(dirname):
    """
    The main couroutine.
    It will get the main loop and run every blocking task on async way.
    """
    flickr = authorize()

    user = flickr.test.login()
    my_user_id = user['user']['id']
    saved_data_set = set()
    per_page = 500

    kwargs = {
        'saved_data_set': saved_data_set,
        'directory_name': dirname,
        'flickr': flickr,
        'per_page': per_page,
        'my_user_id': my_user_id,
    }

    # https://www.flickr.com/services/api/flickr.photosets.getList.html
    sets = flickr.photosets.getList(user_id=my_user_id)

    loop = asyncio.get_event_loop()
    for photoset in sets['photosets']['photoset']:
        pages_per_set = int(photoset['photos'] / per_page) + 1
        kwargs['photoset_id'] = photoset['id']
        for page in range(pages_per_set):
            kwargs['page'] = page
            loop.run_in_executor(None, partial(save_page, **kwargs))


def parse_args():
    """
    Parse args
    """
    parser = argparse.ArgumentParser(description='Set up settings for Flickr-dumper')
    parser.add_argument(
        '-d', '--dirname', type=str, default='photos', help='Directory name for future photos'
    )
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()

    if not os.path.exists(args.dirname):
        os.makedirs(args.dirname)

    main_loop = asyncio.get_event_loop()
    main_loop.run_until_complete(main(args.dirname))
    main_loop.close()
