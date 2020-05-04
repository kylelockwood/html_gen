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
from bs4 import BeautifulSoup
import facebook

# Alt+Shift+F or right-click in file, choose 'Format Document' to format json in VS Code

HELP = ('Usage: tochtml <url> <key>\n'
        '<url>      - accepts youtube and facebook video url\n'
        '<key>      - where to store url data.  Leaving this argument blank will display choices\n' 
        'list       - displays current json data\n'
        'blank      - sets empty strings to data in a key\n'
        'build      - creates an html document titled \'site_code_<timestamp>.txt\' containing current youtube links\n'
        'facebook iframes will be automatically updated in the file \'fb_iframe.txt\' and do not require a <key>\n'
)
PATH = os.path.dirname(os.path.realpath(sys.argv[0])) + '\\'
OUTPATH = 'C:' + os.environ["HOMEPATH"] + '\\Desktop\\TOC LINKS\\'

def main():
    print('Loading data...')
    links = load_json(PATH + 'links.json')
    args = get_inputs(links)
    print('Updating data...')
    links = update_links(links, args)
    if args[1] == 'fb':
        update_fb(links)
    print('Saving data...')
    update_json(links, args[1])

def print_json_list(json_dict):
    for keys in json_dict:
        print(keys)
        for key, item in json_dict[keys].items():
            print(f'   {key} : {item}')
    return

def load_json(filename):
    with open(filename) as f:
        data = json.load(f)
    return data

def get_inputs(links):
    """
    Returns argv[1] and argv[2] after formatting
    """
    # Ensure proper usage
    if len(sys.argv) < 2 or sys.argv[1] == 'help':
        sys.exit(HELP)
    arg1 = sys.argv[1]
    try:
        arg2 = sys.argv[2]
    except IndexError:
        arg2 = None
    if arg1 == 'list':
        # list current data in JSON
        sys.exit(print_json_list(links))
    elif arg1 == 'build':
        build(links)
    elif arg1.startswith('https://www.youtube.com'):
        arg1 = format_short(arg1)
    elif arg1.startswith('https://www.facebook.com'):
        arg2 = 'fb'
    elif arg1.startswith('www'):
        arg1 = 'https://' + arg1
    elif arg1 == 'blank':
        arg1 = None
    if arg2 is None or arg2 not in links.keys():
        while arg2 not in links.keys(): 
            for key in links.keys():
                print(f'  {key}')
            arg2 = input('Please choose a key from the above list. Type \'exit\' to exit: ')
            if arg2.lower() == 'exit':
                sys.exit()
    if arg1 and not arg1.startswith('https://'):
        sys.exit('Error, target must be a valid url.\n' + HELP)
    return arg1, arg2

def update_links(links, args):
    link = args[0]
    key = args[1]
    code = get_id(link)
    timestamp = dt.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    if not link:
        links = blank(key, links, timestamp)
        return links
    links[key]['link'] = link
    links[key]['name'] = get_name(link, key)
    if links['elem']['link'] == '':
        links['kids']['title'] = 'KIDS COMMUNITY VIDEO'
    else:
        links['kids']['title'] = 'PRESCHOOL / KINDER VIDEO'
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
        links[key]['thumb'] = get_thumb(link, code)
    except:
        links[key]['thumb'] = ''
    try:
        links[key]['embed'] = format_embed(link, code)
    except:
        links[key]['embed'] = ''
    return links

def blank(key, links, timestamp):
    yn = input(f'Remove data from \'{key}\'?  Y/N : ')
    if yn.lower() == 'y':
        for item in links[key]:
            links[key][item] = ''
        links[key]['stamp'] = timestamp
    return links


def get_id(link):
    code = link.split('/')[-1]
    return code

def get_name(link, key):
    # Can get a lot of other metadata from this if needed
    name = ''
    print('  Creating name...')
    #try:
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
    #except:
    # TODO get except name
    #    pass 
    return name

def get_date(link):
    # TODO rework this 
    date = ''
    print('  Fetching date...')
    if link.startswith('https://y'):
        soup = get_meta(link)
        if soup:
            date = soup.find("strong", attrs={"class": "watch-time-text"}).text
            if date.startswith('P'):
                date = date.split('Premiered ')[1:]
            elif date.startswith('U'):
                date = date.split('Uploaded on ')[1:]
        try:
            date = date[0]
        except IndexError:
            pass
    return date

