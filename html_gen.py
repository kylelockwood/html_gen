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
import pyperclip
from copy import deepcopy
from bs4 import BeautifulSoup
import html

# TODO Refactor as class

HELP = ('Usage: tochtml <url> <key>   or   tochtml <command>\n'
        '  <url>              - accepts youtube and facebook video url\n'
        '  <key>              - where to store url data.  Leaving this argument blank will display choices\n'
        '  list               - displays current json data relevant to operation\n'
        '  listall            - displays ALL current json data\n'
        '  blank <key>        - sets empty strings to data in a key\n'
        '  build              - creates an html document titled \'site_code_<timestamp>.txt\' containing current youtube links\n'
        '  ytlinks            - copies \'kids\', \'elem\', and \'ms\' links to the clipboard for YouTube description\n'
        '  thumb <key>        - downloads thumbnail image associated with <key>\n'
        '  thumbs             - downloads ALL thumbnail images from videos in database\n'
        '  frame <key>        - creates iframe html associated with key, including title and description, and copies to the clipboard\n'
        '  fbpost             - copies stardard Facebook post to clipboard\n'
        '  instaserv          - copies the link associated with <key> to the clipboard\n'
        '  instaann           - copies the text associated with <key> to the clipboard\n' 
        '  -<new title> <key> - replaces the title attribute in the <key>.  Will return to default after link update\n'
        )

OUTPATH = 'C:' + os.environ["HOMEPATH"] + '\\Desktop\\TOC LINKS\\'

def main():
    print('Loading data...')
    links = load_json('links.json')
    args = validate_inputs(links)
    print('Updating data...')
    links = update_links(links, args)
    #pyperclip.copy(str(links[args[1]]))
    #print(links[args[1]])
    #sys.exit('Changes are unsaved. Delete this line after testing')
    print('Saving data...')
    update_json(links, args[1])

def print_json_list(json_dict, keys=None):
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

def load_json(filename):
    try:
        with open(filename) as f:
            data = json.load(f)
    except Exception as e:
        sys.exit(f'  Unable to load JSON data. {e}')
    return data

def default_keys():
    """Return keys associated with elements used in functions"""
    return{
        'kids' : ['kids', 'elem', 'ms'],
        'main' : ['main', 'kids', 'elem', 'ms', 'ann'],
        'service' : ['service', 'main', 'kids', 'elem', 'ms'],
        'build' : ['main', 'kids', 'elem', 'ms']
    }

def default_title():
    return {'main' : 'SUNDAY SERVICE',
            'kids' : 'PRE-K VIDEO',
            'elem' : 'ELEMENTARY VIDEO',
            'ms' : 'MIDDLE SCHOOL VIDEO',
            'ann' : 'ANNOUNCEMENTS',
            'fb' : 'LIVE UPDATES'
    }

def invalid_key(key):
    """Validates missing keys, ensures proper usage"""
    print(f'\'{key}\' is not a valid key.')
    for k in default_keys()['main']:
        print(f'  {k}')
    ky = input('Please choose a key from the above list. Type \'exit\' to exit: ')
    if ky.lower() == 'exit':
        sys.exit()
    return ky

