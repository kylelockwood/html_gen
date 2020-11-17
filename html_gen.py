#! python3
"""
Script to gather meta data from a video link and create html iframes and posts
Additionally, downloads thumbnail images of linked video
"""

import urllib.request
import urllib
import sys
import os
import json
import datetime as dt
import html
from copy import deepcopy
import pyperclip
from bs4 import BeautifulSoup

# TODO build function to replace ann, zzz, event, etc DRY

class HTML_Generator:
    def __init__(self, dbfile, outpath=''):
        self.dbfile = dbfile

        self.scriptpath = os.path.dirname(os.path.realpath(sys.argv[0])) + '\\' # This is necessary because of the environmental variable call
        if outpath:
            outpath = outpath + '\\'
        self.outpath = 'C:' + os.environ["HOMEPATH"] + '\\Desktop\\' + outpath # Default outpath is Desktop
        self.help = ('Usage: tochtml <url> <key>   or   tochtml <command>\n'
                     '  <url>              - accepts youtube and facebook video urls, as well as zoom meeting urls\n'
                     '  <key>              - where to store url data.  Leaving this argument blank will display choices\n'
                     '  list               - displays current json data relevant to operation\n'
                     '  listall            - displays ALL current json data\n'
                     '  blank <key>        - sets empty strings to data in a key\n'
                     '  -<new title> <key> - replaces the title attribute in the <key>.  Will return to default after link update\n'
                     '  build              - creates document titled \'BUILD_<timestamp>.txt\' containing relevant json data formatted for html\n'
                     '  event <key>        - creates document titled \'EVENT_<timestamp>.txt\' containing html and social media posts for <key> event\n'
                     '  zzz                - creates document titled \'ZZZ_<timestamp>.txt\' containing html and social media posts for Zecond Zunday Zoom\n'
                     '  ann                - creates document titled \'ANN_<timestamp>.txt\' containing html and social media posts for Announcements\n'
                     '  ytlinks            - copies \'kids\', \'elem\', and \'ms\' links to the clipboard for YouTube description\n'
                     '  fbpost <type>      - allowed types are "serv", "ann" or "ev" with optional sub key, copies relevant Facebook post to the clipboard\n'
                     '  instapost <type>   - allowed types are "serv" , "ann" or "ev" with optional sub key, copies relevant Instagram post to the clipboard\n'
                     '  sig                - copies standard post signature to the clipboard\n'
                     '  <zoom url> <key>   - adds zoom urls to associated key in database. Optional sub key as arg3\n'
                     '  frame <key>        - creates iframe html associated with key, including title and description, and copies to the clipboard\n'
                     '  thumb <key>        - downloads thumbnail image associated with <key>\n'
                     '  thumbs             - downloads ALL thumbnail images from videos in database\n'
                    )
        self.default_keys = {'kids' : ['kids', 'elem', 'ms'],
                             'main' : ['main', 'kids', 'elem', 'ms', 'ann'],
                             'service' : ['service', 'main', 'kids', 'elem', 'ms'],
                             'build' : ['main', 'kids', 'elem', 'ms']}
        self.default_title = {'main' : 'SUNDAY SERVICE',
                              'kids' : 'PRE-K VIDEO',
                              'elem' : 'ELEMENTARY VIDEO',
                              'ms' : 'MIDDLE SCHOOL VIDEO',
                              'ann' : 'ANNOUNCEMENTS',
                              'fb' : 'LIVE UPDATES'}
        self.zoom_titles = [('main', 'Zecond. Zunday. Zoom(v.)'),
                            ('kids', 'Kid\'s Community Zoom'),
                            ('ms', 'Middle School Ministry Zoom')]
        self.vidtype = None
        self.app()

    def app(self):
        print('Loading data...')
        self.db = self._load_json_(self.dbfile)
        self.args = self._validate_inputs()
        print('Updating data...')
        self._update_db_()
        print('Saving data...')
        self._update_json(self.args[1])

    def _validate_inputs(self):
        """Returns argv[1] and argv[2] after ensuring proper usage and formatting"""
        if len(sys.argv) < 2 or sys.argv[1].lower() == 'help':
            sys.exit(self.help)
        arg1 = sys.argv[1]
        try:
            arg2 = sys.argv[2]
        except IndexError:
            arg2 = None
        try:
            arg3 = sys.argv[3]
        except IndexError:
            arg3 = None
        if arg1 == 'listall':
            # list current data in JSON
            sys.exit(self._print_json_list())
        elif arg1 == 'list':
            sys.exit(self._print_json_list(keys=self.default_keys['service']))
        elif arg1 == 'build':
            self._build()
        elif arg1 == 'ytlinks':
            self._copy_links_(self.default_keys['kids'])
        elif arg1 == 'fbpost':
            post = self._fb_post_text(arg2, arg3)
            pyperclip.copy(post)
            sys.exit('Facebook post copied to clipboard.')
        elif arg1 == 'instapost':
            post = self._insta_post_text(arg2, arg3)
            pyperclip.copy(post)
            sys.exit('Instagram post copied to clipboard.')
        elif arg1 == 'sig':
            sig = self._post_signature()
            pyperclip.copy(sig)
            sys.exit('Post signature copied to clipboard.')
        elif arg1 == 'thumb':
            while True:
                if arg2 in self.db.keys():
                    try:
                        self._download_thumb(arg2)
                        sys.exit()
                    except:
                        sys.exit()
                else:
                    arg2 = self._invalid_key(arg2)
        elif arg1 == 'thumbs':
            for key in self.default_keys['main']:
                try:
                    self._download_thumb(key)
                except:
                    continue
            sys.exit()
        elif arg1 == 'frame':
            while True:
                if arg2 in self.db.keys():
                    pyperclip.copy(self._generate_video_html(arg2))
                    sys.exit('Video html copied to clipboard.')
                else:
                    arg2 = self._invalid_key(arg2)
        elif arg1 == 'zzz':
            self._build_zzz_html()
        elif arg1 == 'event':
            self._build_event(arg2)
        elif arg1 == 'ann':
            self._build_ann()
        elif arg1.startswith('www'):
            arg1 = 'https://' + arg1
        elif arg1.startswith('https://www.youtube.com'):
            arg1 = self._format_short(arg1)
        elif 'facebook' in arg1:
            self.vidtype = 'fb'
        elif 'zoom' in arg1:
            while True:
                if arg2 == 'event':
                    try:
                        key = arg3
                        if not key in self.db['event']:
                            sys.exit(f'\'{key}\' is not a valid key.')
                    except IndexError:
                        key = self._choose_key('event')
                    self.db['event'][key]['link'] = arg1
                    codes = self._get_zoom_codes(arg1)
                    self.db['event'][key]['id'] = codes[0]
                    self.db['event'][key]['pass'] = codes[1]
                    self._update_json(key)
                elif arg2 in self.db.keys():
                    self.db[arg2]['zoom'] = arg1
                    self._update_json(arg2)
                else:
                    arg2 = self._invalid_key(arg2)
        elif arg1.startswith('-'): # Renaming title
            return arg1, arg2
        elif arg1 == 'blank':
            arg1 = None
        elif arg1 and not arg1.startswith('https://'):
            sys.exit('Error, target must be a valid url or command.\n' + self.help)
        if arg2 is None or arg2 not in self.db.keys():
            arg2 = self._invalid_key(arg2)
        if not self.vidtype:
            self.vidtype = 'yt'
        return arg1, arg2

    def _build(self):
        """Create outfile that contains html for site update"""
        print('Build current list?')
        self._print_json_list(keys=self.default_keys['service'])
        build_keys = self.default_keys['build']
        kids_keys = self.default_keys['kids']
        yn = input('Y/N ')
        if yn.lower() == 'y':
            # FB Post
            text = self._build_social_media('serv')
            
            # Welcome page
            text += '\n\n\n== WELCOME PAGE ==\n\n'
            for key in build_keys:
                text += self._generate_video_html(key)

            # Online Services page
            text += '\n\n\n== ONLINE SERVICES PAGE ==\n\n'
            text += self._generate_video_html('main')

            # Past online services
            text += '\n\n\n== PAST ONLINE SERVICES ==\n\n'
            title = self.db['past']['main']['title']
            title = title.split(' - ')[0]
            text += self. _generate_past_kids('main', title=title)

            # If past links are the same as current from build, recall the previous links
            if self.db['last']['link'] == self.db['main']['link']:
                self.db['last'] = self.db['last_holder']
                self.db['past'] = self.db['past_holder']

            # Kids Community Videos
            text += '\n\n\n== KIDS COMMUNITY VIDEOS ==\n\n'
            text += '<p>Here you will find videos for the Kid\'s Community and Middle School Ministry.&nbsp; Full online service videos can be found in the <a href="/media/online-services" data-location="existing" data-detail="/media/online-services" data-category="link" target="_self" class="cloverlinks">MEDIA/ONLINE SERVICES</a> tab</p><p><br></p><p><br></p><p><br></p>'
            for key in kids_keys:
                text += self._generate_video_html(key)

            # Past Kid's Videos
            text += '\n\n\n== KIDS PAST VIDEOS ==\n\n'
            for key in kids_keys:
                text += self. _generate_past_kids(key)

            # Kids Community thumbs
            text += '\n\n\n== THUMBNAILS ==\n\n'
            for key in build_keys:
                text += self.db[key]['thumb'] + '\n'

            # Create output file
            self._create_txt_file_('BUILD', text)

            # Download the main service thumbnail
            self._download_thumb('main')

            # Thumbnails are generally downloaded earlier in the week to be used in the YT description,
            # so downloading them here is redundant. Leaving the code for future use.
            """
            # Download all thumbnails
            for key in build_keys:
                thumb = self.db[key]['thumb']
                self._download_thumb(key, thumb)
            """

            # Update json
            self._update_last()
            self._update_json()
        else:
            sys.exit()

    def _build_zzz_html(self):
        """Builds html and social media posts for Zecond Zunday Zoom service"""
        body = 'Around 10:30, kids will be "dismissed" during the service to join their own Zoom meetings lead by our Kid\'s Community and Middle School Ministry teams. You will need a separate Zoom account if you will be participating in the main service Zoom simultaneously.'
        text = '=== HOME PAGE ===\n\n'
        text += '<p style="font-size: 0.9722em;">'
        text += 'Click the Zoom links below to join! '  + body
        text += '</p><p style="font-size: 1.5278em;"><br></p><p style="font-size: 1.5278em;">10am Sunday</p><p style="font-size: 0.6944em;"><br></p>'
        for key, title in self.zoom_titles:
            url = self.db[key]['zoom']
            text += '<p><a href="'
            text += url
            text += '" class="cloverlinks" data-category="link" data-location="external" data-detail="'
            text += url
            text += '" target="_self" style="font-size: 1.25em;">'
            text += title
            text += ' - click here</a></p>'
            if key == 'main':
                text += '<p><br></p><p><br></p><p><br></p><p style="font-size: 1.5278em;">Around 10:30am</p><p style="font-size: 0.5556em;"></p>'
            elif key == 'kids':
                text += '<p><br></p>'

        text += '\n\n\n\n=== FB POST ===\n\n'
        text += 'ZECOND. ZUNDAY. ZOOM(V.) TODAY!\n\n'
        text += 'Click the Zoom links below to join! ' + body
        text += '\n\n10am Sunday\n'
        for key, title in self.zoom_titles:
            text += '\n' + title + '\n'
            text += self.db[key]['zoom']
            if key == 'main':
                text += '\n\nAround 10:30am\n'
            elif key == 'kids':
                text += '\n'

        text += '\n\n\n\n=== INSTA POST ===\n\n'
        text += 'ZECOND. ZUNDAY. ZOOM(V.) TODAY!\n\n'
        text += 'Visit our site for the links to join! ' + body
        text += '\n\n' + self._post_signature(insta=True)

        self._create_txt_file_('ZZZ', text)
        sys.exit()

    def _build_event(self, key=None):
        if not key:
            key = self._choose_key('event')
        elif key not in self.db['event']:
            sys.exit(f'\'{key}\' is not a valid key')
        db = self.db['event'][key]
        text = self._build_social_media('ev', key)
        text += '\n\n\n== HOMEPAGE HTML ==\n\n<p>'
        text += db['title']
        text += '</p><p>Click the image below or use the following Zoom info to log in!<br></p><p><br></p><p>id : '
        text += db['id']
        text += '</p>'
        text += '\n\n'
        text += db['link']
        self._create_txt_file_('EVENT', text)
        sys.exit()

    def _build_social_media(self, key=None, sub=None, custom_text=None):
        text = '== FACEBOOK POST ==\n\n'
        text += self._fb_post_text(key, sub, custom_text)
        text += '\n\n\n=== INSTAGRAM POST ===\n\n'
        text += self._insta_post_text(key, sub, custom_text)
        return text

    def _build_ann(self):
        db = self.db['ann']
        text = self._build_social_media('ann')
        text += '\n\n\n== HOMEPAGE HTML ==\n\n<p>'
        text += db['title']
        text += self._generate_video_html('ann')
        self._create_txt_file_('ANN', text)
        sys.exit()

    def _build_fb_links(self, name, embed):
        text = '== WELCOME PAGE ==\n\n'
        text += '<div><span class="clovercustom" style="font-size: 0.915em;">Get the latest updates from The Oregon Community staff here.  Past videos can all be found in the MEDIA tab or by clicking here.</span></div><div><br><br></div>\n'
        text += '<iframe src="'
        text += embed
        text += ';show_text=false&amp;width=734&amp;height=411&amp;appId" width="734" height="411" style="border:none;overflow:hidden" scrolling="no" frameborder="0" allowtransparency="true" allow="encrypted-media" allowfullscreen="true"></iframe>\n'
        text += '<p><br></p>\n'
        text += '<p style="font-size: 1.3072em;">'
        text += name
        text += '<br></p>'
        text += '\n\n\n== VIDEOS PAGE ==\n\n'

        # Update facebook html file
        filename = 'fb_iframe.txt'
        with open(self.outpath + filename, 'w') as f:
            f.writelines(text)
        pyperclip.copy(text)
        print(filename + ' updated. iframe copied to clipboard.')

    def _choose_key(self, sub=None):
        """ Choose a key """
        db = self.db
        if sub:
            db = self.db[sub]
        print('Please choose from the following keys:')
        for key in db:
            print(f'  {key}')
        while True:
            k = input('Leave blank to exit : ')
            if k in db:
                return k
            elif not k:
                sys.exit()
            print(f'\'{k}\' is not a valid option')

    def _fb_post_text(self, post_type, key=None, custom_text=None):
        """Returns the text for a FB post"""
        if post_type == 'serv':
            post = 'The Oregon Community at home\n\n'
            post += self.db['main']['name'] + '\n'
            post += self.db['main']['link']
            for key in self.default_keys['kids']:
                if self.db[key]['link']:
                    post += '\n\n'
                    post += self.db[key]['title'] + '\n'
                    post += self.db[key]['link']
        elif post_type == 'ann':
            post = self.db['ann']['name'] + '\n'
            post += self.db['ann']['link']
        elif post_type == 'ev':
            if not key:
                key = self._choose_key('event')
            post = self.db['event'][key]['title'] + '\n'
            post += self.db['event'][key]['link']

        else:
            sys.exit(f'\'{post_type}\' is not a valid post type.')

        sig = '\n\n' + self._post_signature()
        return post + sig

    def _insta_post_text(self, post_type, key=None, custom_text=None):
        if post_type == 'serv':
            post = 'The Oregon Community at home\n' + self.db['main']['name']
            post += '\nCheck out the video on our YouTube channel!'
        elif post_type == 'ann':
            post = self.db['ann']['name']
            post += '\nCheck out the video on our YouTube channel!'
        elif post_type == 'ev':
            if not key:
                key = self._choose_key('event')
            post = self.db['event'][key]['title']
            post += '\nLink on the Oregon Community site.'
        else:
            sys.exit(f'\'{post_type}\' is not a valid post type.')
        
        sig = '\n\n' + self._post_signature(insta=True)
        return post + sig

    def _download_thumb(self, key, thumb=None):
        """Downloads the image associated with passed thumbnail url to OUTPATH"""
        timestamp = dt.datetime.now().strftime('%m%d%Y_%H%M%S')
        filename = timestamp + '_' + key + '_thumb.jpg'
        if not thumb:
            thumb = self.db[key]['thumb']
        try:
            urllib.request.urlretrieve(thumb, self.outpath + filename)
            print(f'Thumbnail image \'{filename}\' successfully downloaded.')
        except:
            print(f'Failed to download thumbnail image \'{key}\'.')

    def _load_json_(self, filename):
        try:
            with open(self.scriptpath + filename) as f:
                data = json.load(f)
        except Exception as e:
            sys.exit(f'  Unable to load JSON data. {e}')
        return data

    def _update_db_(self):
        """Update links dict for key (arg1) """
        link = self.args[0]
        key = self.args[1]
        timestamp = dt.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
        if link is None:
            self._blank(key, timestamp)
            return
        elif link.startswith('-'): # Rename title command
            temp_title = link.split('-')[1]
            self.db[key]['title'] = temp_title
            print(f'    Title \'{temp_title}\' updated for \'{key}\'.')
            return
        else:
            self.db[key]['title'] = self.default_title[key]
        if self.vidtype == 'yt':
            meta = self._get_yt_meta_(link)
        elif self.vidtype == 'fb':
            meta = self._get_fb_meta_(link)
        self.db[key]['link'] = link

        # If one video for both age groups
        if not self.db['elem']['link']:
            self.db['kids']['title'] = 'KIDS COMMUNITY VIDEO'
            self.db['elem']['title'] = ''
        else:
            self.db['kids']['title'] = 'PRE-K VIDEO'
            self.db['elem']['title'] = 'ELEMENTARY VIDEO'

        self.db[key]['name'] = meta['name']
        self.db[key]['stamp'] = timestamp
        self.db[key]['id'] = meta['id']
        self.db[key]['date'] = meta['published']
        self.db[key]['thumb'] = meta['thumb']
        self.db[key]['embed'] = meta['embed']
        self.db[key]['vidtype'] = meta['vidtype']
        try:
            post_date = self.db['main']['date']
            dt_date = dt.datetime.strptime(post_date, '%Y-%m-%d')
        except:
            dt_date = dt.datetime.now()
        self.db['service']['date'] = self._get_sunday_date(dt_date)
        return

    def _create_txt_file_(self, title, text):
        # Create output file
        timestamp = dt.datetime.now().strftime('%m%d%Y_%H%M%S')
        filename = title + '_' + timestamp +'.txt'
        try:
            with open(self.outpath + filename, 'w') as f:
                f.writelines(text)
            print(f'\nFile \'{filename}\' sucessfully created in {self.outpath}.')
        except:
            print(f'\nFile \'{filename}\' could not be created.')

    def _copy_links_(self, keys):
        """Copies urls in keys to the clipboard"""
        content = ''
        outmessage = ''
        for key in keys:
            link = self.db[key]['link']
            if link:
                content += self.db[key]['title'] + '\n' + link +'\n\n'
                if key == keys[len(keys) -1]:
                    outmessage += ' and'
                outmessage += ' \'' + key + '\''
                if key != keys[len(keys) -1]:
                    outmessage += ','
        pyperclip.copy(content)
        sys.exit(f'Links for{outmessage} copied to clipboard.')

    def _update_json(self, arg=None):
        with open(self.scriptpath + self.dbfile, 'w') as f:
            json.dump(self.db, f)
        if arg:
            sys.exit(f'Link \'{arg}\' updated.')
        else:
            sys.exit()

    def _get_yt_meta_(self, link):
        lookup = {'meta' : 'content', 'link' : 'href'}
        properties = {'itemprop' : ['name', 'datePublished', 'videoId', 'thumbnailUrl', 'embedUrl']}
        meta = self._get_meta(link, lookup, properties)
        try:
            data = {'name' : meta['name'],
                    'published': meta['datePublished'],
                    'id': meta['videoId'],
                    'thumb' : meta['thumbnailUrl'],
                    'embed' : meta['embedUrl'],
                    'vidtype' : 'yt'
                    }
        except KeyError as e:
            sys.exit(f'Unable to acquire attribute {e}. Video may be set as private.')
        return data

    def _get_fb_meta_(self, link):
        lookup = {'meta' : 'content', 'link' : 'href'}
        properties = {'property' : ['og:title', 'og:image'], 'rel' : [['canonical']]}
        meta = self._get_meta(link, lookup, properties)
        url = None
        #print(meta)
        try:
            name = meta['og:title']
            url = meta['[\'canonical\']']
            thumb = html.unescape(meta['og:image'])
            vtype = 'fb'
            vidid = url.split('/')[-2]
            page = url.split('/')[3]
            embed = 'https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2F' + page + '%2Fvideos%2F' + vidid + '&amp'
        except KeyError:
            yn = input('Error: Video is not public, cannot fetch metadata. Do you wish to continue with incomplete data? Y/N ')
            if yn.lower() == 'y':
                vidid = link.split('v=')[1]
                name = None
                thumb = None
                embed = None
                vtype = 'privatefb'
            else:
                sys.exit('Operation aborted.')
        try:
            data = {'name' : name,
                    'published' : '',
                    'id' : vidid,
                    'thumb' : thumb,
                    'embed' : embed,
                    'vidtype' : vtype
                    }
        except KeyError as e:
            sys.exit(f'Unable to acquire attribute {e}. Video may be private.')
        return data

    def _get_zoom_codes(self, link):
        code = link.split('j/')[1]
        pw = None
        try:
            pw = code.split('?pwd=')[1]
            code = code.split('?')[0]
        except IndexError:
            pass
        return code, pw

    def _invalid_key(self, key):
        """Validates missing keys, ensures proper usage"""
        print(f'\'{key}\' is not a valid key.')
        for k in self.default_keys['main']:
            print(f'  {k}')
        ky = input('Please choose a key from the above list. Type \'exit\' to exit: ')
        if ky.lower() == 'exit':
            sys.exit()
        return ky

    def _print_json_list(self, json_dict=None, keys=None):
        if not json_dict:
            json_dict = self.db
        if not keys:
            keys = json_dict.keys()
        for key in keys:
            print(key)
            try:
                for k, item in json_dict[key].items():
                    print(f'   {k} : {item}')
            except:
                pass
        return

    def _post_signature(self, insta=False):
        sig = self.db['event']['sig']['title']
        if insta:
            link = 'Link in bio.\n'
        else:
            link = self.db['event']['sig']['link'] + '\n'
        tags = self.db['event']['sig']['html'] # hashtags
        return sig + link + tags

    def _generate_video_html(self, key, w=734, h=415):
        """Return text for video container that includes title and iframe"""
        link = self.db[key]['link']
        title = self.db[key]['title']
        vidtype = self.db[key]['vidtype']
        if link:
            if vidtype == 'yt' or vidtype =='fb':
                text = self._generate_iframe(key, w, h) + '\n'
                text += '<p style="font-size: 1.8301em;">' + title + '</p>\n'
                text += '<p>' + self.db[key]['name'] + '</p>\n'
                text += '<p><br></p><p><br></p><p><br></p>\n'
            else:
                # No iframe just formatted hyperlink. Used for videos that don't allow embedding.
                # This is validated when the meta data is processed (see: _get_*_meta())
                text = self._generate_video_link(key)
        else:
            text = ''
        return text

    def _generate_video_link(self, key):
        link = self.db[key]['link']
        title = self.db[key]['title']
        text = '<p style="font-size: 1.8301em;"><a href="'
        text += link
        text += '" data-location="external" data-detail="'
        text += link
        text += '" data-category="link" target="_blank" class="cloverlinks">'
        text += title
        text += '</a></p>\n'
        text += '<p><a href="'
        text += link
        text += '" data-location="external" data-detail="'
        text += link
        text += '" data-category="link" target="_blank" class="cloverlinks">Click here</a></p>'
        text += '<p><br></p><p><br></p><p><br></p>\n'
        return text

    def _generate_iframe(self, key, w=734, h=415):
        """Return the iframe text for a link"""
        if self.db[key]['embed']:
            text = '<iframe width="'+ str(w) +'" height="'+ str(h) +'" src="'
            text += self.db[key]['embed']
            text += '" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen=""></iframe>'
        else:
            text = ''
        return text

    def _generate_past_kids(self, key, title=None):
        link = self.db['past'][key]['link']
        text = ''
        if link:
            past_date = self.db['past']['date']
            if title is None:
                title = self.db['past'][key]['title']
            text += '<p>'
            text += past_date
            text += '</p><p><span class="clovercustom" style="font-size: 0.625em;">'
            text += title
            text += '</span></p>\n'
            text += link
            text += '\n\n'
        return text

    def _update_last(self):
        """When build is called, the current database data is moved to 'last'"""
        timestamp = dt.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
        # Update holders, this works because it will be reset in the 'build' if the links match
        self.db['last_holder'] = self.db['last']
        self.db['past_holder'] = deepcopy(self.db['past']) # deepcopy creates a new object instance and removes link to past values

        # Update last to current
        self.db['last'] = deepcopy(self.db['main'])
        self.db['last']['title'] += ' - ' + deepcopy(self.db['main']['name'])
        self.db['last']['stamp'] = timestamp
        self._update_past()

    def _update_past(self):
        # Update past to current
        self.db['past']['date'] = self.db['service']['date']
        for key in self.db:
            if key in self.db['past']:
                title = self.db[key]['title']
                if key == 'main':
                    title = self.db[key]['name']
                self.db['past'][key]['link'] = self.db[key]['link']
                self.db['past'][key]['title'] = title

    def _blank(self, key, timestamp):
        """Removes data from a key in database. Does not remove zoom link"""
        yn = input(f'Remove data from \'{key}\'?  Y/N : ')
        if yn.lower() == 'y':
            for item in self.db[key]:
                if item != 'zoom':
                    self.db[key][item] = ''
            self.db[key]['stamp'] = timestamp

    def _get_meta(self, link, lookup, properties):
        print('    Processing metadata...')
        page = urllib.request.urlopen(link)
        soup = BeautifulSoup(page.read(), "html.parser")
        meta_dict = {}
        for attr in lookup:
            #print(f'{attr=}')
            for itm in soup.find_all(attr):
                #print(f'{itm=}') # meta, link
                for prop in properties:
                    #print(f'{prop=}') # property
                    for p in properties[prop]: # og:title, canonical
                        #print(f'{p=}')
                        ip = itm.get(prop) # property
                        #print(type(ip))
                        content = itm.get(lookup[attr]) # content, href
                        #print(f'{ip=}')
                        if content and ip == p:
                            #print(f'{p=}')
                            #print(f'{content=}')
                            #if content:
                            meta_dict[str(p)] = content
        return meta_dict

    def _get_sunday_date(self, stamp):
        """Return the date of the nearest upcoming Sunday"""
        days_ahead = 6 - stamp.weekday() # 6 = Sunday
        if days_ahead <= 0:
            days_ahead += 7
        sunday = stamp + dt.timedelta(days_ahead)
        sunday = sunday.strftime('%B %d, %Y')
        return sunday

    def _format_short(self, url):
        """Reformats long YouTube urls to short"""
        slug = url.split('=')[-1]
        return 'https://youtu.be/' + slug

if __name__ == '__main__':
    HTML_Generator('links.json', 'TOC LINKS')

# TODO FUTURE
    # TODO scrape facebook for new video post at regular intervals
    # TODO scrape YT channel for new videos at regular interval
    # TODO automate editing the site
    # TODO GUI?