def get_sunday_date(stamp):
    days_ahead = 6 - stamp.weekday() # 6 = Sunday
    if days_ahead <= 0:
        days_ahead += 7
    sunday = stamp + dt.timedelta(days_ahead)
    sunday = sunday.strftime('%B %d, %Y')
    return sunday

def get_thumb(link, slug):
    if link.startswith('https://y'):
        thumb = 'http://img.youtube.com/vi/' + slug + '/maxresdefault.jpg'
    if link.startswith('https://www.f'):
        permalink = get_permalink(link)
        postid = facebook_data(permalink)['id']
        thumb = facebook_data(postid + '?fields=full_picture')['full_picture']
    return thumb

def get_permalink(link):
    print('  Fetching permalink...')
    html = get_meta(link)
    perma = ''
    for lnk in html.find_all('meta'):
        url = lnk.get('content')
        if url and url.startswith('https://'):
            perma = url.split('permalink%2F')[1][:-3]
    return perma

def get_meta(link):
    print('  Processing metadata...')
    page = urllib.request.urlopen(link)
    soup = BeautifulSoup(page.read(), "html.parser")
    return soup

def format_short(url):
    slug = url.split('=')[-1]
    return 'https://youtu.be/' + slug

def format_embed(link, code):
    if link.startswith('https://youtu.be'):
        embed = 'https://www.youtube.com/embed/' + code
    elif link.startswith('https://www.facebook.com'):
        page = link.split('/')[-3]
        embed = 'https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2F' + page + '%2Fvideos%2F' + code + '&amp'
    else:
        embed =''
    return embed

def build(links):
    print('Build current list?')
    print_json_list(links)
    yn = input('Y/N ')
    if yn.lower() == 'y':
        # FB Post
        html = 'The Oregon Community At Home\n'
        html += links['main']['name'] + '\n\n'
        html += links['main']['link']
        keys = ['kids', 'elem', 'ms']
        for key in keys:
            if not links[key]['link'] == '':
                html += '\n\n'
                html += links[key]['title'] + '\n'
                html += links[key]['link']

        # Welcome page
        html += '\n\n\n== WELCOME PAGE ==\n\n'
        keys = ['main', 'kids', 'elem', 'ms']
        for key in keys:
            html += build_video_html(key, links, 734, 415)

        # Online Services page
        html += '\n\n\n== ONLINE SERVICES PAGE ==\n\n'
        html += build_video_html('main', links, 734, 415)
        keys = ['kids', 'elem', 'ms']
        for key in keys:
            if not links[key]['link'] == '':
                html += build_video_link(key, links)

        # Past online services
        html += '\n\n\n== PAST ONLINE SERVICES ==\n\n'
        html += '<p>Past Kid\'s Community videos can be found in the MEDIA/KIDS COMMUNITY tab or by clicking<a href="/media/kids-community-videos" data-location="existing" data-detail="/media/kids-community-videos" data-category="link" target="_self" class="cloverlinks"> HERE.</a></p><p><br></p><p><br></p>\n'
        
        # TODO video Title should be: Title - Date - Speaker
        
        html += build_video_html('last', links, 560, 315)

        # Kids Community Videos
        html += '\n\n\n== KIDS COMMUNITY VIDEOS ==\n\n'
        html += '<p>Here you will find videos for the Kid\'s Community and Middle School Ministry.&nbsp; Full online service videos can be found in the <a href="/media/online-services" data-location="existing" data-detail="/media/online-services" data-category="link" target="_self" class="cloverlinks">MEDIA/ONLINE SERVICES</a> tab</p><p><br></p><p><br></p><p><br></p>'
        keys = ['kids', 'elem', 'ms']
        for key in keys:
            html += build_video_html(key, links, 734, 415)

        # Past Kid's Videos
        # TODO Test this
        html += '\n\n\n== KIDS PAST VIDEOS ==\n\n'
        keys = ['kids', 'elem', 'ms']
        for key in keys:
            html += build_past_kids(key, links)

        # Kids Community thumbs (may not need this)
        html += '\n\n\n== KIDS COMMUNITY THUMBNAILS ==\n\n'
        for key in keys:
            html += links[key]['thumb'] + '\n'

        # Create output file
        timestamp = dt.datetime.now().strftime('%m%d%Y_%H%M%S')
        filename = timestamp +'_site_code.txt'
        with open(OUTPATH + filename, 'w') as f:
            f.writelines(html)

        print(f'\nFile \'{filename}\' sucessfully created.')

        keys = ['main', 'kids', 'elem', 'ms', 'last']
        for key in keys:
            thumb = links[key]['thumb']
            download_thumb(key, thumb)
        
        # Update json
        links = update_last(links)
        update_json(links, None)

    else:
        sys.exit()
    return

