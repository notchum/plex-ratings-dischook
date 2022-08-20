import os
import json
import base64
import requests
from datetime import datetime, timezone
from flask import Flask, request, abort
from ratelimit import limits, sleep_and_retry

app = Flask(__name__)
poster_delete_hash = None

LIMIT_CALLS = 5
LIMIT_PERIOD = 60 * LIMIT_CALLS

IMDB_GUID_INX = 0
TMDB_GUID_INX = 1
TVDB_GUID_INX = 1


def upload_to_imgur(img_data, img_title='', rating_key='', fallback=''):
    """ Uploads an image to Imgur """
    img_url = delete_hash = ''

    headers = {'Authorization': f"Client-ID {os.environ['IMGUR_CLIENT_ID']}"}
    data = {'image': base64.b64encode(img_data),
            'title': img_title.encode('utf-8'),
            'name': str(rating_key) + '.png',
            'type': 'png'}

    response = requests.post('https://api.imgur.com/3/image', headers=headers, data=data)

    if (response and response.status_code == 200):
        print(f"DEBUG :: Image '{img_title}' ({fallback}) uploaded to Imgur.")
        imgur_response_data = response.json().get('data')
        img_url = imgur_response_data.get('link', '').replace('http://', 'https://')
        delete_hash = imgur_response_data.get('deletehash', '')
    else:
        print(f"ERROR :: Unable to upload image '{img_title}' ({fallback}) to Imgur.")
        print(f"ERROR :: Request response: {response.status_code} {response.reason}")

    return img_url, delete_hash


def delete_from_imgur(delete_hash, img_title='', fallback=''):
    """ Deletes an image from Imgur """
    headers = {'Authorization': f"Client-ID {os.environ['IMGUR_CLIENT_ID']}"}

    response = requests.delete(f"https://api.imgur.com/3/image/{delete_hash}", headers=headers)

    if (response and response.status_code == 200):
        print(f"DEBUG :: Image '{img_title}' ({fallback}) deleted from Imgur.")
        return True
    else:
        print(f"ERROR :: Unable to delete image '{img_title}' ({fallback}) from Imgur.")
        print(f"ERROR :: Request response: {response.status_code} {response.reason}")
        return False


@limits(calls=LIMIT_CALLS, period=LIMIT_PERIOD)
def send_to_discord(data: dict):
    response = requests.post(
        url=os.environ['DISCORD_WEBHOOK'],
        data=json.dumps(data),
        headers={'Content-Type': 'application/json'}
    )

    if (response.status_code not in [200, 204]):
        raise Exception(f"API response: {response.status_code}")
    return response