def validate_inputs(links):
    """Returns argv[1] and argv[2] after ensuring proper usage and formatting"""
    vidtype = 'yt' # TODO default for now
    if len(sys.argv) < 2 or sys.argv[1].lower() == 'help':
        sys.exit(HELP)
    arg1 = sys.argv[1]
    try:
        arg2 = sys.argv[2]
    except IndexError:
        arg2 = None
    if arg1 == 'listall':
        # list current data in JSON
        sys.exit(print_json_list(links))
    elif arg1 == 'list':
        sys.exit(print_json_list(links, default_keys()['service']))
    elif arg1 == 'build':
        build(links)
    elif arg1 == 'ytlinks':
        copy_links(links, default_keys()['kids'])    
    elif arg1 == 'fbpost':
        post = fb_post_text(links)
        pyperclip.copy(post)
        sys.exit(f'Facebook post copied to clipboard.')
    elif arg1 == 'instaserv':
        post = insta_post_text('serv', links)
        pyperclip.copy(post)
        sys.exit(f'Instagram service post copied to clipboard.')
    elif arg1 == 'instaann':
        post = insta_post_text('ann', links)
        pyperclip.copy(post)
        sys.exit(f'Instagram announcements post copied to clipboard.')
    elif arg1 == 'thumb':
        while True:
            if arg2 in links.keys():
                try:
                    thumb = links[arg2]['thumb']
                    download_thumb(arg2, thumb)
                    sys.exit()
                except:
                    sys.exit()
            else:
                arg2 = invalid_key(arg2)
    elif arg1 == 'thumbs':
        for key in default_keys()['main']:
            try:
                download_thumb(key, links[key]['thumb'])
            except:
                continue
        sys.exit()
    elif arg1 == 'frame':
        while True:
            if arg2 in links.keys():
                pyperclip.copy(build_video_html(arg2, links))
                sys.exit(f'Video html copied to clipboard.')
            else:
                arg2 = invalid_key(arg2)
    elif arg1.startswith('https://www.youtube.com'):
        arg1 = format_short(arg1)
    elif arg1.startswith('https://www.facebook.com'):
        #arg2 = 'fb'
        vidtype = 'fb'
    elif arg1.startswith('www'):
        arg1 = 'https://' + arg1
    elif arg1.startswith('-'): # Renaming title
        return arg1, arg2
    elif arg1 == 'blank':
        arg1 = None
    elif arg1 and not arg1.startswith('https://'):
        sys.exit('Error, target must be a valid url or command.\n' + HELP)
    if arg2 is None or arg2 not in links.keys():
        arg2 = invalid_key(arg2)

    return arg1, arg2, vidtype

def get_yt_meta(link):
    lookup = {'meta' : 'content', 'link' : 'href'}
    properties = {'itemprop' : ['name', 'datePublished', 'videoId', 'thumbnailUrl', 'embedUrl']}
    meta = get_meta(link, lookup, properties)
    return {'name' : meta['name'],
            'published': meta['datePublished'], 
            'id': meta['videoId'],
            'thumb' : meta['thumbnailUrl'],
            'embed' : meta['embedUrl']
            }

def get_fb_meta(link):
    lookup = {'meta' : 'content', 'link' : 'href'}
    properties = {'property' : ['og:title', 'og:image'], 'rel' : [['canonical']]}  
    meta = get_meta(link, lookup, properties)
    print(meta)
    try:
        name = meta['og:title']
        url = meta['[\'canonical\']']
        thumb = html.unescape(meta['og:image'])
    except KeyError:
        sys.exit('Error: Video is not public, cannot fetch metadata.')
    vidid = url.split('/')[-2]
    page = url.split('/')[3]
    embed = 'https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2F' + page + '%2Fvideos%2F' + vidid + '&amp'
    return {'name' : name,
            'published' : '',
            'id' : vidid,
            'thumb' : thumb,
            'embed' : embed
            }

def get_meta(link, lookup, properties):
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

def update_links(links, args):
    """Update links dict for key (arg1) """
    link = args[0]
    key = args[1]
    vidtype = args[2]
    timestamp = dt.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    if link is None:
        links = blank(key, links, timestamp)
        return links
    elif link.startswith('-'): # Rename title command
        temp_title = link.split('-')[1]
        links[key]['title'] = temp_title
        print(f'    Title \'{temp_title}\' updated for \'{key}\'.')
        return links
    else:
        links[key]['title'] = default_title()[key]
    if vidtype == 'yt':
        meta = get_yt_meta(link)
    elif vidtype =='fb':
        meta = get_fb_meta(link)
    links[key]['link'] = link

    # If one video for both age groups
    if not links['elem']['link']:
        links['kids']['title'] = 'KIDS COMMUNITY VIDEO'
        links['elem']['title'] = ''
    else:
        links['kids']['title'] = 'PRE-K VIDEO'
        links['elem']['title'] = 'ELEMENTARY VIDEO'

    links[key]['name'] = meta['name']
    links[key]['stamp'] = timestamp
    links[key]['id'] = meta['id']
    links[key]['date'] = meta['published']
    links[key]['thumb'] = meta['thumb']
    links[key]['embed'] = meta['embed']
    try:
        post_date = links['main']['date']
        dt_date = dt.datetime.strptime(post_date, '%Y-%m-%d')
    except:
        dt_date = dt.datetime.now()
    links['service']['date'] = get_sunday_date(dt_date)
    return links