def build_past_kids(key, links):
    # TODO TEST THIS
    link = links['past'][key]['link']
    title = links['past'][key]['title']
    html = ''
    if not link == '':
        past_date = links['past']['date']
        title = links[key]['title']
        html += '<p>'
        html += past_date
        html += '</p><p><span class="clovercustom" style="font-size: 0.625em;">'
        html += title
        html += '</span></p>\n'
        html += link
        html += '\n\n'
    return html

def build_video_html(key, links, w, h):
    link = links[key]['link']
    title = links[key]['title']
    if not link == '':
        if link.startswith('https://youtu.be'):
            html = build_iframe(key, links, w, h) + '\n'
            html += '<p style="font-size: 1.8301em;">' + title + '</p>\n'
            html += '<p>' + links[key]['name'] + '</p>\n'
            html += '<p><br></p><p><br></p><p><br></p>\n'
        else:
            html = build_video_link(key, links)
    else:
        html =''
    return html

def build_iframe(key, links, w, h):
    if not links[key]['embed'] == '':
        html = '<iframe width="'+ str(w) +'" height="'+ str(h) +'" src="'
        html += links[key]['embed']
        html +='" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen=""></iframe>'
    else:
        html =''
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
    timestamp = dt.datetime.now().strftime('%m%d%Y_%H%M%S')
    filename = timestamp + '_' + key + '_thumb.jpg'
    try:
        urllib.request.urlretrieve(thumb, OUTPATH + filename)
        print(f'Thumbnail image \'{filename}\' successfully created.')
    except:
        print(f'Failed to create thumbnail image \'{filename}\'.')
    return 

def update_fb(links):
    link = links['fb']['link']
    permalink = get_permalink(link)
    fbdata = facebook_data(permalink)
    name = fbdata['message']
    links['fb']['name'] = name
    embed = links['fb']['embed']
    date = fbdata['created_time']
    date = dt.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S+0000')
    links['fb']['date'] = date.strftime('%B %d, %Y')
    build_fb_links(name, embed)
    thumb = links['fb']['thumb']
    download_thumb('fb', thumb)
    return

def facebook_data(link):
    token = load_json(PATH + 'uservars.json')['usertoken']
    graph = facebook.GraphAPI(access_token=token)
    data = graph.get_object(id=link)
    return data

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
    print(filename + ' updated.')
    return

def update_last(links):
    timestamp = dt.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    # TODO Title needs to be Name - Date - Speaker
    title = ''
    if not links['last'] == links['main']:
        links['last'] = links['main']
        links['last']['stamp'] = timestamp
        #links['last']['title'] = title
        links = update_past(links)
    return links

def update_past(links):
    links['past']['date'] = links['service']['date']
    for key in links:
        if key in links['past']:
            links['past'][key]['link'] = links[key]['link']
            links['past'][key]['title'] = links[key]['title']

    return links

def update_json(updateDict, arg=None):
    with open(PATH + 'links.json', 'w') as f:
        json.dump(updateDict, f)
    if arg:
        sys.exit(f'Link \'{arg}\' updated.')
    else:
        sys.exit()

if __name__ == '__main__':
    main()

# TODO FUTURE
    # TODO scrape facebook for new video post at regular intervals
    # TODO scrape YT channel for new videos at regular interval
    # TODO automate editing the site
    # TODO GUI?