@app.route('/plex', methods=['POST'])
def get_webhook():
    if (request.method == 'POST'):
        payload = attrdict(json.loads(request.values['payload']))
        print(f"Got webhook for {payload.event}")
        
        # If the event is a rating
        if (payload.event == "media.rate"):
            # Get Poster
            if ('grandparentThumb' in payload.Metadata):
                img_split = payload.Metadata.grandparentThumb.split('/')
            elif ('parentThumb' in payload.Metadata):
                img_split = payload.Metadata.parentThumb.split('/')
            else:
                img_split = payload.Metadata.thumb.split('/')
            if (img_split[-1].isdigit()):
                img = '/'.join(img_split[:-1])
            rating_key = img_split[3]
            img = f"{img.rstrip('/')}/{int(datetime.now().timestamp())}"
            url = os.environ['PLEX_HOSTNAME_PORT'] + img + "?X-Plex-Token=" + os.environ['X_PLEX_TOKEN']
            result = requests.get(url=url)

            # Delete last poster image
            global poster_delete_hash
            if (poster_delete_hash):
                delete_from_imgur(delete_hash=poster_delete_hash)
            
            # Upload poster image
            if (result.status_code == 200):
                poster_url, poster_delete_hash = upload_to_imgur(img_data=result.content, rating_key=rating_key)

            # Configure the Title
            if (payload.Metadata.librarySectionType == "show"):
                if ('Guid' in payload.Metadata):
                    media_db_url = f"[TheTVDB](https://thetvdb.com/?tab=series&id={payload.Metadata.Guid[TVDB_GUID_INX].id.split('//')[-1]})"
                else:
                    media_db_url = f"[TheTVDB](https://thetvdb.com/?tab=series&id={payload.Metadata.guid.split('//')[-1].split('?')[0].split('/')[0].split('-')[-1]})"
                if (payload.Metadata.type == "episode"):
                    payload.Metadata.title = f"{payload.Metadata.grandparentTitle} - {payload.Metadata.title} (S{payload.Metadata.parentIndex} · E{payload.Metadata.index})"
                elif (payload.Metadata.type == "season"):
                    payload.Metadata.title = f"{payload.Metadata.parentTitle} - {payload.Metadata.title}"
            elif (payload.Metadata.librarySectionType == "movie"):
                media_db_url = f"[IMDb](https://www.imdb.com/title/{payload.Metadata.Guid[IMDB_GUID_INX].id.split('//')[-1]})"
            else:
                print(f"ERROR :: {payload.Metadata.librarySectionType} is not handled!")

            # Correct 0 ratings
            if (payload.rating < 0):
                payload.rating = 0

            data = {
                'embeds': [
                    {
                        "title": f"{payload.Account.title} rated {payload.Metadata.title}!",
                        "fields": [
                            {
                                "name": "Description",
                                "value": payload.Metadata.summary if payload.Metadata.summary else "N/A"
                            },
                            {
                                "name": "Rating",
                                "value": f"{int(payload.rating)}/10",
                                "inline": True
                            },
                            {
                                "name": "Audience Rating",
                                "value": f"{payload.Metadata.audienceRating}/10" if 'audienceRating' in payload.Metadata else "N/A",
                                "inline": True
                            },
                            {
                                "name": "View Details",
                                "value": media_db_url,
                                "inline": True
                            }
                        ],
                        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:00.000Z"),
                        "image": {
                            "url": poster_url
                        },
                        "thumbnail": {
                            "url": payload.Account.thumb
                        }
                    }
                ]
            }

            _ = send_to_discord(data)
        return 'Success!', 200
    else:
        abort(400)


class attrdict(dict):
    """
    Attribute Dictionary.

    Enables getting/setting/deleting dictionary keys via attributes.
    Getting/deleting a non-existent key via attribute raises `AttributeError`.
    Objects are passed to `__convert` before `dict.__setitem__` is called.

    This class rebinds `__setattr__` to call `dict.__setitem__`. Attributes
    will not be set on the object, but will be added as keys to the dictionary.
    This prevents overwriting access to built-in attributes. Since we defined
    `__getattr__` but left `__getattribute__` alone, built-in attributes will
    be returned before `__getattr__` is called. Be careful::

        >>> a = attrdict()
        >>> a['key'] = 'value'
        >>> a.key
        'value'
        >>> a['keys'] = 'oops'
        >>> a.keys
        <built-in method keys of attrdict object at 0xabcdef123456>

    Use `'key' in a`, not `hasattr(a, 'key')`, as a consequence of the above.
    """
    def __init__(self, *args, **kwargs):
        # We trust the dict to init itself better than we can.
        dict.__init__(self, *args, **kwargs)
        # Because of that, we do duplicate work, but it's worth it.
        for k, v in self.items():
            self.__setitem__(k, v)

    def __getattr__(self, k):
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            # Maintain consistent syntactical behaviour.
            raise AttributeError(
                "'attrdict' object has no attribute '" + str(k) + "'"
            )

    def __setitem__(self, k, v):
        dict.__setitem__(self, k, attrdict.__convert(v))

    __setattr__ = __setitem__

    def __delattr__(self, k):
        try:
            dict.__delitem__(self, k)
        except KeyError:
            raise AttributeError(
                "'attrdict' object has no attribute '" + str(k) + "'"
            )

    @staticmethod
    def __convert(o):
        """
        Recursively convert `dict` objects in `dict`, `list`, `set`, and
        `tuple` objects to `attrdict` objects.
        """
        if isinstance(o, dict):
            o = attrdict(o)
        elif isinstance(o, list):
            o = list(attrdict.__convert(v) for v in o)
        elif isinstance(o, set):
            o = set(attrdict.__convert(v) for v in o)
        elif isinstance(o, tuple):
            o = tuple(attrdict.__convert(v) for v in o)
        return o

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