def blank(key, links, timestamp):
    """Removes data from a key in database"""
    yn = input(f'Remove data from \'{key}\'?  Y/N : ')
    if yn.lower() == 'y':
        for item in links[key]:
            links[key][item] = ''
        links[key]['stamp'] = timestamp
    return links

def copy_links(links, keys):
    """Copies urls in keys to the clipboard""" 
    content = ''
    outmessage = ''
    for key in keys:
        link = links[key]['link']
        if link:
            content += links[key]['title'] + '\n' + link +'\n\n'
            if key == keys[len(keys) -1]:
                outmessage += ' and'
            outmessage += ' \'' + key + '\''
            if key != keys[len(keys) -1]:
                outmessage += ','
    pyperclip.copy(content)
    sys.exit(f'Links for{outmessage} copied to clipboard.')

def get_sunday_date(stamp):
    """Return the date of the nearest upcoming Sunday"""
    days_ahead = 6 - stamp.weekday() # 6 = Sunday
    if days_ahead <= 0:
        days_ahead += 7
    sunday = stamp + dt.timedelta(days_ahead)
    sunday = sunday.strftime('%B %d, %Y')
    return sunday

def format_short(url):
    """Reformats long YouTube urls to short"""
    slug = url.split('=')[-1]
    return 'https://youtu.be/' + slug

def fb_post_text(links):
    """Returns the text for a FB post to be used in build"""
    # FB Post creation
    html = 'The Oregon Community At Home\n\n'
    html += links['main']['name'] + '\n'
    html += links['main']['link']
    for key in default_keys()['kids']:
        if links[key]['link']:
            html += '\n\n'
            html += links[key]['title'] + '\n'
            html += links[key]['link']
    html += '\n\n' + links['recurring']['sig']['html'] + links['recurring']['sig']['link'] + '\n'
    html += links['recurring']['sig']['id']
    return html

def insta_post_text(post_type, links):
    if post_type == 'serv':
        title = 'The Oregon Community at home\n' + links['main']['name']
    elif post_type == 'ann':
        title = links['ann']['name']
    sig = '\n\n' + links['recurring']['sig']['html'] + 'Link in bio.\n'
    tags = links['recurring']['sig']['id']
    return title + sig + tags

def build(links):
    """Create outfile that contains html for site update"""
    print('Build current list?')
    print_json_list(links, default_keys()['service'])
    build_keys = default_keys()['build']
    kids_keys = default_keys()['kids']
    yn = input('Y/N ')
    if yn.lower() == 'y':
        # FB Post
        html = '== FACEBOOK POST ==\n\n'
        html += fb_post_text(links)

        # insta post
        html += '\n\n\n== INSTAGRAM POST ==\n\n'
        html += insta_post_text('service', links)

        # Welcome page
        html += '\n\n\n== WELCOME PAGE ==\n\n'
        for key in build_keys:
            html += build_video_html(key, links, 734, 415)

        # Online Services page
        html += '\n\n\n== ONLINE SERVICES PAGE ==\n\n'
        html += build_video_html('main', links, 734, 415)

        # Past online services
        html += '\n\n\n== PAST ONLINE SERVICES ==\n\n'
        title = links['past']['main']['title']
        title = title.split(' - ')[0]
        html += build_past_kids('main', links, title=title)

        # If past links are the same as current from build, recall the previous links
        if links['last']['link'] == links['main']['link']:
            links['last'] = links['last_holder']
            links['past'] = links['past_holder']

        # Kids Community Videos
        html += '\n\n\n== KIDS COMMUNITY VIDEOS ==\n\n'
        html += '<p>Here you will find videos for the Kid\'s Community and Middle School Ministry.&nbsp; Full online service videos can be found in the <a href="/media/online-services" data-location="existing" data-detail="/media/online-services" data-category="link" target="_self" class="cloverlinks">MEDIA/ONLINE SERVICES</a> tab</p><p><br></p><p><br></p><p><br></p>'
        for key in kids_keys:
            html += build_video_html(key, links, 734, 415)

        # Past Kid's Videos
        html += '\n\n\n== KIDS PAST VIDEOS ==\n\n'
        for key in kids_keys:
            html += build_past_kids(key, links)

        # Kids Community thumbs
        html += '\n\n\n== THUMBNAILS ==\n\n'
        for key in build_keys:
            html += links[key]['thumb'] + '\n'

        # Create output file
        timestamp = dt.datetime.now().strftime('%m%d%Y_%H%M%S')
        filename = 'BUILD_' + timestamp +'.txt'
        try:
            with open(OUTPATH + filename, 'w') as f:
                f.writelines(html)
            print(f'\nFile \'{filename}\' sucessfully created in {OUTPATH}.')
        except:
            print(f'\nFile \'{filename}\' could not be created.')
        
        # Thumbnails are generally downloaded earlier in the week to be used in the YT description,
        # so downloading them here is redundant. Leaving the code for future use.
        """
        # Download thumbnails
        for key in build_keys:
            thumb = links[key]['thumb']
            download_thumb(key, thumb)
        """

        # Update json
        update_last(links)
        update_json(links)
    else:
        sys.exit()

def build_past_kids(key, links, title=None):
    link = links['past'][key]['link']
    html = ''
    if link:
        past_date = links['past']['date']
        if title is None:
            title = links['past'][key]['title']
        html += '<p>'
        html += past_date
        html += '</p><p><span class="clovercustom" style="font-size: 0.625em;">'
        html += title
        html += '</span></p>\n'
        html += link
        html += '\n\n'
    return html

def build_video_html(key, links, w=734, h=415):
    """Return html for video container that includes title and iframe"""
    link = links[key]['link']
    title = links[key]['title']
    if link:
        if link.startswith('https://youtu.be'):
            html = build_iframe(key, links, w, h) + '\n'
            html += '<p style="font-size: 1.8301em;">' + title + '</p>\n'
            html += '<p>' + links[key]['name'] + '</p>\n'
            html += '<p><br></p><p><br></p><p><br></p>\n'
        else:
            html = build_video_link(key, links)
    else:
        html = ''
    return html

def build_iframe(key, links, w=734, h=415):
    """Return the iframe html for a link"""
    if links[key]['embed']:
        html = '<iframe width="'+ str(w) +'" height="'+ str(h) +'" src="'
        html += links[key]['embed']
        html += '" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen=""></iframe>'
    else:
        html = ''
    return html

def build_video_link(key, links):
    link = links[key]['link']
    title = links[key]['title']
    html = '<p style="font-size: 1.8301em;"><a href="'
    html += link
    html += '" data-location="external" data-detail="'
    html += link
    html += '" data-category="link" target="_blank" class="cloverlinks">'
    html += title
    html += '</a></p>\n'
    html += '<p><a href="'
    html += link
    html += '" data-location="external" data-detail="'
    html += link
    html += '" data-category="link" target="_blank" class="cloverlinks">Click here</a></p>'
    html += '<p><br></p><p><br></p><p><br></p>\n'
    return html

def download_thumb(key, thumb):
    """Downloads the image associated with passed thumbnail url to OUTPATH"""
    timestamp = dt.datetime.now().strftime('%m%d%Y_%H%M%S')
    filename = timestamp + '_' + key + '_thumb.jpg'
    try:
        urllib.request.urlretrieve(thumb, OUTPATH + filename)
        print(f'Thumbnail image \'{filename}\' successfully downloaded.')
    except:
        print(f'Failed to download thumbnail image \'{key}\'.')

def build_fb_links(name, embed):
    html = '== WELCOME PAGE ==\n\n'
    html += '<div><span class="clovercustom" style="font-size: 0.915em;">Get the latest updates from The Oregon Community staff here.  Past videos can all be found in the MEDIA tab or by clicking here.</span></div><div><br><br></div>\n'
    html += '<iframe src="'
    html += embed
    html += ';show_text=false&amp;width=734&amp;height=411&amp;appId" width="734" height="411" style="border:none;overflow:hidden" scrolling="no" frameborder="0" allowtransparency="true" allow="encrypted-media" allowfullscreen="true"></iframe>\n'
    html += '<p><br></p>\n'
    html += '<p style="font-size: 1.3072em;">'
    html += name
    html += '<br></p>'
    html += '\n\n\n== VIDEOS PAGE ==\n\n'

    # Update facebook html file
    filename = 'fb_iframe.txt'
    with open(OUTPATH + filename, 'w') as f:
        f.writelines(html)
    pyperclip.copy(html)
    print(filename + ' updated. iframe copied to clipboard.')

def update_last(links):
    """When build is called, the current database data is moved to 'last'"""
    timestamp = dt.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    # Update holders, this works because it will be reset in the 'build' if the links match
    links['last_holder'] = links['last']
    links['past_holder'] = deepcopy(links['past']) # deepcopy creates a new object instance and removes link to past values

    # Update last to current
    links['last'] = deepcopy(links['main'])
    links['last']['title'] += ' - ' + deepcopy(links['main']['name'])
    links['last']['stamp'] = timestamp
    update_past(links)

def update_past(links):
    # Update past to current
    links['past']['date'] = links['service']['date']
    for key in links:
        if key in links['past']:
            title = links[key]['title']
            if key == 'main':
                title = links[key]['name']
            links['past'][key]['link'] = links[key]['link']
            links['past'][key]['title'] = title

def update_json(updateDict, arg=None):
    with open('links.json', 'w') as f:
        json.dump(updateDict, f)
    if arg:
        sys.exit(f'Link \'{arg}\' updated.')
    else:
        sys.exit()

# Legacy
"""
PATH = os.path.dirname(os.path.realpath(sys.argv[0])) + '\\'

def build(links):
    <snip>
        # One last check for missing names
        for key in build_keys:
            if not links[key]['name']:
                print(f'  Missing name \'{key}\'')
                name = get_name(links[key]['link'], key)
                if name:
                    links[key]['name'] = name
                else:
                    print(f'    Warning, \'{key}\' is still missing attribute \'name\'')

def get_name(link, key):

    # Can get a lot of other metadata from this if needed
    name = ''
    print(f'  Fetching title for \'{key}\'...')
    try:
        if link.startswith('https://youtu.be'):
            params = {'format': 'json', 'url': link}
            url = 'https://www.youtube.com/oembed'
            query_string = urllib.parse.urlencode(params)
            url = url + '?' + query_string
            with urllib.request.urlopen(url) as response:
                response_text = response.read()
                data = json.loads(response_text.decode())
            name = data['title']

        elif key == 'kids':
            name = 'Watch with your kids... this is fun.'
        elif key == 'elem':
            name = 'This one is for the big kids.'
        elif key == 'ms':
            name = 'A video for the preteen audience'
        else:
            name = ''
        print('    Sucessfully updated title.')
    except Exception as e:
        print(f'    Failed to fetch name. Error: {e}')
    return name

def get_date(link):

    strdate = ''
    print('  Fetching date...')
    if link.startswith('https://youtu.be'):
        soup = get_meta(link)
        if soup:
            date = soup.find("strong", attrs={"class": "watch-time-text"}).text
            if date.startswith('Pr'):
                date = date.split('Premiered ')
            elif date.startswith('Pu'):
                date = date.split('Published on ')
            elif date.startswith('U'):
                date = date.split('Uploaded on ')
        try:
            print('    Sucessfully updated date.')
            strdate = date[1]
        except IndexError:
            print('    Failed to aquire date.')
    return strdate

def get_thumb(key, links, slug):
    link = links[key]['link']
    #if key == 'main':
    #    image_type = '/0.jpg'
    if link.startswith('https://youtu.be'):
        thumb = 'http://img.youtube.com/vi/' + slug + '/maxresdefault.jpg'
        try:
            urllib.request.urlretrieve(thumb)
        except:
            thumb = 'http://img.youtube.com/vi/' + slug + '/0.jpg'
    elif link.startswith('https://www.facebook'):
        permalink = get_permalink(link)
        postid = facebook_data(permalink)['id']
        thumb = facebook_data(postid + '?fields=full_picture')['full_picture']
    elif link.startswith('https://www.gominno'):
        thumb = links['recurring']['minnow']
    return thumb

def get_meta(link):
    print('    Processing metadata...')
    page = urllib.request.urlopen(link)
    soup = BeautifulSoup(page.read(), "html.parser")
    return soup

def format_embed(link, code):
    if link.startswith('https://youtu.be'):
        embed = 'https://www.youtube.com/embed/' + code
    elif link.startswith('https://www.facebook.com'):
        page = link.split('/')[-3]
        embed = 'https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2F' + page + '%2Fvideos%2F' + code + '&amp'
    else:
        embed = ''
    return embed

def get_id(link):
    code = link.split('/')[-1]
    return code

def get_soup(link):
    print('    Processing metadata...')
    page = urllib.request.urlopen(link)
    return BeautifulSoup(page.read(), "html.parser")

def get_yt_meta(link):
    soup = get_soup(link)
    if soup:
        meta_dict = {}
        lookup = {'meta' : 'content', 'link' : 'href'}
        keys = ['name', 'datePublished', 'videoId', 'thumbnailUrl', 'embedUrl']
        for attr in lookup.keys():
            for itm in soup.find_all(attr):
                ip = itm.get('itemprop')
                content = itm.get(lookup[attr])
                for key in keys:
                    if content and ip == key:
                        meta_dict[key] = content
        return {'name' : meta_dict['name'],
                'published': meta_dict['datePublished'], 
                'id': meta_dict['videoId'],
                'thumb' : meta_dict['thumbnailUrl'],
                'embed' : meta_dict['embedUrl']}
    else:
        sys.exit('Error: could not fetch metadata')

def format_fb_embed(link, code):
    page = link.split('/')[-3]
    embed = 'https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2F' + page + '%2Fvideos%2F' + code + '&amp'
    return embed

def update_links(); # legacy assignments
    

    try:
        links[key]['stamp'] = timestamp
    except:
        links[key]['stamp'] = ''
    try:
        links[key]['id'] = code
    except:
        links[key]['id'] = ''
    try:
        post_date = get_date(link)
        links[key]['date'] = post_date
    except:
        print('    No date data found.')
        links[key]['date'] = ''
        links['service']['date'] = ''
    try:
        post_date = links['main']['date']
        dt_date = dt.datetime.strptime(post_date, '%B %d, %Y')
    except:
        dt_date = dt.datetime.now()
    links['service']['date'] = get_sunday_date(dt_date)

    try:
        links[key]['thumb'] = get_thumb(key, links, code)
    except:
        links[key]['thumb'] = ''
    try:
        links[key]['embed'] = format_embed(link, code)
    except:
        links[key]['embed'] = ''
    return links

def get_permalink(link):
    print('  Fetching permalink...')
    page = urllib.request.urlopen(link)
    soup = BeautifulSoup(page.read(), "html.parser")
    perma = ''
    for lnk in soup.find_all('meta'):
        url = lnk.get('content')
        if url and url.startswith('https://'):
            perma = url.split('permalink%2F')[1][:-3]
    return perma

def update_fb(links):
    link = links['fb']['link']
    permalink = get_permalink(link)
    fbdata = facebook_data(permalink)
    
    try:
        name = fbdata['message']
    except KeyError:
        print(f'    Could not process \'name\'.')
        name = ''
    links['fb']['name'] = name
    embed = links['fb']['embed']
    date = fbdata['created_time']
    date = dt.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S+0000')
    links['fb']['date'] = date.strftime('%B %d, %Y')
    build_fb_links(name, embed)
    thumb = links['fb']['thumb']
    download_thumb('fb', thumb)

def facebook_data(link):
    token = load_json(PATH + 'uservars.json')['fb']['usertoken']
    graph = facebook.GraphAPI(access_token=token)
    data = graph.get_object(id=link)
    return data
"""

if __name__ == '__main__':
    main()

# TODO FUTURE
    # TODO scrape facebook for new video post at regular intervals
    # TODO scrape YT channel for new videos at regular interval
    # TODO automate editing the site
    # TODO GUI?
